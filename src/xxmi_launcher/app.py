import os
import argparse
import sys
import logging
import subprocess
import multiprocessing
import time
import traceback

from typing import Union, Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import Thread, current_thread, main_thread
from queue import Queue, Empty

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import PackageManager

from core.packages.installer_package import InstallerPackage
from core.packages.launcher_package import LauncherPackage
from core.packages.migoto_package import MigotoPackage
from core.packages.model_importers.wwmi_package import WWMIPackage
from core.packages.model_importers.zzmi_package import ZZMIPackage

from gui.windows.main.main_window import MainWindow


@dataclass
class ApplicationEvents:

    @dataclass
    class ConfigUpdate:
        pass

    @dataclass
    class OpenSettings:
        wait_window: bool = False

    @dataclass
    class LoadImporter:
        importer_id: str

    @dataclass
    class Ready:
        pass

    @dataclass
    class Busy:
        pass

    @dataclass
    class Launch:
        pass

    @dataclass
    class StatusUpdate:
        status: str

    @dataclass
    class SettingsUpdate:
        name: str
        value: str

    @dataclass
    class MoveWindow:
        offset_x: int
        offset_y: int

    @dataclass
    class Minimize:
        pass

    @dataclass
    class Maximize:
        pass

    @dataclass
    class Close:
        delay: int = 0

    @dataclass
    class Update:
        no_install: bool = False
        force: bool = False
        reinstall: bool = False
        packages: Union[list, None] = None
        silent: bool = False
        no_thread: bool = False

    @dataclass
    class CheckForUpdates:
        pass

    @dataclass
    class SetupHook:
        library_name: str

    @dataclass
    class WaitForProcess:
        process_name: str

    @dataclass
    class StartGameExe:
        process_name: str

    @dataclass
    class VerifyHook:
        library_name: str
        process_name: str

    @dataclass
    class ShowMessage:
        modal: bool = False
        icon: str = 'info-icon.ico'
        title: str = 'Message'
        message: str = '< Text >'
        confirm_text: str = 'OK'
        confirm_command: Union[Callable, None] = None
        cancel_text: str = ''
        cancel_command: Union[Callable, None] = None
        lock_master: bool = True
        screen_center: bool = False

    @dataclass
    class ShowError(ShowMessage):
        icon: str = 'error-icon.ico'
        title: str = 'Error'

    @dataclass
    class ShowWarning(ShowMessage):
        icon: str = 'warning-icon.ico'
        title: str = 'Warning'

    @dataclass
    class ShowInfo(ShowMessage):
        icon: str = 'info-icon.ico'
        title: str = 'Info'

    @dataclass
    class ShowDialogue(ShowMessage):
        confirm_text: str = 'Confirm'
        cancel_text: str = 'Cancel'


class Application:
    def __init__(self, app_gui: MainWindow):
        self.is_alive = True
        self.gui = app_gui

        parser = argparse.ArgumentParser(description='Launches and updates XXMI')
        parser.add_argument('-n', '--nogui', action='store_true',
                            help="Instantly launch XXMI if there's no update available")
        parser.add_argument('-u', '--update', action='store_true',
                            help="Automatically clean-install the latest XXMI version")
        parser.add_argument('-x', '--xxmi', type=str,
                            help="Set provided XXMI edition as default")
        self.args = parser.parse_args()

        try:
            Config.Config.load()
        except Exception as e:
            logging.exception(e)
            self.gui.show_messagebox(Events.Application.ShowError(
                modal=True,
                screen_center=True,
                lock_master=False,
                message=f'Failed to load configuration! Falling back to defaults.',
            ))

        logging.getLogger().setLevel(logging.getLevelNamesMapping().get(Config.Launcher.log_level, 'DEBUG'))

        self.threads = []
        self.error_queue = Queue()

        self.packages = [
            InstallerPackage(),
            LauncherPackage(),
            MigotoPackage(),
            WWMIPackage(),
            ZZMIPackage(),
        ]

        self.update_manager = PackageManager(self.packages)

        if self.args.xxmi is not None:
            Config.Launcher.active_importer = self.args.xxmi

        # Load packages of active importer and skip update for fast start
        self.load_importer(Config.Launcher.active_importer, update=False)

        # Quick launch mode
        if self.args.nogui:
            # Async run update_packages in check-for-updates mode to save available updates versions to config
            # It allows to go straight to game launch at the cost of update notification being delayed by 1 restart
            self.run_as_thread(self.update_manager.update_packages, no_install=True)
            # If there are any updates, ask user whether they want to install or skip them and just launch the game
            if self.update_scheduled():
                # Force update_packages call below to install the latest updates
                self.args.update = True
            else:
                # Launch game and close launcher
                self.launch()
                self.exit()
                return

        self.gui.initialize()

        if self.args.update:
            Events.Fire(Events.Application.Busy())
            Events.Fire(Events.Application.StatusUpdate(status='Initializing update...'))

        Events.Fire(Events.Application.LoadImporter(importer_id=Config.Launcher.active_importer))

        Events.Subscribe(Events.Application.Update,
                         lambda event: self.run_as_thread(self.update_manager.update_packages, **event.__dict__))
        Events.Subscribe(Events.Application.CheckForUpdates,
                         lambda event: self.run_as_thread(self.check_for_updates))
        Events.Subscribe(Events.Application.LoadImporter,
                         lambda event: self.run_as_thread(self.load_importer, importer_id=event.importer_id))
        Events.Subscribe(Events.Application.Launch,
                         lambda event: self.run_as_thread(self.launch))

        Events.Fire(Events.Application.ConfigUpdate())

        self.update_manager.notify_package_versions()

        self.gui.after(100, self.run_as_thread, self.auto_update)

        self.check_threads()

        self.gui.open()

        self.exit()

    def auto_update(self, no_install=False):
        self.update_manager.update_packages(force=self.args.update, no_install=True, silent=True)
        if not no_install and self.update_manager.update_available() and Config.Launcher.auto_update:
            self.update_manager.update_packages(force=False, no_install=False, silent=False)

    def load_importer(self, importer_id):
        if hasattr(Config, 'Active'):
            self.update_manager.unload_package(Config.Launcher.active_importer)
        Config.Launcher.active_importer = importer_id
        Config.Active = getattr(Config.Importers, importer_id)
        self.update_manager.load_package(importer_id)
        self.update_manager.notify_package_versions()
        Config.ConfigSecurity.validate_config()
        Events.Fire(Events.Application.ConfigUpdate())
        self.run_as_thread(self.auto_update, no_install=True)

    def update_scheduled(self) -> bool:
        if not self.update_manager.update_available():
            return False

        pending_update_message = []

        for package_name, package in self.update_manager.get_version_notification().package_states.items():
            # Exclude skipped package updates from the list
            if package.latest_version == package.skipped_version:
                continue
            # Include packages with version different from the latest
            if (package.installed_version != package.latest_version) and package.latest_version != '':
                pending_update_message.append(
                    f'{package_name} update found: {package.installed_version} -> {package.latest_version}')

        if len(pending_update_message) == 0:
            return False

        update_dialogue = Events.Application.ShowDialogue(
            modal=True,
            screen_center=not self.gui.is_shown(),
            lock_master=self.gui.is_shown(),
            icon='update-icon.ico',
            title='Update Available',
            confirm_text='Update',
            cancel_text='Skip',
            message='\n'.join(pending_update_message),
        )

        user_requested_update = self.gui.show_messagebox(update_dialogue)

        # Mark updates as skipped if user pressed Skip button, but only if it's not None from Close button
        if not user_requested_update and user_requested_update is not None:
            self.update_manager.skip_latest_updates()

        return bool(user_requested_update)

    def check_for_updates(self, force: bool = True):
        self.update_manager.update_packages(no_install=True, force=force)
        if self.update_manager.update_available():
            if self.update_scheduled():
                self.update_manager.update_packages(force=force)
        else:
            Events.Fire(Events.Application.ShowInfo(
                modal=True,
                message='No updates available!',
            ))

    def launch(self):
        Events.Fire(Events.Application.Busy())

        try:
            # Execute specified shell command before game start
            if Config.Active.Importer.run_pre_launch != '':
                process = subprocess.Popen(Config.Active.Importer.run_pre_launch, shell=True)
                if Config.Active.Importer.run_pre_launch_wait:
                    process.wait()

            # Signal active model importer package to start game and inject 3dmigoto
            Events.Fire(Events.ModelImporter.StartGame())

            # Execute specified shell command after successful injection
            if Config.Active.Importer.run_post_load != '':
                process = subprocess.Popen(Config.Active.Importer.run_post_load, shell=True)
                if Config.Active.Importer.run_post_load_wait:
                    process.wait()

        except Exception as e:
            raise Exception(f'{Config.Launcher.active_importer} Loading Failed:\n{str(e)}') from e
        finally:
            self.gui.after(100, Events.Fire, Events.Application.Ready())

        # Close the launcher or reset its UI state
        if Config.Launcher.auto_close:
            Events.Fire(Events.Application.Close(delay=1000))
        else:
            self.gui.after(1000, Events.Fire, Events.Application.Ready())

    def wrap_errors(self, callback, *args, **kwargs):
        try:
            callback(*args, **kwargs)
        except Exception as e:
            self.error_queue.put_nowait((e, traceback.format_exc()))

    def run_as_thread(self, callback, *args, **kwargs):
        # Force blocking callback execution with value return via `no_thread=True`is found in kwargs
        # Doing so allows to wait for callback completion or get its return value
        if 'no_thread' in kwargs:
            no_thread = kwargs['no_thread']
            del kwargs['no_thread']
        else:
            no_thread = False
        # Execute callback function directly or deploy it as thread
        if no_thread:
            return callback(*args, **kwargs)
        else:
            thread = Thread(target=self.wrap_errors, args=(callback, *args), kwargs=kwargs)
            self.threads.append(thread)
            thread.start()

    def check_threads(self):
        self.gui.after(50, self.check_threads)
        # Remove finished threads from the list
        self.threads = [thread for thread in self.threads if thread.is_alive()]
        # Raise exceptions sent to error queue by threads
        try:
            if self.gui.state() != 'normal':
                return
            self.report_thread_error()
            # raise exception
        except Empty:
            pass

    def report_thread_error(self):
        (error, trace) = self.error_queue.get_nowait()
        logging.error(trace)
        self.gui.show_messagebox(Events.Application.ShowError(
            modal=True,
            screen_center=not self.gui.is_shown(),
            lock_master=self.gui.is_shown(),
            message=str(error),
        ))
        if self.gui.is_shown():
            self.gui.after(100, Events.Fire, Events.Application.Ready())

    def watchdog(self, timeout: int = 15):
        timeout = time.time() + timeout
        while True:
            time.sleep(0.1)
            if not self.is_alive:
                return
            if time.time() > timeout:
                break
        logging.error('[WATCHDOG]: Shutting down stuck process...')
        os._exit(os.EX_OK)

    def exit(self):
        try:
            assert current_thread() is main_thread()
        except Exception as e:
            self.error_queue.put_nowait((e, traceback.format_exc()))
        # Start watchdog to forcefully shutdown process in 5 seconds
        watchdog_thread = Thread(target=self.watchdog, kwargs={'timeout': 5})
        watchdog_thread.start()
        # Join active threads
        logging.debug(f'Joining threads...')
        for thread in self.threads:
            thread.join()
        # Join watchdog thread
        logging.debug(f'Joining watchdog thread...')
        self.is_alive = False
        watchdog_thread.join()
        # Write config to ini file
        logging.debug(f'Saving config...')
        Config.Config.save()
        # Report any errors left in queue
        while True:
            try:
                self.report_thread_error()
            except Empty:
                break
        logging.debug(f'App Exit')
        os._exit(os.EX_OK)


if __name__ == '__main__':
    multiprocessing.freeze_support()

    if getattr(sys, 'frozen', False):
        root_path = Path(sys.executable).parent
        log_name = Path(sys.executable).stem
    else:
        root_path = Path().resolve()
        log_name = root_path.name

    # import binascii
    # bytestring = binascii.unhexlify(''.join(arr))
    # test = b.decode("ascii")

    Paths.initialize(root_path)

    logging.basicConfig(filename=root_path / f'{log_name} Log.txt',
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        level=logging.DEBUG)

    logging.debug(f'App Start')

    gui = MainWindow()

    try:
        # raise ValueError('1')
        # raise ValueError('1\n2\n3')
        Application(gui)
    except Exception as e:
        # raise e
        logging.exception(e)
        gui.show_messagebox(Events.Application.ShowError(
            modal=True,
            screen_center=True,
            lock_master=False,
            message=str(e),
        ))
