import logging
import os
import time
import re

from pathlib import Path
from dataclasses import fields

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.locale_manager import L
from core.config_manager import AppConfig
from core.config.enums import GameLaunch, StartMethod, InjectMode
from core.platforms.game import Game
from core.platforms.game_platform import GamePlatform
from core.platforms.game_platform_protocol import GamePlatformProtocol
from core.platforms.game_platform_registry import PlatformRegistry
from core.platforms.steam.steam_manager import SteamManager
from core.platforms.epic.epic_manager import EpicManager
from core.packages.model_importers.model_importer import ModelImporterPackage
from core.packages.migoto_package import MigotoPackage, MigotoInjector, InjectorContext, MigotoIdentity, MigotoFork
from core.utils.process_manager import ProcessManager, ProcessPriorityClass, LaunchContext, ExecutableLaunch, CommandLaunch

log = logging.getLogger(__name__)


LAUNCH_TO_PLATFORM = {
    GameLaunch.STEAM: GamePlatform.STEAM,
    GameLaunch.EPIC_GAMES: GamePlatform.EPIC,
}


class GameLauncher:

    def __init__(self):
        self.xxmi_injector: MigotoPackage | None = None
        self.model_importer: ModelImporterPackage | None = None
        self.platform_registry: PlatformRegistry | None = None
        self.xxmi_dll_identity: MigotoIdentity | None = None

        Events.Subscribe(Events.ModelImporter.Install, self.install_model_importer)
        Events.Subscribe(Events.PackageManager.VersionNotification, self._handle_version_notification)

    def initialize(self, xxmi_injector: MigotoPackage):
        self.xxmi_injector: MigotoPackage = xxmi_injector

        if self.platform_registry is not None:
            raise RuntimeError('GameLauncher already initialized')

        self.platform_registry = PlatformRegistry({
            SteamManager,
            EpicManager,
        })

    def set_model_importer(self, model_importer: ModelImporterPackage) -> None:
        self.model_importer = model_importer

    def _handle_version_notification(self, event: Events.PackageManager.VersionNotification) -> None:
        self.detect_xxmi_dll_identity()

    def detect_xxmi_dll_identity(self):
        self.xxmi_dll_identity = self.xxmi_injector.identify_dll()

    def install_model_importer(self, event: Events.ModelImporter.Install):
        # Assert installation path
        try:
            game_path, game_exe_path = self.get_game_paths()
        except UserWarning:
            return
        except Exception as e:
            raise ValueError(L('error_model_importer_installation_failed', """
                {importer} Installation Failed:
                {error_text}
            """).format(importer=Config.Launcher.active_importer, error_text=e)) from e

        # Install importer package and its requirements
        Events.Fire(Events.Application.Update(packages=[Config.Launcher.active_importer], force=True, reinstall=True))

    def require_launch(self, game_launch: GameLaunch) -> None:
        game_platform = LAUNCH_TO_PLATFORM.get(game_launch, None)

        if game_platform is None:
            return None

        platform_manager = self.platform_registry.get_platform_manager(game_platform)

        if platform_manager is None:
            raise ValueError(L("steam_client_not_found_error", """
                Cannot find an installed {game_platform} client
            """).format(game_platform=game_platform.value))

        game = Config.Active.Importer.game

        if not platform_manager.is_installed(game):
            raise ValueError(L("platform_game_not_found_error", """
                Cannot find {game} installed in the {game_platform} library
            """).format(game=game.value, game_platform=game_platform.value))

        return None

    def get_game_path(self) -> Path | None:
        match Config.Active.Importer.game_launch:
            case GameLaunch.DIRECT:
                game_path = Config.Active.Importer.game_folder

            case GameLaunch.STEAM:
                steam_manager = self.platform_registry.get_platform_manager(GamePlatform.STEAM)
                game_path = steam_manager.get_game_path(Config.Active.Importer.game)

            case GameLaunch.EPIC_GAMES:
                epic_manager = self.platform_registry.get_platform_manager(GamePlatform.EPIC)
                game_path = epic_manager.get_game_path(Config.Active.Importer.game)

            case GameLaunch.CUSTOM | GameLaunch.MANUAL:
                return None

        try:
            return self.model_importer.validate_game_path(game_path)
        except Exception as e:
            match Config.Active.Importer.game_launch:
                # DIRECT must always pass folder validation.
                case GameLaunch.DIRECT:
                    raise e
                # Allow invalid game folder for STEAM and EPIC_GAMES launches, since in this case it's optional.
                # STEAM is expected to pass folder validation unless game folder structure is unknown.
                # EPIC_GAMES is expected to pass folder validation unless game folder is relocated.
                case GameLaunch.STEAM | GameLaunch.EPIC_GAMES:
                    return None

    def get_game_paths(self) -> tuple[Path | None, Path | None]:
        game_path, game_exe_path = None, None

        try:
            game_path = self.get_game_path()

            if game_path is not None:
                self._validate_installation_path(game_path)
                game_exe_path = self.model_importer.validate_game_exe_path(game_path)
        except:
            if Config.Active.Importer.game_launch == GameLaunch.DIRECT:
                game_folder, game_path, game_exe_path = self.model_importer.detect_game_paths()
                Config.Active.Importer.game_folder = str(game_folder)
            else:
                pass

        return game_path, game_exe_path

    @staticmethod
    def get_game_exe_name(game_exe_path: Path | None) -> str:
        if Config.Active.Importer.game_process_exe_enabled:
            return Config.Active.Importer.game_process_exe

        if game_exe_path is not None:
            return game_exe_path.name

        return next(field.default for field in fields(type(Config.Active.Importer)) if field.name == "game_process_exe")

    def build_cmd_args(
        self,
        cfg: AppConfig,
        game_exe_path: Path | None = None,
        get_value = lambda x: x
    ) -> str:
        cmd_parts = []

        if get_value(cfg.Active.Importer.game_launch) == GameLaunch.STEAM:
            if (
                get_value(cfg.Active.Importer.game) == Game.ZENLESS_ZONE_ZERO
                and get_value(cfg.Active.Importer.skip_platform_game_launcher)
            ):
                if not game_exe_path:
                    game_path, game_exe_path = self.get_game_paths()
                if game_exe_path:
                    cmd_parts.append(f'"{game_exe_path.resolve()}" && %command%')

        if get_value(cfg.Active.Importer.d3d11_mode_cmd_args):
            cmd_parts.append(get_value(cfg.Active.Importer.d3d11_mode_cmd_args))

        if get_value(cfg.Active.Importer.use_launch_options):
            cmd_parts.append(get_value(cfg.Active.Importer.launch_options).replace('\\', '/'))

        return ' '.join(cmd_parts)

    @staticmethod
    def _get_cmd_arg_name(arg: str) -> str | None:
        match = re.match(r"^-{1,2}([^\s=]+)(?:=.*)?$", arg.strip())
        return match.group(1) if match else None

    @staticmethod
    def _get_cmd_arg_names(cmd: str) -> set[str]:
        pattern = re.compile(r"(?<!\S)-{1,2}([^\s=]+)(?==|\s|$)")
        return {match.group(1) for match in pattern.finditer(cmd)}

    def ensure_game_close(self):
        game_path, game_exe_path = self.get_game_paths()

        game_exe_name = self.get_game_exe_name(game_exe_path)

        self._ensure_game_close(game_exe_name)

    def launch(self, extra_args: list[str]):
        # region Game Executable

        self.require_launch(Config.Active.Importer.game_launch)

        game_path, game_exe_path = self.get_game_paths()

        game_exe_name = self.get_game_exe_name(game_exe_path)

        self._ensure_game_close(game_exe_name)

        game_platform = LAUNCH_TO_PLATFORM.get(Config.Active.Importer.game_launch, None)
        platform_manager = self.platform_registry.get_platform_manager(game_platform) if game_platform else None

        # endregion

        Events.Fire(Events.Application.StatusUpdate(
            status=L('status_resolving_launch_context', 'Resolving {game} launch context...').format(
                game=Config.Active.Importer.game.value,
            ))
        )

        # region Process Flags

        # process_flags = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_DEFAULT_ERROR_MODE
        # process_flags = subprocess.DETACHED_PROCESS
        process_flags = 0

        if Config.Active.Importer.start_method == StartMethod.NATIVE:
            process_flags |= ProcessPriorityClass(Config.Active.Importer.process_priority).get_process_flag()

        # endregion

        # region Console Command Arguments

        cmd_args = self.build_cmd_args(Config.Config, game_exe_path)

        # endregion

        # region Launch Context

        match Config.Active.Importer.game_launch:
            case GameLaunch.DIRECT:
                target = ExecutableLaunch(
                    exe_path=game_exe_path,
                    cmd_args=cmd_args,
                )
            case GameLaunch.STEAM | GameLaunch.EPIC_GAMES:
                target = ExecutableLaunch(
                    exe_path=game_exe_path or Path(game_exe_name),
                    cmd_args=cmd_args,
                )
            case GameLaunch.CUSTOM:
                target = CommandLaunch(
                    cmd=Config.Active.Importer.custom_launch,
                )
            case GameLaunch.MANUAL:
                target = CommandLaunch(
                    cmd="",
                )

        launch_context = LaunchContext(
            start_method=Config.Active.Importer.start_method,
            process_name=game_exe_path.name if game_exe_path else game_exe_name,
            target=target,
            work_dir=game_exe_path.parent if game_exe_path else None,
            process_flags=process_flags,
        )

        self.model_importer.override_launch_context(launch_context, game_path, game_exe_path)

        # Proxy extra args only when the argument name is not already present.
        if extra_args and isinstance(launch_context.target, ExecutableLaunch):
            arg_names = self._get_cmd_arg_names(launch_context.target.cmd_args)

            for extra_arg in extra_args:
                arg_name = self._get_cmd_arg_name(extra_arg)
                if arg_name and arg_name not in arg_names:
                    launch_context.target.cmd_args += ' ' + extra_arg
                    arg_names.add(arg_name)

        # endregion

        # region Pre-Launch Routine

        if Config.Active.Importer.is_xxmi_dll_used():

            Events.Fire(Events.Application.StatusUpdate(
                status=L('status_configuring', 'Configuring {entity}...').format(
                    entity=Config.Launcher.active_importer,
                ))
            )

            # Configure migoto package.
            self.xxmi_injector.run_pre_launch(launch_context)

            self.detect_xxmi_dll_identity()

            # Configure model importer package.
            self.model_importer.run_pre_launch(launch_context)

            # Write configured settings to main 3dmigoto ini file
            if Config.Active.Migoto.manage_xxmi_dll_config:
                if self.xxmi_dll_identity and self.xxmi_dll_identity.fork == MigotoFork.XXMI:
                    xxmi_dll_version = self.xxmi_dll_identity.version
                else:
                    xxmi_dll_version = None
                self.model_importer.update_d3dx_ini(
                    game_exe_name=launch_context.process_name,
                    xxmi_dll_version=xxmi_dll_version,
                )

            # Optimize ini files in Mods and ShaderFixes folders
            Events.Fire(Events.ModelImporter.OptimizeMods())

        # Configure game settings.
        Events.Fire(Events.Application.StatusUpdate(
            status=L('status_configuring', 'Configuring {entity}...').format(
                entity=Config.Active.Importer.game.value,
            ))
        )
        self.model_importer.configure_game_settings(game_path, game_exe_path)

        # Configure Steam game Launch Options.
        if Config.Active.Importer.configure_platform_launch_options:
            if Config.Active.Importer.game_launch == GameLaunch.STEAM:
                launch_options = platform_manager.get_launch_options(Config.Active.Importer.game)
                if launch_options != cmd_args:
                    Events.Fire(Events.Application.StatusUpdate(
                        status=L('status_configuring_launch_options', 'Configuring {game} Launch Options on {platform}...').format(
                            game=Config.Active.Importer.game.value,
                            platform=Config.Active.Importer.game_launch.value,
                        ))
                    )
                    platform_manager.set_launch_options(Config.Active.Importer.game, cmd_args)

        # endregion

        # region Start & Inject Sequence

        Events.Fire(Events.Application.StatusUpdate(
            status=L('status_starting', 'Starting {entity}...').format(
                entity=Config.Active.Importer.game.value,
            ))
        )

        self.notify_d3d11_mode_required()

        inject_dll_paths = []
        if Config.Active.Importer.extra_libraries_enabled:
            inject_dll_paths.extend(Config.Active.Importer.extra_dll_paths)

        if Config.Active.Importer.xxmi_dll_inject_mode != InjectMode.SKIP or inject_dll_paths:

            injector_context = InjectorContext(
                injector_path=self.xxmi_injector.package_path / '3dmloader.dll',
                process_name=launch_context.process_name,
                use_hook=Config.Active.Importer.xxmi_dll_inject_mode == InjectMode.HOOK,
                xxmi_dll_path=Config.Active.Importer.importer_path / 'd3d11.dll',
                inject_dll_paths=list(Config.Active.Importer.extra_dll_paths) if Config.Active.Importer.extra_libraries_enabled else [],
            )

            # Start game (or wait for manual start) and inject DLLs to game process.
            # * For HOOK mode, injector setup is happening before game start for SetWindowsHookEx.
            # * For INJECT mode, injector waits for game process to spawn and modifies DLL path with WriteProcessMemory.
            with MigotoInjector(injector_context) as injector:
                self._start_game_exe(launch_context, platform_manager)
                injector.run()
                self.wait_for_window(launch_context)
                injector.verify()

        else:
            # Start game without injecting anything.
            self._start_game_exe(launch_context, platform_manager)
            self.wait_for_window(launch_context)

        # endregion

        # Wait a pi more for window to maximize.
        time.sleep(3.141592653589793)

    @staticmethod
    def notify_d3d11_mode_required():
        if Config.Active.Importer.d3d11_mode_cmd_args_warned:
            return

        if Config.Active.Importer.game_launch != GameLaunch.EPIC_GAMES:
            return

        if Config.Active.Importer.game not in {Game.WUTHERING_WAVES, Game.ARKNIGHTS_ENDFIELD}:
            return

        Events.Fire(Events.Application.ShowWarning(
            title=L('message_title_d3d11_warning', "DirectX 11 Reminder"),
            message=L('message_text_d3d11_warning', """
                **{importer}** requires **DirectX 11** to function.

                Once the **official launcher** opens, please make sure to **enable the DirectX 11 mode checkbox** in the **bottom-right corner** of the launcher window.
            """).format(
                importer=Config.Launcher.active_importer,
            ),
            confirm_text=L('message_button_ok', 'OK'),
            modal=True,
        ))

        Config.Active.Importer.d3d11_mode_cmd_args_warned = True

    @staticmethod
    def wait_for_window(launch_context: LaunchContext):
        Events.Fire(Events.Application.WaitForProcess(process_name=launch_context.process_name))

        manager = ProcessManager(launch_context)

        window_found = manager.wait_until_running(
            timeout=Config.Active.Importer.process_timeout,
            wait_for_window=True
        )

        if not window_found:
            raise ValueError(L('error_migoto_game_detection_timeout', """
                Failed to detect window of game process {process_name}!

                If game window takes more than {start_timeout} seconds to appear, adjust **Timeout** in **General Settings**.

                If game crashed, try to follow the [Crash Isolation Checklist]({checklist_link}).
            """).format(
                process_name=launch_context.process_name,
                importer=Config.Launcher.active_importer,
                start_timeout=Config.Active.Importer.process_timeout,
                checklist_link='https://github.com/SpectrumQT/XXMI-Launcher/blob/main/.github/ISSUE_TEMPLATE/game-crash-report.md#-crash-isolation-checklist'
            ))

    @staticmethod
    def _start_game_exe(
        launch_context: LaunchContext,
        platform_manager: GamePlatformProtocol | None = None
    ) -> None:

        match Config.Active.Importer.game_launch:
            case GameLaunch.STEAM:
                platform_manager.launch(Config.Active.Importer.game, "")

            case GameLaunch.EPIC_GAMES:
                platform_manager.launch(Config.Active.Importer.game, launch_context.target.cmd_args)

            case GameLaunch.MANUAL:
                log.debug(f'Waiting for user to start the game process {launch_context.process_name}...')

            case _:
                # Start game exe.
                Events.Fire(Events.Application.StartGameExe(process_name=launch_context.process_name))
                manager = ProcessManager(launch_context)
                manager.start()

    @staticmethod
    def _ensure_game_close(process_name: str):
        Events.Fire(Events.Application.StatusUpdate(status=L('status_ensuring_game_closed', 'Ensuring the game is closed...')))

        manager = ProcessManager(Path(process_name))

        while manager.is_running():
            # Terminate the game automatically.
            if not manager.stop(timeout=5):
                # Ask user to close the game manually.
                user_response = Events.Call(Events.Application.ShowWarning(
                    modal=True,
                    message=L('message_text_game_stop_failed', """
                        Failed to stop {process_name}!
    
                        Please close the game manually and press [OK] to continue.
                    """).format(process_name=process_name),
                    confirm_text=L('message_button_ok', 'OK'),
                    cancel_text=L('message_button_abort', 'Abort'),
                ))

                # Return to main launcher window on `Abort`.
                if user_response is False:
                    raise UserWarning

            # Wait a pi more for files to unlock.
            time.sleep(3.141592653589793)

    @staticmethod
    def _validate_installation_path(game_path: Path) -> None:
        # Skip installation locations check for Linux
        if os.name != 'nt' or any(x in os.environ for x in ['WINE', 'WINEPREFIX', 'WINELOADER']):
            return

        # Ensure that user didn't install the launcher to the game exe location
        if str(game_path) in str(Paths.App.Root):
            raise ValueError(L('error_launcher_in_game_folder', """

                Launcher must be installed outside of the game folder!

                Please reinstall the launcher to another location.
            """))

        # Ensure that user didn't set a model importer folder to the game exe location
        if str(game_path) in str(Config.Active.Importer.importer_path):
            raise ValueError(L('error_model_importer_in_game_folder', """
                
                {importer} Folder must be located outside of the Game Folder!
                
                Please chose another location for Settings > {importer} > {importer} Folder.
            """).format(importer=Config.Launcher.active_importer))


Launcher = GameLauncher()
