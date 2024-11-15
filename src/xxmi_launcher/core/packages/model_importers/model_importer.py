import logging
import os
import sys
import platform
import shutil
import winshell
import pythoncom
import re

from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import Package, PackageMetadata

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
class ModelImporterConfig:
    package_name: str = ''
    importer_folder: str = ''
    game_folder: str = ''
    launcher_theme: str = 'Default'
    overwrite_ini: bool = True
    process_priority: str = 'Normal'
    window_mode: str = 'Borderless'
    run_pre_launch_enabled: bool = False
    run_pre_launch: str = ''
    run_pre_launch_signature: str = ''
    run_pre_launch_wait: bool = True
    custom_launch_enabled: bool = False
    custom_launch: str = ''
    custom_launch_signature: str = ''
    custom_launch_inject_mode: str = 'Inject'
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

    @property
    def importer_path(self) -> Path:
        importer_path = Path(self.importer_folder)
        if importer_path.is_absolute():
            return importer_path
        else:
            return Paths.App.Root / importer_path

    @property
    def theme_path(self) -> Path:
        return Paths.App.Themes / self.launcher_theme

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
                raise ValueError(f'Failed to inject extra library {dll_path}:\nFile not found!\nPlease check Advanced Settings -> Inject Libraries.')
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
                raise ValueError(f'Unknown command {name}!')
            try:
                command_handler(value)
            except Exception as e:
                raise ValueError(f'Failed to execute `{name} = {value}` of auto_update.xcmd!:\n{str(e)}') from e

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
            raise ValueError(f'File or folder removal is allowed only from Core or ShaderFixes folder!')

        # Forbid removal of entire Core or ShaderFixes folder for security reasons
        if len(non_dots_parts) == 1:
            raise ValueError(f'Explicit removal of entire Core or ShaderFixes folder is not allowed!')

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
        if not game_path.is_absolute():
            raise ValueError(f'Game folder is not a valid path!')
        if not game_path.exists():
            raise ValueError(f'Game folder does not exist!')
        if not game_path.is_dir():
            raise ValueError(f'Game folder is not a directory!')
        return game_path

    def validate_game_exe_path(self, game_path: Path) -> Path:
        raise NotImplementedError

    def load(self):
        self.subscribe(Events.ModelImporter.Install, self.install)
        self.subscribe(Events.ModelImporter.StartGame, self.start_game)
        self.subscribe(Events.ModelImporter.ValidateGameFolder, lambda event: self.validate_game_path(event.game_folder))
        self.subscribe(Events.ModelImporter.CreateShortcut, lambda event: self.create_shortcut())
        super().load()
        try:
            game_path = self.validate_game_path(Config.Active.Importer.game_folder)
            self.validate_game_exe_path(game_path)
        except Exception as e:
            try:
                game_folder = self.autodetect_game_folder()
                game_path = self.validate_game_path(game_folder)
                self.validate_game_exe_path(game_path)
                Config.Active.Importer.game_folder = str(game_folder)
            except Exception as e:
                pass
        if self.get_installed_version() != '' and not Config.Active.Importer.shortcut_deployed:
            self.create_shortcut()

    def unload(self):
        self.unsubscribe()
        super().unload()

    def get_game_paths(self):
        try:
            game_path = self.validate_game_path(Config.Active.Importer.game_folder)
            game_exe_path = self.validate_game_exe_path(game_path)
        except Exception as e:
            try:
                game_folder = self.autodetect_game_folder()
                game_path = self.validate_game_path(game_folder)
                game_exe_path = self.validate_game_exe_path(game_path)
                Config.Active.Importer.game_folder = str(game_folder)
            except Exception as e:
                Events.Fire(Events.Application.OpenSettings())
                raise ValueError(f'\n'
                                 f'Failed to detect Game Folder!\n\n'
                                 f'Refer to tooltip of Settings > General > Game Folder for details.')

        # Skip installation locations check for Linux
        if platform.system() == 'Linux' or any(x in os.environ for x in ['WINE', 'WINEPREFIX', 'WINELOADER']):
            return game_path, game_exe_path

        # Ensure that user didn't install the launcher to the game exe location
        if str(game_exe_path.parent) in str(Paths.App.Root):
            raise ValueError(f'\n'
                             f'Launcher must be installed outside of the game folder!\n\n'
                             f'Please reinstall the launcher to another location.')

        # Ensure that user didn't set a model importer folder to the game exe location
        if str(game_exe_path.parent) in str(Config.Active.Importer.importer_path):
            raise ValueError(f'\n'
                             f'{Config.Launcher.active_importer} Folder must be located outside of the Game Folder!\n\n'
                             f'Please chose another location for Settings > {Config.Launcher.active_importer} > {Config.Launcher.active_importer} Folder.')

        return game_path, game_exe_path

    def install_latest_version(self, clean):
        Events.Fire(Events.PackageManager.InitializeInstallation())

        self.initialize_backup()
        d3dx_ini_path = Config.Active.Importer.importer_path / 'd3dx.ini'
        self.backup(d3dx_ini_path)

        xxmi_cmd_handler = ModelImporterCommandFileHandler(self.downloaded_asset_path / 'Core' / 'auto_update.xcmd')
        xxmi_cmd_handler.execute_command_section(ModelImporterCommandFileSection.PreInstall)

        self.move_contents(self.downloaded_asset_path, Config.Active.Importer.importer_path)

        xxmi_cmd_handler = ModelImporterCommandFileHandler(Config.Active.Importer.importer_path / 'Core' / 'auto_update.xcmd')
        xxmi_cmd_handler.execute_command_section(ModelImporterCommandFileSection.PostInstall)

        if not Config.Active.Importer.overwrite_ini:
            self.restore(d3dx_ini_path)

        if not Config.Active.Importer.shortcut_deployed:
            self.create_shortcut()

    def install(self, event):
        # Assert installation path
        try:
            self.get_game_paths()
        except Exception as e:
            raise ValueError(f'{Config.Launcher.active_importer} Installation Failed:\n{e}') from e
        # Install importer package and its requirements
        Events.Fire(Events.Application.Update(packages=[Config.Launcher.active_importer], force=True, reinstall=True))

    def initialize_game_launch(self, game_path: Path):
        raise NotImplementedError

    def update_d3dx_ini(self, game_exe_path: Path):
        Events.Fire(Events.Application.StatusUpdate(status='Updating d3dx.ini...'))

        ini_path = Config.Active.Importer.importer_path / 'd3dx.ini'

        Events.Fire(Events.Application.VerifyFileAccess(path=ini_path, write=True))

        log.debug(f'Reading d3dx.ini...')
        with open(ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(ignore_comments=False), f)

        # Set default game exe as target, can be overridden via XXMI Launcher Config.json:
        # 1. Locate "Importers" > "GIMI" > "Importer" > "d3dx_ini"> "core" > "Loader"
        # 2. Add `"target": "GenshinImpact.exe",` line before `"loader": "XXMI Launcher.exe"`
        ini.set_option('Loader', 'target', game_exe_path.name)

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
            raise ValueError(f'Config is missing {setting_name} setting!')
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
                    raise ValueError(f'Config is missing value for section `{section}` option `{option}` key `{key}')

                try:
                    ini.set_option(section, option, value)
                except Exception as e:
                    raise ValueError(f'Failed to set section {section} option {option} to {value}: {str(e)}') from e

    def get_start_cmd(self, game_path: Path) -> Tuple[Path, List[str], Optional[str]]:
        game_exe_path = self.validate_game_exe_path(game_path)
        return game_exe_path, [], str(game_exe_path.parent)

    def start_game(self, event):
        # Ensure package integrity
        self.validate_package_files()
        
        # Execute commands from XXMI command file
        xxmi_cmd_handler = ModelImporterCommandFileHandler(Config.Active.Importer.importer_path / 'Core' / 'auto_update.xcmd')
        xxmi_cmd_handler.execute_command_section(ModelImporterCommandFileSection.PreLaunch)

        # Check if game location is properly configured
        game_path, game_exe_path = self.get_game_paths()

        # Write configured settings to main 3dmigoto ini file
        self.update_d3dx_ini(game_exe_path=game_exe_path)

        # Execute initialization sequence of implemented importer
        self.initialize_game_launch(game_path)

        start_exe_path, start_args, work_dir = self.get_start_cmd(game_path)

        Events.Fire(Events.MigotoManager.StartAndInject(game_exe_path=game_exe_path, start_exe_path=start_exe_path,
                                                        start_args=start_args, work_dir=work_dir, use_hook=self.use_hook))

    def autodetect_game_folder(self) -> Path:
        raise NotImplementedError

    def validate_package_files(self):
        ini_path = Config.Active.Importer.importer_path / 'd3dx.ini'
        if not ini_path.exists():
            user_requested_restore = Events.Call(Events.Application.ShowError(
                modal=True,
                confirm_text='Restore',
                cancel_text='Cancel',
                message=f'{Config.Launcher.active_importer} installation is damaged!\n'
                        f'Details: Missing critical file: {ini_path.name}!\n'
                        f'Would you like to restore {Config.Launcher.active_importer} automatically?',
            ))

            if not user_requested_restore:
                raise ValueError(f'Missing critical file: {ini_path.name}!')

            Events.Fire(Events.Application.Update(no_thread=True, force=True, reinstall=True, packages=[self.metadata.package_name]))

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
        with winshell.shortcut(str(Path(winshell.desktop()) / f'{Config.Launcher.active_importer} Quick Start.lnk')) as link:
            link.path = str(Path(sys.executable))
            link.description = f'Start game with {Config.Launcher.active_importer} and skip launcher load'
            link.working_directory = str(Paths.App.Resources / 'Bin')
            link.arguments = f'--nogui --xxmi {Config.Launcher.active_importer}'
            link.icon_location = (str(Config.Active.Importer.theme_path / 'Shortcuts' / f'{Config.Launcher.active_importer}.ico'), 0)
        Config.Active.Importer.shortcut_deployed = True

    def disable_duplicate_libraries(self, libs_path: Path):
        log.debug(f'Searching for duplicate libs...')
        mods_path = Config.Active.Importer.importer_path / 'Mods'

        exclude_patterns = []
        include_options = self.ini.get_section('Include').options
        for option_name, exclude_pattern, _, _, _ in include_options:
            exclude_pattern = exclude_pattern.lower()
            if option_name.lower() == 'exclude_recursive':
                if exclude_pattern[-1] == '*':
                    exclude_patterns.append((exclude_pattern[:-1], lambda x, y: x.startswith(y)))
                elif exclude_pattern[0] == '*':
                    exclude_patterns.append((exclude_pattern[1:], lambda x, y: x.endswith(y)))
                else:
                    exclude_patterns.append((exclude_pattern, lambda x, y: x == y))

        mods_namespaces = self.index_namespaces(mods_path, exclude_patterns)
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
            confirm_text='Disable',
            cancel_text='Ignore',
            message=f'Your {Config.Launcher.active_importer} installation already includes some libraries present in the Mods folder!\n\n'
                    f'Would you like to disable following duplicates automatically (recommended)?\n'
                    f'\n' + '\n'.join([f'Mods\{x.relative_to(mods_path)}' for x in duplicate_ini_paths])
        ))

        if not user_requested_disable:
            return

        for ini_path in duplicate_ini_paths:
            ini_path.rename(ini_path.parent / f'DISABLED{ini_path.name}')

    def index_namespaces(self, folder_path: Path, exclude_patterns):
        log.debug(f'Indexing namespaces for {folder_path}...')
        namespace_pattern = re.compile(r'namespace\s*=\s*(.*)')
        namespaces = {}
        self.index_namespaces_recursive(folder_path, namespace_pattern, exclude_patterns, namespaces)
        return namespaces

    def index_namespaces_recursive(self, path: Path, namespace_pattern, exclude_patterns, namespaces):
        if path.is_dir():
            for exclude_str, exclude_func in exclude_patterns:
                if exclude_func(path.name.lower(), exclude_str):
                    return
            for sub_path in path.iterdir():
                self.index_namespaces_recursive(sub_path, namespace_pattern, exclude_patterns, namespaces)
        else:
            if not path.suffix == '.ini':
                return
            for exclude_str, exclude_func in exclude_patterns:
                if exclude_func(path.name.lower(), exclude_str):
                    return
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

    def uninstall(self):
        log.debug(f'Uninstalling package {self.metadata.package_name}...')

        if self.package_path.is_dir():
            log.debug(f'Removing {self.package_path}...')
            shutil.rmtree(self.package_path)

        shortcut_path = Path(winshell.desktop()) / f'{self.metadata.package_name} Quick Start.lnk'
        if shortcut_path.is_file():
            log.debug(f'Removing {shortcut_path}...')
            shortcut_path.unlink()
