import logging
import os
import sys
import shutil
import winreg
import ctypes
import winshell
import pythoncom
import re
import time

from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import Package, PackageMetadata
from core.locale_manager import T, L

from core.utils.ini_handler import IniHandler, IniHandlerSettings

log = logging.getLogger(__name__)


class SettingType(Enum):
    Constant = 'constant'
    Bool = 'bool'
    Map = 'map'


@dataclass
class ModelImporterEvents:
    @dataclass
    class Install:
        pass

    @dataclass
    class StartGame:
        pass

    @dataclass
    class ValidateGameFolder:
        game_folder: str

    @dataclass
    class CreateShortcut:
        pass

    @dataclass
    class DetectGameFolder:
        pass


@dataclass
class ModelImporterConfig:
    package_name: str = ''
    importer_folder: str = ''
    game_folder: str = ''
    overwrite_ini: bool = True
    process_start_method: str = 'Native'
    xxmi_dll_init_delay: int = 0
    process_priority: str = 'Normal'
    window_mode: str = 'Borderless'
    run_pre_launch_enabled: bool = False
    run_pre_launch: str = ''
    run_pre_launch_signature: str = ''
    run_pre_launch_wait: bool = True
    custom_launch_enabled: bool = False
    custom_launch: str = ''
    custom_launch_signature: str = ''
    custom_launch_inject_mode: str = 'Hook'
    run_post_load_enabled: bool = False
    run_post_load: str = ''
    run_post_load_signature: str = ''
    run_post_load_wait: bool = True
    extra_libraries_enabled: bool = False
    extra_libraries: str = ''
    extra_libraries_signature: str = ''
    deployed_migoto_signatures: Dict[str, str] = field(default_factory=lambda: {})
    shortcut_deployed: bool = False
    d3dx_ini: Dict[
        str, Dict[str, Dict[str, Union[str, int, float, Dict[str, Union[str, int, float]]]]]
    ] = field(default_factory=lambda: {})
    configure_game: bool = True
    launch_count: int = -1

    @property
    def importer_path(self) -> Path:
        importer_path = Path(self.importer_folder)
        if importer_path.is_absolute():
            return importer_path
        else:
            return Paths.App.Root / importer_path

    @property
    def extra_dll_paths(self) -> List[Path]:
        dll_paths = []
        for dll_path in self.extra_libraries.split('\n'):
            if len(dll_path) == 0:
                continue
            dll_path = Path(dll_path.strip())
            if not dll_path.is_absolute():
                dll_path = Paths.App.Root / dll_path
            if dll_path.is_file():
                dll_paths.append(dll_path)
            else:
                raise ValueError(T('model_importer_extra_library_not_found',
                                   f'Failed to inject extra library {dll_path}:\nFile not found!\nPlease check Advanced Settings -> Inject Libraries.'))
        return dll_paths


class ModelImporterCommandFileSection(Enum):
    PreInstall = 'PreInstall'
    PostInstall = 'PostInstall'
    PreLaunch = 'PreLaunch'


class ModelImporterCommandFileHandler:
    def __init__(self, ini_path):
        self.ini_path = ini_path
        self.ini = None
        self.load_ini()

    def load_ini(self):
        if not self.ini_path.is_file():
            return

        with open(self.ini_path, 'r', encoding='utf-8') as f:
            self.ini = IniHandler(IniHandlerSettings(option_value_spacing=True, ignore_comments=False), f)

    def execute_command_section(self, cmd_section: ModelImporterCommandFileSection):
        if self.ini is None:
            return

        section = self.ini.get_section(cmd_section.value)

        if section is None:
            return

        supported_commands = {
            'delete': self.cmd_delete
        }

        for (name, value, flag_modified, comments, inline_comment) in section.options:
            command_handler = supported_commands.get(name, None)
            if command_handler is None:
                raise ValueError(T('model_importer_unknown_command', f'Unknown command {name}!'))
            try:
                command_handler(value)
            except Exception as e:
                raise ValueError(T('model_importer_command_execution_failed',
                                   'Failed to execute `{} = {}` of auto_update.xcmd!:\n{}').format(name, value,
                                                                                                   str(e))) from e

    @staticmethod
    def cmd_delete(path: str):
        # Remove any `.` or `..` parts from path for security reasons
        parts = Path(path).parts
        non_dots_parts = []
        for part in parts:
            if part != '..' and part != '.':
                non_dots_parts.append(part)
        path = Path(*non_dots_parts)

        # Limit removal scope to Core and ShaderFixes folders
        valid_roots = ['Core', 'ShaderFixes']
        path_root = non_dots_parts[0]
        if path_root.lower() not in [x.lower() for x in valid_roots]:
            raise ValueError(T('model_importer_removal_scope_restricted',
                               f'File or folder removal is allowed only from Core or ShaderFixes folder!'))

        # Forbid removal of entire Core or ShaderFixes folder for security reasons
        if len(non_dots_parts) == 1:
            raise ValueError(T('model_importer_removal_forbidden',
                               f'Explicit removal of entire Core or ShaderFixes folder is not allowed!'))

        # Execute removal for given path
        path = Config.Active.Importer.importer_path.joinpath(path)
        if path.is_file():
            log.debug(f'Removing file {path}...')
            Paths.assert_file_write(path)
            path.unlink()
        elif path.is_dir():
            log.debug(f'Removing folder {path}...')
            Paths.assert_path(path)
            shutil.rmtree(path)


class ModelImporterPackage(Package):
    def __init__(self, metadata: PackageMetadata):
        super().__init__(metadata)
        self.backups_path = None
        self.use_hook: bool = True
        self.ini = None

    def validate_game_path(self, game_folder) -> Path:
        game_path = Path(game_folder)
        if not str(game_folder):
            raise ValueError(
                T('model_importer_game_folder_not_specified', f'Game installation folder is not specified!'))
        if not game_path.is_absolute() or not game_path.is_dir():
            raise ValueError(
                T('model_importer_game_folder_not_found', f'Specified game installation folder is not found!'))
        return game_path

    def validate_game_exe_path(self, game_path: Path) -> Path:
        raise NotImplementedError

    def load(self):
        self.subscribe(Events.ModelImporter.Install, self.install)
        self.subscribe(Events.ModelImporter.StartGame, self.start_game)
        self.subscribe(Events.ModelImporter.ValidateGameFolder, lambda event: self.validate_game_folder(event))
        self.subscribe(Events.ModelImporter.CreateShortcut, lambda event: self.create_shortcut())
        self.subscribe(Events.ModelImporter.DetectGameFolder, lambda event: self.detect_game_paths(supress_errors=True))
        super().load()
        if self.get_installed_version() != '' and not Config.Active.Importer.shortcut_deployed:
            self.create_shortcut()

    def unload(self):
        self.unsubscribe()
        super().unload()

    def validate_game_folder(self, event):
        game_path = self.validate_game_path(event.game_folder)
        self.validate_game_exe_path(game_path)
        return game_path

    def validate_game_folders(self, game_folders: List[Path]):
        cache, known_paths = [], []
        for game_folder in set(game_folders):
            try:
                game_path = self.validate_game_path(game_folder)
                exe_path = self.validate_game_exe_path(game_path)
                mod_time = exe_path.stat().st_mtime
                if game_path in known_paths:
                    continue
                known_paths.append(game_path)
                cache.append((game_folder, mod_time, game_path, exe_path))
            except:
                continue
        cache.sort(key=lambda data: data[1], reverse=True)
        return cache

    def notify_game_folder_detection_failure(self):
        user_requested_settings = Events.Call(Events.Application.ShowError(
            message=T('model_importer_game_detection_failed',
                      f'Automatic detection of the game installation failed!\n\n'
                      f'Please configure it manually with Game Folder option of General Settings.'),
            confirm_text=L('model_importer_open_settings_button', 'Open Settings'),
            cancel_text=L('model_importer_cancel_button', 'Cancel'),
            modal=True,
        ))

        if user_requested_settings:
            Events.Fire(Events.Application.OpenSettings())

    def notify_game_folder_detection(self, game_folders_index):
        if len(game_folders_index) == 1:
            game_folder_id = 0
            user_confirmed_game_folder = Events.Call(Events.Application.ShowInfo(
                message=T('model_importer_game_detected_single',
                          'Detected game installation:\n\n{}\n\nPlease check if it is desired Game Folder or change it in General Settings.').format(
                    game_folders_index[0]),
                confirm_text=L('model_importer_confirm_button', 'Confirm'),
                cancel_text=L('model_importer_open_settings_button', 'Open Settings'),
                modal=True,
            ))
            if user_confirmed_game_folder is None:
                user_confirmed_game_folder = True
        else:
            (user_confirmed_game_folder, game_folder_id) = Events.Call(Events.Application.ShowWarning(
                message=T('model_importer_game_detected_multiple', f'Detected game installations:\n\n'
                                                                   f'Select desired Game Folder from the list below or set it in General Settings:\n'),
                confirm_text=L('model_importer_confirm_button', 'Confirm'),
                cancel_text=L('model_importer_open_settings_button', 'Open Settings'),
                radio_options=game_folders_index,
                modal=True,
            ))
        return user_confirmed_game_folder, game_folder_id

    def notify_game_folder_not_configured(self):
        user_requested_settings = Events.Call(Events.Application.ShowError(
            message=T('model_importer_game_folder_not_configured', f'Game installation folder is not configured!\n\n'
                                                                   f'Please set it with Game Folder option of General Settings.'),
            confirm_text=L('model_importer_open_settings_button', 'Open Settings'),
            cancel_text=L('model_importer_cancel_button', 'Cancel'),
            modal=True,
        ))

        if user_requested_settings:
            Events.Fire(Events.Application.OpenSettings())

    def detect_game_paths(self, supress_errors=False):

        try:

            Events.Fire(Events.Application.StatusUpdate(
                status=L('model_importer_autodetecting_game', 'Autodetecting game installation folder...')))

            # Try to automatically detect the game folder using search algo dedicated for given game
            # Those results are inaccurate as algos try to parse as much path-like strings as possible
            game_folders_candidates = self.autodetect_game_folders()

            # Exclude folders not matching the expected file structure
            # Results are sorted based on game exe last modification time (with latest being at 0 index)
            game_folders = self.validate_game_folders(game_folders_candidates)

            # Notify user if there are no game folders detected
            if len(game_folders) == 0:
                self.notify_game_folder_detection_failure()
                # User is already notified, lets skip error popup
                raise UserWarning

            for data in game_folders:
                log.debug(f'Selected game folder: {data[0]} (modified: {datetime.fromtimestamp(data[1])})')

            # Notify user if about game folder detection, ask which to use if there are more than 1 folder found
            game_folders_index = [x[0] for x in game_folders]
            (user_confirmed_game_folder, game_folder_id) = self.notify_game_folder_detection(game_folders_index)
            if user_confirmed_game_folder is None:
                # User neither confirmed detection result nor decided to open settings
                # With multiple game installations detected it might end up miserably, lets show them error
                raise Exception

            # Set folder with selected game_folder_id as game folder
            game_folder, mod_time, game_path, game_exe_path = game_folders[game_folder_id]

            log.debug(f'Selected game folder: {game_folder} (modified: {datetime.fromtimestamp(mod_time)})')

            # User decided to open Settings
            if not user_confirmed_game_folder:
                Events.Fire(Events.Application.OpenSettings())
                # User is already notified, lets skip error popup
                raise UserWarning

        except UserWarning:
            # Upcast UserWarning
            raise UserWarning

        except Exception as e:
            if supress_errors:
                return
            self.notify_game_folder_not_configured()
            # User is already notified, lets skip error popup
            raise UserWarning

        return game_folder, game_path, game_exe_path

    def get_game_paths(self):
        try:
            game_path = self.validate_game_path(Config.Active.Importer.game_folder)
            game_exe_path = self.validate_game_exe_path(game_path)
        except:
            game_folder, game_path, game_exe_path = self.detect_game_paths()
            Config.Active.Importer.game_folder = str(game_folder)

        # Skip installation locations check for Linux
        if os.name != 'nt' or any(x in os.environ for x in ['WINE', 'WINEPREFIX', 'WINELOADER']):
            return game_path, game_exe_path

        # Ensure that user didn't install the launcher to the game exe location
        if str(game_exe_path.parent) in str(Paths.App.Root):
            raise ValueError(T('model_importer_launcher_in_game_folder', f'\n'
                                                                         f'Launcher must be installed outside of the game folder!\n\n'
                                                                         f'Please reinstall the launcher to another location.'))

        # Ensure that user didn't set a model importer folder to the game exe location
        if str(game_exe_path.parent) in str(Config.Active.Importer.importer_path):
            raise ValueError(T('model_importer_importer_in_game_folder',
                               '\n{} Folder must be located outside of the Game Folder!\n\nPlease chose another location for Settings > {} > {} Folder.').format(
                Config.Launcher.active_importer, Config.Launcher.active_importer, Config.Launcher.active_importer))

        return game_path, game_exe_path

    def install_latest_version(self, clean):
        Events.Fire(Events.PackageManager.InitializeInstallation())

        self.initialize_backup()
        d3dx_ini_path = Config.Active.Importer.importer_path / 'd3dx.ini'
        self.backup(d3dx_ini_path)

        xxmi_cmd_handler = ModelImporterCommandFileHandler(self.downloaded_asset_path / 'Core' / 'auto_update.xcmd')
        xxmi_cmd_handler.execute_command_section(ModelImporterCommandFileSection.PreInstall)

        self.move_contents(self.downloaded_asset_path, Config.Active.Importer.importer_path)

        xxmi_cmd_handler = ModelImporterCommandFileHandler(
            Config.Active.Importer.importer_path / 'Core' / 'auto_update.xcmd')
        xxmi_cmd_handler.execute_command_section(ModelImporterCommandFileSection.PostInstall)

        if not Config.Active.Importer.overwrite_ini:
            self.restore(d3dx_ini_path)

        if not Config.Active.Importer.shortcut_deployed:
            self.create_shortcut()

    def install(self, event):
        # Assert installation path
        try:
            self.get_game_paths()
        except UserWarning:
            return
        except Exception as e:
            raise ValueError(T('model_importer_installation_failed', '{} Installation Failed:\n{}').format(
                Config.Launcher.active_importer, e)) from e
        # Install importer package and its requirements
        Events.Fire(Events.Application.Update(packages=[Config.Launcher.active_importer], force=True, reinstall=True))

    def initialize_game_launch(self, game_path: Path):
        raise NotImplementedError

    def update_d3dx_ini(self, game_exe_path: Path):
        Events.Fire(Events.Application.StatusUpdate(status=L('model_importer_updating_ini', 'Updating d3dx.ini...')))

        ini_path = Config.Active.Importer.importer_path / 'd3dx.ini'

        Events.Fire(Events.Application.VerifyFileAccess(path=ini_path, write=True))

        log.debug(f'Reading d3dx.ini...')
        with open(ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(ignore_comments=False), f)

        # Set default game exe as target, can be overridden via XXMI Launcher Config.json:
        # 1. Locate "Importers" > "GIMI" > "Importer" > "d3dx_ini"> "core" > "Loader"
        # 2. Add `"target": "GenshinImpact.exe",` line before `"loader": "XXMI Launcher.exe"`
        ini.set_option('Loader', 'target', game_exe_path.name)

        ini.set_option('System', 'dll_initialization_delay', Config.Active.Importer.xxmi_dll_init_delay)

        screen_width, screen_height = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
        ini.set_option('System', 'screen_width', screen_width)
        ini.set_option('System', 'screen_height', screen_height)

        self.set_default_ini_values(ini, 'core', SettingType.Constant)
        if Config.Active.Migoto.enforce_rendering:
            self.set_default_ini_values(ini, 'enforce_rendering', SettingType.Constant)
        self.set_default_ini_values(ini, 'calls_logging', SettingType.Bool, Config.Active.Migoto.calls_logging)
        self.set_default_ini_values(ini, 'debug_logging', SettingType.Bool, Config.Active.Migoto.debug_logging)
        self.set_default_ini_values(ini, 'mute_warnings', SettingType.Bool, Config.Active.Migoto.mute_warnings)
        self.set_default_ini_values(ini, 'enable_hunting', SettingType.Bool, Config.Active.Migoto.enable_hunting)
        self.set_default_ini_values(ini, 'dump_shaders', SettingType.Bool, Config.Active.Migoto.dump_shaders)

        if ini.is_modified():
            log.debug(f'Writing d3dx.ini...')
            with open(ini_path, 'w', encoding='utf-8') as f:
                f.write(ini.to_string())

        self.ini = ini

    def set_default_ini_values(self, ini: IniHandler, setting_name: str, setting_type: SettingType, setting_value=None):
        settings = Config.Active.Importer.d3dx_ini.get(setting_name, None)
        if settings is None:
            raise ValueError(T('model_importer_missing_setting', f'Config is missing {setting_name} setting!'))
        for section, options in settings.items():
            for option, values in options.items():

                key, value = None, None

                if setting_type == SettingType.Constant:
                    value = values
                elif setting_type == SettingType.Bool:
                    key = 'on' if setting_value else 'off'
                    value = values[key]
                elif setting_type == SettingType.Map:
                    key = setting_value
                    value = values[key]

                if value is None:
                    raise ValueError(T('model_importer_missing_value',
                                       f'Config is missing value for section `{section}` option `{option}` key `{key}`'))

                try:
                    ini.set_option(section, option, value)
                except Exception as e:
                    raise ValueError(T('model_importer_set_option_failed',
                                       f'Failed to set section {section} option {option} to {value}: {str(e)}')) from e

    def get_start_cmd(self, game_path: Path) -> Tuple[Path, List[str], Optional[str]]:
        game_exe_path = self.validate_game_exe_path(game_path)
        return game_exe_path, [], str(game_exe_path.parent)

    def start_game(self, event):
        # Ensure package integrity
        self.validate_package_files()

        # Execute commands from XXMI command file
        xxmi_cmd_handler = ModelImporterCommandFileHandler(
            Config.Active.Importer.importer_path / 'Core' / 'auto_update.xcmd')
        xxmi_cmd_handler.execute_command_section(ModelImporterCommandFileSection.PreLaunch)

        # Check if game location is properly configured
        game_path, game_exe_path = self.get_game_paths()

        # Write configured settings to main 3dmigoto ini file
        self.update_d3dx_ini(game_exe_path=game_exe_path)

        # Check for critical errors in Mods folder structure
        self.validate_mods_folder()

        # Execute initialization sequence of implemented importer
        self.initialize_game_launch(game_path)

        start_exe_path, start_args, work_dir = self.get_start_cmd(game_path)

        Events.Fire(Events.MigotoManager.StartAndInject(game_exe_path=game_exe_path, start_exe_path=start_exe_path,
                                                        start_args=start_args, work_dir=work_dir,
                                                        use_hook=self.use_hook))

    def reg_search_game_folders(self, game_exe_files: List[str]):
        paths = []

        reg_key_paths = [
            (winreg.HKEY_CLASSES_ROOT, 'Local Settings\\Software\\Microsoft\\Windows\\Shell\\MuiCache'),
            (winreg.HKEY_CURRENT_USER,
             'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FeatureUsage\\AppSwitched'),
            (winreg.HKEY_CURRENT_USER,
             'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FeatureUsage\\ShowJumpView'),
        ]

        for (key_type, sub_key) in reg_key_paths:
            try:
                with winreg.OpenKey(key_type, sub_key, 0, winreg.KEY_READ) as reg_key:
                    i = 0
                    while True:
                        try:
                            value_name, value_data, value_type = winreg.EnumValue(reg_key, i)
                            for game_exe in game_exe_files:
                                if game_exe in value_name:
                                    parts = value_name.split(game_exe)
                                    path = Path(parts[0])
                                    if path not in paths:
                                        paths.append(path)
                                        log.debug(f'Game folder candidate found in registry: {path}')
                                    break
                            i += 1
                        except OSError:
                            break
            except Exception:
                continue

        return paths

    def autodetect_game_folders(self) -> List[Path]:
        raise NotImplementedError

    def validate_package_files(self):
        ini_path = Config.Active.Importer.importer_path / 'd3dx.ini'
        if not ini_path.exists():
            user_requested_restore = Events.Call(Events.Application.ShowError(
                modal=True,
                confirm_text=L('model_importer_restore_button', 'Restore'),
                cancel_text=L('model_importer_cancel_button', 'Cancel'),
                message=T('model_importer_installation_damaged',
                          '{} installation is damaged!\nDetails: Missing critical file: {}!\nWould you like to restore {} automatically?').format(
                    Config.Launcher.active_importer, ini_path.name, Config.Launcher.active_importer),
            ))

            if not user_requested_restore:
                raise ValueError(
                    T('model_importer_missing_critical_file', 'Missing critical file: {}!').format(ini_path.name))

            Events.Fire(Events.Application.Update(no_thread=True, force=True, reinstall=True,
                                                  packages=[self.metadata.package_name]))

    def initialize_backup(self):
        backup_name = self.metadata.package_name + ' ' + datetime.now().strftime('%Y-%m-%d %H-%M-%S')
        self.backups_path = Paths.App.Backups / backup_name

    def backup(self, file_path: Path):
        if not file_path.exists():
            return
        Paths.verify_path(self.backups_path)
        shutil.copy2(file_path, self.backups_path / file_path.name)

    def restore(self, file_path: Path):
        backup_path = self.backups_path / file_path.name
        if not backup_path.exists():
            return
        shutil.copy2(backup_path, file_path)

    def create_shortcut(self):
        pythoncom.CoInitialize()
        with winshell.shortcut(
                str(Path(winshell.desktop()) / f'{Config.Launcher.active_importer} Quick Start.lnk')) as link:
            link.path = str(Path(sys.executable))
            link.description = str(
                L('model_importer_shortcut_description', 'Start game with {importer} and skip launcher load').format(
                    importer=Config.Launcher.active_importer))
            link.working_directory = str(Paths.App.Resources / 'Bin')
            link.arguments = f'--nogui --xxmi {Config.Launcher.active_importer}'
            link.icon_location = (
            str(Config.Config.theme_path / 'Shortcuts' / f'{Config.Launcher.active_importer}.ico'), 0)
        Config.Active.Importer.shortcut_deployed = True

    def get_ini_exclude_patterns(self):
        """
        Limited "support" of GLOB patterns.
        Supports patterns: `*substr*`, `substr*`, `*substr`, `substr`
        """
        result = []
        include_options = self.ini.get_section('Include').options
        for option_name, exclude_pattern, _, _, _ in include_options:
            exclude_pattern = exclude_pattern.lower()
            if option_name.lower() == 'exclude_recursive':
                if exclude_pattern[-1] == '*':
                    if exclude_pattern[0] == '*':
                        # Handles `*substr*` pattern (aka contains)
                        result.append((exclude_pattern[1:-1], lambda x, y: y in x))
                    else:
                        # Handles `substr*` pattern (aka starts with)
                        result.append((exclude_pattern[:-1], lambda x, y: x.startswith(y)))
                elif exclude_pattern[0] == '*':
                    # Handles `*substr` pattern (aka ends with)
                    result.append((exclude_pattern[1:], lambda x, y: x.endswith(y)))
                else:
                    # Handles `substr` pattern (aka exact match)
                    result.append((exclude_pattern, lambda x, y: x == y))
        return result

    def disable_duplicate_libraries(self, libs_path: Path):
        log.debug(f'Searching for duplicate libs...')
        mods_path = Config.Active.Importer.importer_path / 'Mods'
        Paths.verify_path(mods_path)

        mods_namespaces = self.index_namespaces(mods_path, self.get_ini_exclude_patterns())
        packaged_namespaces = self.index_namespaces(libs_path, [])

        log.debug(f'Deducing duplicate libs...')
        duplicate_ini_paths = []
        for mods_namespace, ini_paths in mods_namespaces.items():
            if mods_namespace in packaged_namespaces.keys():
                for ini_path in ini_paths:
                    duplicate_ini_paths.append(ini_path)

        if len(duplicate_ini_paths) == 0:
            return

        user_requested_disable = Events.Call(Events.Application.ShowError(
            modal=True,
            confirm_text=L('model_importer_disable_button', 'Disable'),
            cancel_text=L('model_importer_ignore_button', 'Ignore'),
            message=T('model_importer_duplicate_libraries',
                      'Your {importer} installation already includes some libraries present in the Mods folder!\n\nWould you like to disable following duplicates automatically (recommended)?\n\n{duplicates}').format(
                importer=Config.Launcher.active_importer,
                duplicates='\n'.join([f'Mods\\{x.relative_to(mods_path)}' for x in duplicate_ini_paths]))
        ))

        if not user_requested_disable:
            return

        for ini_path in duplicate_ini_paths:
            disabled_ini_path = ini_path.parent / f'DISABLED_{ini_path.name}'
            if disabled_ini_path.is_file():
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                disabled_ini_path = ini_path.parent / f'DISABLED_{ini_path.stem}_{timestamp}{ini_path.suffix}'
            ini_path.rename(disabled_ini_path)
            time.sleep(0.001)

    def validate_mods_folder(self):
        log.debug(f'Searching for invalid folders...')
        mods_path = Config.Active.Importer.importer_path / 'Mods'

        for entry in self.scan_directory(mods_path, self.get_ini_exclude_patterns()):

            if entry.is_file():
                path = Path(entry)
                if path.name == 'd3dx.ini':
                    user_requested_fix = Events.Call(Events.Application.ShowError(
                        modal=True,
                        confirm_text=L('model_importer_delete_file_button', 'Delete File'),
                        cancel_text=L('model_importer_abort_button', 'Abort'),
                        message=T('model_importer_ini_in_mods_folder',
                                  'Global config file d3dx.ini found inside the Mods folder:\n{path}\n\nIt is duplicate file that may cause glitches and crashes.\n\nWould you like to remove it?').format(
                            path=path.relative_to(Config.Active.Importer.importer_path.parent))
                    ))
                    if user_requested_fix:
                        path.unlink()
                    else:
                        raise ValueError(
                            T('model_importer_cannot_start_ini_in_mods', f'Cannot start with d3dx.ini in Mods folder!'))
                else:
                    if path.parent.name == 'ShaderFixes' and path.name in ['3dvision2sbs.ini', 'help.ini', 'mouse.ini',
                                                                           'upscale.ini']:
                        logging.warning(f'Automatically disabling illegitimate {path}...')
                        disabled_ini_path = path.parent / f'DISABLED_{path.name}'
                        if disabled_ini_path.is_file():
                            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                            disabled_ini_path = path.parent / f'DISABLED_{path.stem}_{timestamp}{path.suffix}'
                        path.rename(disabled_ini_path)
                        time.sleep(0.001)

    def index_namespaces(self, folder_path: Path, exclude_patterns):
        log.debug(f'Indexing namespaces for {folder_path}...')
        namespace_pattern = re.compile(r'namespace\s*=\s*(.*)')
        namespaces = {}

        for path in self.scan_directory(folder_path, exclude_patterns):
            if not path.is_file():
                continue

            path = Path(path)

            if not path.suffix == '.ini':
                continue

            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line_id, line in enumerate(f.readlines()):
                        stripped_line = line.strip().lower()
                        if not stripped_line:
                            continue
                        if stripped_line[0] == ';':
                            continue
                        result = namespace_pattern.findall(stripped_line)
                        if len(result) == 1:
                            namespace = result[0]
                            known_namespace = namespaces.get(namespace, None)
                            if known_namespace:
                                known_namespace.append(path)
                            else:
                                namespaces[namespace] = [path]
            except Exception as e:
                pass

        return namespaces

    def get_paths_from_hoyoplay(self, patterns: Union[re.Pattern, List[re.Pattern]], known_children: List[str] = None):
        hoyoplay_path = Path(os.getenv('APPDATA')).parent / 'Roaming' / 'Cognosphere' / 'HYP'
        paths = []
        if hoyoplay_path.is_dir():
            for root, dirs, files in hoyoplay_path.walk():
                for file in files:
                    if file == 'gamedata.dat':
                        file_path = root / file
                        paths += self.find_paths_in_file(file_path, patterns, known_children)
        return paths

    def find_paths_in_file(self, file_path: Path, patterns: Union[re.Pattern, List[re.Pattern]],
                           known_children: List[str] = None):
        paths = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = f.read()
                if isinstance(patterns, re.Pattern):
                    patterns = [patterns]
                if known_children is None:
                    known_children = []
                for pattern in patterns:
                    result = pattern.findall(data)
                    for string in result:
                        for child in known_children:
                            pos = string.rfind(child)
                            if pos != -1:
                                string = string[:pos]
                        path = Path(string)
                        if path not in paths:
                            paths.append(path)
        except Exception as e:
            log.debug(f'Failed to parse path from {file_path}:')
            log.exception(e)
        return paths

    def uninstall(self):
        log.debug(f'Uninstalling package {self.metadata.package_name}...')

        if self.package_path.is_dir():
            log.debug(f'Removing {self.package_path}...')
            shutil.rmtree(self.package_path)

        shortcut_path = Path(winshell.desktop()) / f'{self.metadata.package_name} Quick Start.lnk'
        if shortcut_path.is_file():
            log.debug(f'Removing {shortcut_path}...')
            shortcut_path.unlink()
