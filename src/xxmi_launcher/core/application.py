import sys
import logging
import os
import argparse
import subprocess
import time
import traceback

from pathlib import Path
from threading import Thread, current_thread, main_thread, Lock, Event
from queue import Queue, Empty

import core.error_manager as Errors
import core.locale_manager as Locale
import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config
import core.utils.system_info as system_info

from core.locale_manager import L
from core.events.application import ApplicationEvents
from core.package_manager import PackageManager

from core.packages.launcher_package import LauncherPackage
from core.packages.migoto_package import MigotoPackage
from core.packages.genshin_fps_unlock_package import GenshinFpsUnlockerPackage
from core.packages.model_importers.model_importer import ModelImporterPackage
from core.packages.model_importers.gimi_package import GIMIPackage
from core.packages.model_importers.srmi_package import SRMIPackage
from core.packages.model_importers.wwmi_package import WWMIPackage
from core.packages.model_importers.zzmi_package import ZZMIPackage
from core.packages.model_importers.himi_package import HIMIPackage
from core.packages.model_importers.efmi_package import EFMIPackage

from core.game_launcher import Launcher


class Application:
    def __init__(self, gui):
        # At this point GUI is minimally initialized (just enough to show messages)
        self.gui = gui
        # Lock state flag, game launch attempts will be ignored while it's True
        self.is_locked = False
        # Thread pool for threaded tasks
        self.threads = []
        self.thread_lock = Lock()
        # Queue for thread errors handling
        self.error_queue = Queue()
        # App shutdown state flag
        self.shutting_down = False
        # App shutdown event for watchdog thread
        self.shutdown_event = Event()

        # Parse console args
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('exe_path', nargs='?', default='', help='Path to game .exe file.')
        parser.add_argument('-h', '--help', '-help', action='store_true',
                            help='Show this help message and exit.')
        parser.add_argument('-x', '--xxmi', type=str,
                            help='Set active model importer (WWMI/ZZMI/SRMI/GIMI/HIMI/EFMI) used by launcher.')
        parser.add_argument('-n', '--nogui', action='store_true',
                            help='Start game with active model importer without showing launcher window.')
        parser.add_argument('-u', '--update', action='store_true',
                            help='Force check for updates and install available ones.')
        parser.add_argument('-s', '--create_shortcut', type=str,
                            help='Create desktop shortcut for launcher .exe.')
        parser.add_argument('-un', '--uninstall', action='store_true',
                            help='Remove downloaded packages from the Resources folder.')
        try:
            args = [arg for arg in sys.argv[1:] if arg != '&&']  # Filter out shell operator '&&'
            self.args, self.unknown_args = parser.parse_known_args(args)
            logging.debug(f'Arguments: {self.args}')
            if self.args.help:
                parser.print_help()
                return
        except BaseException:
            raise ValueError(L('application_failed_parse_args', 'Failed to parse args: {args}').format(args=sys.argv))

        # Load config json
        try:
            self.load_config()
        except Exception as error:
            logging.exception(error)
            self.gui.show_messagebox(Events.Application.ShowError(
                modal=True,
                message=L('message_text_config_was_reset', 'Failed to load configuration! Falling back to defaults.'),
            ))

        # Configure locale
        Events.Subscribe(Events.Application.LoadLocale, self.handle_load_locale)
        try:
            if not Config.Launcher.locale:
                # Write detected OS locale to config
                Config.Launcher.locale = Locale.Locale.active_locale.name
            else:
                # Use locale specified by config
                Events.Fire(Events.Application.LoadLocale(locale_name=Config.Launcher.locale, skip_reload=True))
        except Exception as error:
            logging.exception(error)

        logging.getLogger().setLevel(logging.getLevelNamesMapping().get(Config.Launcher.log_level, 'DEBUG'))

        # Async query and log OS and hardware info
        self.run_as_thread(system_info.log_system_info)

        # Load packages
        self.packages = [
            LauncherPackage(),
            MigotoPackage(),
            GenshinFpsUnlockerPackage(),
            GIMIPackage(),
            SRMIPackage(),
            WWMIPackage(),
            ZZMIPackage(),
            EFMIPackage(),
            HIMIPackage(),
        ]

        self.package_manager = PackageManager(self.packages)

        if self.args.uninstall:
            self.package_manager.uninstall_packages()
            self.exit()
            return

        if self.args.create_shortcut:
            Events.Fire(Events.LauncherManager.CreateShortcut())

        # Initialize launcher class.
        self.launcher = Launcher
        self.launcher.initialize(self.package_manager.get_package('XXMI'))

        # Get active MI from args, use one from config or fallback to XXMI homepage
        active_importer = self.get_active_importer()

        # Load packages of active importer and skip update for fast start
        self.load_importer(active_importer, update=False)

        if self.args.update:
            Config.Manager.save()

        Events.Subscribe(Events.Application.OpenSettings, self.handle_open_settings)

        # Quick launch mode
        if self.args.nogui:
            # If there are any updates, ask user whether they want to install or skip them and just launch the game
            if self.update_scheduled():
                # Force update_packages call below to install the latest updates
                self.args.update = True
            else:
                # Async run update_packages in check-for-updates mode to save available updates versions to config
                # It allows to go straight to game launch at the cost of update notification being delayed by 1 restart
                self.run_as_thread(self.package_manager.update_packages, no_install=True, silent=True)
                # Launch game and close launcher
                self.launch()
                self.exit()
                return

        self.initialize_gui()

        self.exit()

    def initialize_gui(self, open_settings: bool = False):
        self.gui.initialize()

        if self.args.update:
            Events.Fire(Events.Application.Busy())
            Events.Fire(Events.Application.StatusUpdate(status=L('status_initializing_update', 'Initializing update...')))

        # Trigger events required to initialize GUI state.
        Events.Fire(Events.Application.LoadImporter(importer_id=Config.Launcher.active_importer))
        Events.Fire(Events.Application.ConfigUpdate())
        Events.Fire(Events.PackageManager.NotifyPackageVersions(detect_installed=True))

        Events.Subscribe(Events.Application.Update, self.handle_update)
        Events.Subscribe(Events.Application.CheckForUpdates,
            lambda event: self.run_as_thread(self.check_for_updates))
        Events.Subscribe(Events.Application.LoadImporter,
            lambda event: self.run_as_thread(self.load_importer, importer_id=event.importer_id, reload=event.reload))
        Events.Subscribe(Events.Application.Launch,
            lambda event: self.run_as_thread(self.launch))
        Events.Subscribe(Events.Application.Restart,
            lambda event: self.run_as_thread(self.restart, delay=event.delay))

        self.gui.after(100, self.run_as_thread, self.auto_update)

        if open_settings:
            Events.Fire(Events.Application.OpenSettings())

        self.handle_stats()

        self.check_threads()

        logging.debug('Core ready!')

        self.gui.open()

    def handle_update(self, event: Events.Application.Update):
        self.launcher.ensure_game_close()
        self.run_as_thread(self.package_manager.update_packages, **event.__dict__)

    def handle_open_settings(self, event: ApplicationEvents.OpenSettings):
        settings_frame = self.gui.launcher_frame.grab('SettingsFrame')
        if not settings_frame:
            self.initialize_gui(open_settings=True)
        else:
            settings_frame.open_settings(tab_name=event.tab_name, wait_window=event.wait_window)

    def load_config(self):
        cfg_backup_path = Paths.App.Backups / Config.Manager.config_path.name
        try:
            Config.Manager.load()
            # Backup last successfully loaded config
            if Config.Manager.config_path.is_file():
                Paths.App.copy_file(Config.Manager.config_path, cfg_backup_path)
        except Exception as e:
            if Config.Manager.config_path.is_file():
                error_dialogue = Events.Application.ShowError(
                    modal=True,
                    confirm_text=L('message_button_load_backup_config', 'Load Backup'),
                    cancel_text=L('message_button_load_default_config', 'Load Default'),
                    message=L('message_text_config_load_failed', 'Failed to load configuration!'),
                )
                user_requested_backup_load = self.gui.show_messagebox(error_dialogue)
                if user_requested_backup_load:
                    Config.Manager.load(cfg_backup_path)
            else:
                raise e

    def handle_load_locale(self, event: ApplicationEvents.LoadLocale):
        Locale.Locale.set_active_locale(event.locale_name, skip_reload=event.skip_reload)
        # Notify user about locale errors
        if Locale.Locale.locale_engine.locale_errors:
            self.gui.show_messagebox(Events.Application.ShowWarning(
                modal=True,
                message=L('message_text_locale_errors', """
                    Detected errors in active localization files:
                    
                    {locale_errors:md_list}
                """).format(
                    locale_errors=Locale.Locale.locale_engine.locale_errors,
                ),
            ))

    def validate_importer_name(self, importer_name: str) -> str:
        importer_name = importer_name.upper()
        if importer_name != 'XXMI' and importer_name not in Config.Importers.__dict__.keys():
            raise ValueError(L('error_unknown_model_importer', 'Unknown model importer {importer}!').format(importer=importer_name))
        return importer_name

    def get_importer_from_path(self, game_exe_path: Path):
        Events.Fire(Events.PathManager.VerifyFileAccess(path=game_exe_path, extension_filter="exe"))

        for package_name, package_config in Config.Importers.__dict__.items():
            game_exe_name = game_exe_path.name

            if game_exe_name in package_config.Importer.process_exe_names:
                return package_name, game_exe_path.parent, game_exe_path

            if game_exe_name in package_config.Importer.game_exe_names:
                return package_name, game_exe_path.parent, game_exe_path

        raise ValueError(L('error_model_importer_auto_select_failed', """
            Failed to auto-select importer for `{path}`!
            
            Try to add `--nogui --xxmi WWMI` args (or GIMI, SRMI, ZZMI, HIMI, EFMI).
        """).format(path=game_exe_path))

    def get_active_importer(self) -> str:
        active_importer = None

        if not self.args.xxmi and self.args.exe_path:
            exe_path = Path(self.args.exe_path)

            importer_name, game_path, game_exe_path = self.get_importer_from_path(exe_path)
            logging.debug(f'Detected {importer_name} start request for {game_exe_path}.')

            self.args.nogui = True
            self.args.xxmi = importer_name
            Config.Importers.__dict__[importer_name].Importer.game_folder = str(game_path)

        if self.args.xxmi:
            # Active model importer override is supplied via command line arg `--xxmi`
            try:
                active_importer = self.validate_importer_name(self.args.xxmi)
            except Exception:
                Events.Fire(Events.Application.ShowWarning(
                    message=L('error_unknown_model_importer_arg', 'Unknown model importer supplied as command line arg `--xxmi={arg_xxmi}`!').format(arg_xxmi=self.args.xxmi))
                )

        elif Config.Launcher.active_importer:
            # Active model importer override is supplied via `active_importer` setting
            try:
                active_importer = self.validate_importer_name(Config.Launcher.active_importer)
            except Exception:
                Events.Fire(Events.Application.ShowWarning(
                    message=L('error_unknown_model_importer_setting', 'Unknown model importer `{importer}` supplied with `active_importer` setting!').format(importer=Config.Launcher.active_importer))
                )

        if active_importer is None:
            active_importer = 'XXMI'

        return active_importer

    def auto_update(self):
        # Exit early if current active model importer is not installed
        importer_package = self.package_manager.packages.get(Config.Launcher.active_importer, None)
        if importer_package is None or importer_package.get_installed_version() == '':
            self.package_manager.update_packages(packages=['Launcher'], no_install=True, silent=True)
            Events.Fire(Events.Application.Ready())
            return
        # Query GitHub for updates and skip installation, force query and lock GUI if --update argument is supplied
        try:
            self.package_manager.update_packages(no_install=True, force=self.args.update, silent=not self.args.update)
            if Config.Launcher.active_importer == 'XXMI' and not self.args.update:
                return
        except Exception as e:
            if self.args.update:
                Events.Fire(Events.Application.ShowWarning(
                    message=L('error_version_list_fetch_failed', """
                        Failed to get latest versions list from GitHub!
                        
                        {error_text}
                    """).format(error_text=e),
                    modal=True))
        # Exit early if there are no updates available
        if not self.package_manager.update_available():
            return
        # Exit early if automatic update installation is not expected
        if not (Config.Launcher.auto_update or self.args.update):
            return
        # If user is in rush and managed to start the game, lets rather not bother them with update
        if self.is_locked:
            return
        # Install any updates we've managed to find during previous update_packages call
        self.package_manager.update_packages(no_check=True, force=self.args.update, silent=False)
        # This flag is supposed to affect only the first auto-update after launcher start, so lets remove it here
        self.args.update = False
        # Resume interrupted Quick Start
        if self.args.nogui:
            Events.Fire(Events.Application.Launch())

    def load_importer(self, importer_id, update=True, reload=False):
        # Unload package of other MI if there's one loaded
        if hasattr(Config, 'Active'):
            if importer_id == Config.Launcher.active_importer and not reload:
                return
            self.package_manager.unload_package(Config.Launcher.active_importer)
        # Mark requested MI as active
        Config.Launcher.active_importer = importer_id
        # Exit early if requested MI is `XXMI` aka dummy id used for homepage
        if importer_id == 'XXMI':
            return
        # Add MI to the list of enabled one if it's not in it already (i.e. if user manually edited settings file)
        if importer_id not in Config.Launcher.enabled_importers:
            Config.Launcher.enabled_importers.append(importer_id)
        # Load MI package
        Config.Active = getattr(Config.Importers, importer_id)
        Config.Config.Active = Config.Active
        self.package_manager.load_package(importer_id)
        self.launcher.set_model_importer(self.package_manager.get_package(importer_id))
        self.package_manager.notify_package_versions()
        Config.Manager.validate_config()
        Events.Fire(Events.Application.ConfigUpdate())
        # Check for updates
        if update and self.package_manager.get_package(importer_id).installed_version:
            self.run_as_thread(self.package_manager.update_packages, no_install=True, silent=True)

    def update_scheduled(self) -> bool:
        if not self.package_manager.update_available():
            return False

        pending_update_message = []

        for package_name, package in self.package_manager.get_version_notification().package_states.items():
            # Exclude skipped package updates from the list
            if package.latest_version == package.skipped_version:
                continue
            # Include packages with version different from the latest
            if package.latest_version != '' and (package.installed_version != package.latest_version):
                pending_update_message.append(L('application_update_found',
                    '{package} update found: {current} → {latest}'
                ).format(
                    package=package_name,
                    current=package.installed_version or 'N/A',
                    latest=package.latest_version
                ))

        if len(pending_update_message) == 0:
            return False

        update_dialogue = Events.Application.ShowDialogue(
            modal=True,
            title=L('message_title_update_available', 'Update Available'),
            confirm_text=L('message_button_install_update', 'Update'),
            cancel_text=L('message_button_skip_update', 'Skip'),
            message='\n'.join(pending_update_message),
        )

        user_requested_update = self.gui.show_messagebox(update_dialogue)

        # Mark updates as skipped if user pressed Skip button, but only if it's not None from Close button
        if not user_requested_update and user_requested_update is not None:
            self.package_manager.skip_latest_updates()

        return bool(user_requested_update)

    def check_for_updates(self, force: bool = True):
        try:
            self.package_manager.update_packages(no_install=True, force=force)
        except Exception as e:
            if 'failed to detect latest launcher version' in str(e).lower():
                # Failed to check launcher package GitHub, and since it's the very first check, there's connection error
                raise e
            else:
                # Failed to check some other package, lets give a warning and still try to go further
                Events.Fire(Events.Application.ShowWarning(
                    message=str(e),
                    modal=True
                ))
        if self.package_manager.update_available():
            if self.update_scheduled():
                self.package_manager.update_packages(no_check=True, force=force)
        else:
            Events.Fire(Events.Application.ShowInfo(
                modal=True,
                message=L('message_text_already_up_to_date', 'No updates available!'),
            ))

    def get_launch_counters_from_log(self, exclude_failed = True):
        with (open(Paths.App.Root / 'XXMI Launcher Log.txt', 'r', encoding='utf-8', errors='ignore') as f):
            launch_counters = { 'GIMI': 0, 'SRMI': 0,  'WWMI': 0, 'ZZMI': 0, 'HIMI': 0, 'EFMI': 0 }

            def parse_active_package(line):
                if 'Loaded package:' in line:
                    for package in launch_counters.keys():
                        if package in line:
                            return package
                return ''
            def parse_launch(line):
                return line.endswith('ApplicationEvents.Launch()')
            def parse_warning(line):
                return 'ApplicationEvents.ShowWarning' in line
            def parse_error(line):
                return 'ApplicationEvents.ShowError' in line
            def parse_state_ready(line):
                return line.endswith('ApplicationEvents.Ready()')

            active_package = ''
            launch_in_progress = False

            for line_id, line in enumerate(map(str.strip, f.readlines())):
                # Detect which model importer is used for launch event
                package = parse_active_package(line)
                if package:
                    active_package = package
                    launch_in_progress = False  # Reset launch event state to handle possible malformed logs
                    continue
                # Skip all lines 'till model importer package load
                if not active_package:
                    continue
                # Detect launch event
                if parse_launch(line):
                    launch_in_progress = True
                    continue
                # Detect result of launch event
                if launch_in_progress:
                    # Abort launch event parsing on warning or error
                    if exclude_failed and (parse_warning(line) or parse_error(line)):
                        launch_in_progress = False
                        continue
                    # Detect launch event finish
                    if parse_state_ready(line):
                        launch_counters[active_package] += 1
                        launch_in_progress = False
                        continue

            return launch_counters

    def get_launch_counters(self):
        launch_counters = {}
        # Fetch launch stats from config
        for package_name, importer in Config.Importers.__dict__.items():
            launch_counters[package_name] = importer.Importer.launch_count
        # Parse launch stats from log
        if -1 in launch_counters.values():
            try:
                logged_launch_count = self.get_launch_counters_from_log()
                for importer, count in launch_counters.items():
                    if count == -1:
                        launch_counters[importer] = logged_launch_count.get(importer, 0)
                        Config.Importers.__dict__[importer].Importer.launch_count = launch_counters[importer]
                        logging.debug(f'Parsed {importer} launch count from log: {launch_counters[importer]}')
            except Exception as e:
                logging.debug(f'Failed to parse launch counts from log: {e}')
        return launch_counters

    def handle_stats(self):
        # Show 1-time credits notification for the first model importer that reaches 100 launches
        if not Config.Launcher.credits_shown:
            # Check flag file to handle possible config reset
            flag_path = Paths.App.Resources / 'Security' / 'Credits.lock'
            if flag_path.is_file():
                Config.Launcher.credits_shown = True
                return

            launch_counters = self.get_launch_counters()

            most_launched_model_importer = max(launch_counters, key=launch_counters.get)
            max_launch_count = launch_counters[most_launched_model_importer]

            if max_launch_count >= 100 and most_launched_model_importer == Config.Launcher.active_importer:
                # Set flag in config to avoid excessive FS calls
                Config.Launcher.credits_shown = True
                # Create flag file to prevent notification spam on config reset
                try:
                    flag_path.touch()
                except Exception as e:
                    logging.debug(f'Failed to create Credits.lock: {e}')
                # Show credits notification
                try:
                    Events.Fire(Events.Application.OpenDonationCenter(
                        mode='POPUP',
                        model_importer=most_launched_model_importer,
                        launch_count=max_launch_count
                    ))
                except Exception as e:
                    logging.debug(f'Failed to show credits notification: {e}')

    def launch(self):
        if self.is_locked:
            return
        self.is_locked = True

        Events.Fire(Events.Application.Busy())

        try:
            # Execute specified shell command before game start
            if Config.Active.Importer.run_pre_launch_enabled and Config.Active.Importer.run_pre_launch != '':
                Events.Fire(Events.Application.RunPreLaunch(cmd=Config.Active.Importer.run_pre_launch))
                process = subprocess.Popen(Config.Active.Importer.run_pre_launch, shell=True)
                if Config.Active.Importer.run_pre_launch_wait:
                    process.wait()

            # Start game and inject 3dmigoto
            self.launcher.launch(self.unknown_args)

            # Execute specified shell command after successful injection
            if Config.Active.Importer.run_post_load_enabled and Config.Active.Importer.run_post_load != '':
                Events.Fire(Events.Application.RunPostLoad(cmd=Config.Active.Importer.run_post_load))
                process = subprocess.Popen(Config.Active.Importer.run_post_load, shell=True)
                if Config.Active.Importer.run_post_load_wait:
                    process.wait()
        except UserWarning:
            self.is_locked = False
            self.gui.after(100, Events.Fire, Events.Application.Ready())
            return
        except Exception as e:
            raise Errors.with_title(e, L('message_title_model_importer_loading_failed', '{importer} Loading Failed').format(
                importer=Config.Launcher.active_importer,
            ))
        finally:
            self.is_locked = False
            if not Config.Launcher.auto_close:
                self.gui.after(100, Events.Fire, Events.Application.Ready())

        # Track launch stats
        Config.Active.Importer.launch_count += 1

        # Close the launcher or reset its UI state
        if Config.Launcher.auto_close or self.args.nogui:
            Events.Fire(Events.Application.Close(delay=1000))

    def wrap_errors(self, callback, *args, **kwargs):
        try:
            callback(*args, **kwargs)
        except Exception as e:
            self.error_queue.put_nowait((e, traceback.format_exc()))

    def run_as_thread(self, callback, *args, **kwargs):
        # Force blocking callback execution with value return via `no_thread=True`is found in kwargs.
        # Doing so allows to wait for callback completion or get its return value.
        no_thread = kwargs.pop("no_thread", False)

        # Execute callback function directly.
        if no_thread:
            return callback(*args, **kwargs)

        with self.thread_lock:
            if self.shutting_down:
                logging.warning("Ignoring thread request during application shutdown: %s", callback)
                return None

            thread = Thread(
                target=self.wrap_errors,
                args=(callback, *args),
                kwargs=kwargs
            )

            self.threads.append(thread)
            thread.start()

        return None

    def check_threads(self):
        if self.shutting_down:
            return

        # Remove finished threads from the list.
        with self.thread_lock:
            self.threads = [thread for thread in self.threads if thread.is_alive()]

        # Handle all pending worker exceptions.
        while True:
            try:
                self.report_thread_error()
            except Empty:
                break
            except Exception:
                # Don't allow an error while displaying an error to kill the Tkinter polling loop.
                logging.exception("Failed to report thread error")
                break

        # Schedule the next check.
        try:
            self.gui.after(50, self.check_threads)
        except RuntimeError:
            # GUI/mainloop has already shut down.
            pass

    def report_thread_error(self):
        (error, trace) = self.error_queue.get_nowait()

        logging.error(trace)

        self.gui.show_messagebox(Events.Application.ShowError(
            modal=True,
            title=Errors.get_title(error) or L("message_title_error", "Error"),
            message=str(error),
        ))

    def log_remaining_thread_errors(self):
        count = 0

        while True:
            try:
                error, trace = self.error_queue.get_nowait()
            except Empty:
                break

            count += 1
            logging.error("Unhandled worker exception during shutdown: %s\n%s", error, trace)

        if count:
            logging.error("Shutting down with %d unreported worker error(s).", count)

    def watchdog(self, timeout: int = 15):
        if not self.shutdown_event.wait(timeout):
            logging.error("[WATCHDOG]: Shutting down stuck process...")
            os._exit(os.EX_OK)

    def exit(self):
        if current_thread() is not main_thread():
            raise RuntimeError("exit() must be called from the main thread")

        # Establish the shutdown barrier.
        with self.thread_lock:
            self.shutting_down = True
            threads = list(self.threads)

        # Start watchdog to forcefully shutdown process in 5 seconds.
        watchdog_thread = Thread(
            target=self.watchdog,
            kwargs={"timeout": 5},
            daemon=True,
        )
        watchdog_thread.start()

        # No new threads should be started from this point.
        logging.debug("Joining threads...")
        for thread in threads:
            thread.join()

        # All workers are now finished, so no more errors can be added to error_queue.
        self.log_remaining_thread_errors()

        # Disable watchdog.
        logging.debug("Stopping shutdown watchdog...")
        self.shutdown_event.set()

        # Write config to ini file
        logging.debug("Saving config...")
        try:
            Config.Manager.save()
        except Exception:
            logging.exception("Failed to save config during shutdown")

        logging.debug("App Exit")
        os._exit(os.EX_OK)

    def restart(self, delay: int = 0):
        if '__compiled__' in globals() or getattr(sys, 'frozen', False):
            subprocess.Popen(sys.executable, shell=True)
        Events.Fire(Events.Application.Close(delay=delay))
