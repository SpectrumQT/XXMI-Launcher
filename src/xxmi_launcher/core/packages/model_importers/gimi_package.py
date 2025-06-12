import re
import os
import logging
import shutil
import winreg
import json

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Union, Tuple, Optional, List
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import PackageMetadata

from core.utils.ini_handler import IniHandler, IniHandlerSettings
from core.utils.process_tracker import wait_for_process_exit, WaitResult, ProcessPriority
from core.packages.model_importers.model_importer import ModelImporterPackage, ModelImporterConfig
from core.packages.migoto_package import MigotoManagerConfig
from core.locale_manager import T, L

log = logging.getLogger(__name__)


@dataclass
class GIMIConfig(ModelImporterConfig):
    importer_folder: str = 'GIMI/'
    launch_options: str = ''
    process_start_method: str = 'Shell'
    d3dx_ini: Dict[
        str, Dict[str, Dict[str, Union[str, int, float, Dict[str, Union[str, int, float]]]]]
    ] = field(default_factory=lambda: {
        'core': {
            'Loader': {
                'loader': 'XXMI Launcher.exe',
            },
        },
        'enforce_rendering': {
            'Rendering': {
                'texture_hash': 0,
                'track_texture_updates': 0,
            },
        },
        'calls_logging': {
            'Logging': {
                'calls': {'on': 1, 'off': 0},
            },
        },
        'debug_logging': {
            'Logging': {
                'debug': {'on': 1, 'off': 0},
            },
        },
        'mute_warnings': {
            'Logging': {
                'show_warnings': {'on': 0, 'off': 1},
            },
        },
        'enable_hunting': {
            'Hunting': {
                'hunting': {'on': 2, 'off': 0},
            },
        },
        'dump_shaders': {
            'Hunting': {
                'marking_actions': {'on': 'clipboard hlsl asm regex', 'off': 'clipboard'},
            },
        },
    })
    unlock_fps: bool = False
    disable_dcr: bool = True
    enable_hdr: bool = False


@dataclass
class GIMIPackageConfig:
    Importer: GIMIConfig = field(
        default_factory=lambda: GIMIConfig()
    )
    Migoto: MigotoManagerConfig = field(
        default_factory=lambda: MigotoManagerConfig()
    )


class WindowMode(Enum):
    Windowed = 'Windowed'
    Borderless = 'Borderless'
    Fullscreen = 'Fullscreen'
    ExclusiveFullscreen = 'Exclusive Fullscreen'


class GIMIPackage(ModelImporterPackage):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='GIMI',
            auto_load=False,
            github_repo_owner='SilentNightSound',
            github_repo_name='GIMI-Package',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='GIMI-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAET5SWORxEdlJ3RXWIFiuwMX6oyZedz+DgaxtsbpWyxNQJDgIDj4uKLLJlvhRNpnkFEuQntgJKzJs0SpASBEguPOTE7VSnmp+x5uyDmsQsWzsRSAZip++a02jqR/K2j18H',
            exit_after_update=False,
            installation_path='GIMI/',
            requirements=['XXMI', 'GI-FPS-Unlocker'],
        ))

    def get_installed_version(self):
        try:
            return str(Version(Config.Importers.GIMI.Importer.importer_path / 'Core' / 'GIMI' / 'main.ini'))
        except Exception as e:
            return ''

    def autodetect_game_folders(self) -> List[Path]:
        paths = self.reg_search_game_folders(['GenshinImpact.exe', 'YuanShen.exe'])

        common_pattern = re.compile(r'([a-zA-Z]:[^:\"\']*Genshin[^:\"\']*)')
        known_children = ['GenshinImpact_Data']

        # "installPath":"D:\\Games\\Genshin Impact game"
        # "persistentInstallPath":"D:\\Games\\Genshin Impact game"
        hoyoplay_pattern = re.compile(r'\"(?:installPath|persistentInstallPath)\":\"([a-zA-Z]:[^:^\"]*)\"')

        paths += self.get_paths_from_hoyoplay([common_pattern, hoyoplay_pattern], known_children)

        # dll path: C:/Games/Genshin Impact/DATA/Genshin Impact game/GenshinImpact_Data\Plugins\EOSSDK-Win64-Shipping.dll
        # TelemetryInterface path:C:\Games\Genshin Impact\DATA\Genshin Impact game\GenshinImpact_Data\SDKCaches, level:2, dest:0
        output_log_pattern = re.compile(r'([a-zA-Z]:[^:\"\']*)(?:Plugins|SDKCaches|StreamingAssets|Persistent)')

        output_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'miHoYo' / 'Genshin Impact' / 'output_log.txt'
        paths += self.find_paths_in_file(output_log_path, [common_pattern, output_log_pattern], known_children)

        output_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'miHoYo' / 'Genshin Impact' / 'output_log.txt.last'
        paths += self.find_paths_in_file(output_log_path, [common_pattern, output_log_pattern], known_children)

        return paths

    def validate_game_exe_path(self, game_path: Path) -> Path:
        game_exe_path = game_path / 'GenshinImpact.exe'
        if not game_exe_path.is_file():
            game_exe_cn_path = game_path / 'YuanShen.exe'
            if not game_exe_cn_path.is_file():
                raise ValueError(T('gimi_game_exe_not_found', 'Game executable {} or {} not found!').format(game_exe_path.name, game_exe_cn_path.name))
            game_exe_path = game_exe_cn_path
        return game_exe_path

    def get_start_cmd(self, game_path: Path) -> Tuple[Path, List[str], Optional[str]]:
        if Config.Importers.GIMI.Importer.unlock_fps:
            game_exe_path = Paths.App.Resources / 'Packages' / 'GI-FPS-Unlocker' / 'unlockfps_nc.exe'
            work_dir_path = str(game_exe_path.parent)
        else:
            game_exe_path = self.validate_game_exe_path(game_path)
            work_dir_path = str(game_exe_path.parent)
        return game_exe_path, [], work_dir_path

    def initialize_game_launch(self, game_path: Path):
        if Config.Active.Importer.custom_launch_inject_mode != 'Bypass':
            self.update_gimi_ini()
            self.disable_duplicate_libraries(Config.Active.Importer.importer_path / 'Core' / 'GIMI' / 'Libraries')
            if Config.Importers.GIMI.Importer.configure_game:
                try:
                    # Set "Dynamic Character Resolution" to "Off"
                    self.update_dcr()
                except Exception as e:
                    raise ValueError(T('gimi_dcr_config_failed',
                          '{}\n\n'
                          'If nothing helps:\n'
                          '1. Disable `Configure Game Settings` in launcher\'s `General Settings`\n'
                          '2. Configure in-game `Graphics Settings` manually:\n'
                          '* Graphics > `Dynamic Character Resolution` must be `Off`.').format(e)) from e
        if Config.Importers.GIMI.Importer.unlock_fps:
            try:
                self.configure_fps_unlocker()
            except Exception as e:
                raise Exception(T('gimi_fps_unlocker_config_failed', 'Failed to configure FPS Unlocker!\n\n{}').format(str(e)))
        if Config.Importers.GIMI.Importer.enable_hdr:
            try:
                self.enable_hdr()
            except Exception as e:
                raise Exception(T('gimi_hdr_enable_failed', 'Failed to enable HDR!\n\n{}').format(str(e)))

    def update_gimi_ini(self):
        Events.Fire(Events.Application.StatusUpdate(status=L('gimi_updating_ini', 'Updating GIMI main.ini...')))

        gimi_ini_path = Config.Importers.GIMI.Importer.importer_path / 'Core' / 'GIMI' / 'main.ini'
        if not gimi_ini_path.exists():
            raise ValueError(T('gimi_ini_not_found', 'Failed to locate Core/GIMI/main.ini!'))

        Events.Fire(Events.Application.VerifyFileAccess(path=gimi_ini_path, write=True))

        # with open(gimi_ini_path, 'r', encoding='utf-8') as f:Add commentMore actions
        #     ini = IniHandler(IniHandlerSettings(option_value_spacing=True, ignore_comments=False), f)
        #
        # if ini.is_modified():
        #     log.debug(f'Writing main.ini...')
        #     with open(gimi_ini_path, 'w', encoding='utf-8') as f:Add commentMore actions
        #         f.write(ini.to_string())

    def update_dcr(self):
        log.debug(f'Checking DCR...')

        # Open GI registry settings key
        settings_key = None
        gi_reg_keys = [
            (winreg.HKEY_CURRENT_USER, 'SOFTWARE\\miHoYo\\Genshin Impact'),
            (winreg.HKEY_CURRENT_USER, 'SOFTWARE\\miHoYo\\原神'),
        ]
        for (key, subkey) in gi_reg_keys:
            try:
                settings_key = winreg.OpenKey(key, subkey, 0, winreg.KEY_ALL_ACCESS)
                break
            except FileNotFoundError:
                continue
        if settings_key is None:
            raise ValueError(
                T('gimi_registry_key_not_found',
                  'Genshin Impact registry key is not found!\n\n'
                  'Please start the game via original launcher to create the key and try again.')
        )

        # Read binary Graphics Settings key
        try:
            (settings_bytes, regtype) = winreg.QueryValueEx(settings_key, 'GENERAL_DATA_h2389025596')
            if regtype != winreg.REG_BINARY:
                raise ValueError(T('gimi_unknown_settings_format', 'Unknown Settings format: Data type {} is not {} of REG_BINARY!').format(regtype, winreg.REG_BINARY))
        except FileNotFoundError:
            raise ValueError(
                T('gimi_graphics_settings_not_found',
                  'Graphics Settings record is not found in GI registry!\n\n'
                  'Please start the game via official launcher to create the record and try again.'))

        # Read bytes till the first null byte as settings ascii string
        null_byte_pos = settings_bytes.find(b'\x00')
        if null_byte_pos != -1:
            settings_bytes = settings_bytes[:null_byte_pos]
        else:
            log.debug(f'Binary record GENERAL_DATA_h2389025596 is not null-terminated!')
        settings_str = settings_bytes.decode('ascii')

        # Load settings string to dict
        settings_dict = json.loads(settings_str)

        # Ensure settings dict has known keys
        if 'graphicsData' not in settings_dict:
            raise ValueError(T('gimi_graphics_data_key_not_found', 'Unknown Graphics Settings format: "graphicsData" key not found!'))
        if 'globalPerfData' not in settings_dict:
            raise ValueError(T('gimi_global_perf_data_key_not_found', 'Unknown Graphics Settings format: "globalPerfData" key not found!'))

        # Set new settings
        settings_updated = False

        graphics_data = json.loads(settings_dict['graphicsData'])
        custom_volatile_grades = graphics_data['customVolatileGrades']

        found = False
        for entry in custom_volatile_grades:
            if entry['key'] == 21:
                found = True
                if entry['value'] == 2:
                    entry['value'] = 1
                    settings_updated = True
        if not found:
            custom_volatile_grades.append({'key': 21, 'value': 1})
            settings_updated = True

        global_perf_data = json.loads(settings_dict['globalPerfData'])
        save_items = global_perf_data['saveItems']

        found = False
        for entry in save_items:
            if entry['entryType'] == 21:
                found = True
                if entry['index'] == 1:
                    entry['index'] = 0
                    entry['itemVersion'] = 'OSRELWin5.0.0'
                    settings_updated = True
        if not found:
            save_items.append({'entryType': 21, 'index': 0, 'itemVersion': 'OSRELWin5.0.0'})
            settings_updated = True

        # Exit early if no settings were changed
        if not settings_updated:
            return

        log.debug(f'Disabling DCR...')

        # Serialize settings dict back to string
        settings_dict['graphicsData'] = json.dumps(graphics_data, separators=(',', ':'))
        settings_dict['globalPerfData'] = json.dumps(global_perf_data, separators=(',', ':'))
        settings_str = json.dumps(settings_dict, separators=(',', ':'))

        # Encode settings string as ascii bytes and terminate it with null
        settings_bytes = bytes(settings_str.encode('ascii')) + b'\x00'

        # Write encoded settings back to registry
        winreg.SetValueEx(settings_key, 'GENERAL_DATA_h2389025596', None, regtype, settings_bytes)

    def enable_hdr(self):
        log.debug(f'Enabling HDR...')

        # Open GI registry settings key
        settings_key = None
        gi_reg_keys = [
            (winreg.HKEY_CURRENT_USER, 'SOFTWARE\\miHoYo\\Genshin Impact'),
            (winreg.HKEY_CURRENT_USER, 'SOFTWARE\\miHoYo\\原神'),
        ]
        for (key, subkey) in gi_reg_keys:
            try:
                settings_key = winreg.OpenKey(key, subkey, 0, winreg.KEY_ALL_ACCESS)
                break
            except FileNotFoundError:
                continue
        if settings_key is None:
            raise ValueError(
                T('gimi_registry_key_not_found',
                  'Genshin Impact registry key is not found!\n\n'
                  'Please start the game via original launcher to create the key and try again.')
            )

        # Write required key to registry, we need to do it each time, as it's getting removed after the game start
        try:
            winreg.SetValueEx(settings_key, 'WINDOWS_HDR_ON_h3132281285', None, winreg.REG_DWORD, 1)
        except FileNotFoundError:
            raise ValueError(
                T('gimi_hdr_record_not_found',
                  'HDR record is not found in GI registry!\n\n'
                  'Please start the game via official launcher to create the record and try again.'))

    def configure_fps_unlocker(self):
        Events.Fire(Events.Application.StatusUpdate(status=L('gimi_configuring_fps_unlocker', 'Configuring FPS Unlocker...')))

        result, pid = wait_for_process_exit('unlockfps_nc.exe', timeout=10, kill_timeout=5)
        if result == WaitResult.Timeout:
            Events.Fire(Events.Application.ShowError(
                modal=True,
                message=T('gimi_fps_unlocker_terminate_failed',
                         'Failed to terminate FPS Unlocker!\n\n'
                         'Please close it manually and press [OK] to continue.'),
            ))

        fps_config_template_path = Paths.App.Resources / 'Packages' / 'GI-FPS-Unlocker' / 'fps_config_template.json'
        fps_config_path = fps_config_template_path.parent / 'fps_config.json'

        try:
            with open(fps_config_path, 'r', encoding='utf-8') as f:
                fps_config = json.load(f)
        except Exception:
            shutil.copy2(fps_config_template_path, fps_config_path)
            with open(fps_config_path, 'r', encoding='utf-8') as f:
                fps_config = json.load(f)

        game_path = self.validate_game_path(Config.Active.Importer.game_folder)
        game_exe_path = self.validate_game_exe_path(game_path)

        modified = False

        if fps_config.get('GamePath', None) != str(game_exe_path):
            fps_config['GamePath'] = str(game_exe_path)
            modified = True

        process_priorities = {
            ProcessPriority.IDLE_PRIORITY_CLASS: 5,
            ProcessPriority.BELOW_NORMAL_PRIORITY_CLASS: 4,
            ProcessPriority.NORMAL_PRIORITY_CLASS: 3,
            ProcessPriority.ABOVE_NORMAL_PRIORITY_CLASS: 2,
            ProcessPriority.HIGH_PRIORITY_CLASS: 1,
            ProcessPriority.REALTIME_PRIORITY_CLASS: 0,
        }
        try:
            process_priority = ProcessPriority(Config.Active.Importer.process_priority)
        except Exception as e:
            process_priority = ProcessPriority.ABOVE_NORMAL_PRIORITY_CLASS
            Config.Active.Importer.process_priority = process_priority.value
        process_priority = process_priorities[process_priority]

        if fps_config.get('Priority', None) != process_priority:
            fps_config['Priority'] = process_priority
            modified = True

        if fps_config.get('AdditionalCommandLine', None) != Config.Active.Importer.launch_options:
            fps_config['AdditionalCommandLine'] = Config.Active.Importer.launch_options
            modified = True

        window_modes = {
            WindowMode.Windowed: {
                'PopupWindow': False,
                'Fullscreen': False,
                'IsExclusiveFullscreen': False,
            },
            WindowMode.Borderless: {
                'PopupWindow': True,
                'Fullscreen': False,
                'IsExclusiveFullscreen': False,
            },
            WindowMode.Fullscreen: {
                'PopupWindow': False,
                'Fullscreen': True,
                'IsExclusiveFullscreen': False,
            },
            WindowMode.ExclusiveFullscreen: {
                'PopupWindow': False,
                'Fullscreen': True,
                'IsExclusiveFullscreen': True,
            },
        }
        try:
            window_mode = WindowMode(Config.Active.Importer.window_mode)
        except Exception as e:
            window_mode = WindowMode.Borderless
            Config.Active.Importer.window_mode = window_mode.value

        for setting, value in window_modes[window_mode].items():
            if fps_config.get(setting, None) != value:
                fps_config[setting] = value
                modified = True

        if not modified:
            return

        with open(fps_config_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(fps_config, indent=4))


class Version:
    def __init__(self, gimi_ini_path):
        self.gimi_ini_path = gimi_ini_path
        self.version = None
        self.parse_version()

    def parse_version(self):
        with open(self.gimi_ini_path, 'r', encoding='utf-8') as f:

            version_pattern = re.compile(r'^global \$version = (\d+)\.*(\d)(\d*)')

            for line in f.readlines():

                result = version_pattern.findall(line)

                if len(result) != 1:
                    continue

                result = list(result[0])

                if len(result) == 2:
                    result.append(0)

                if len(result) != 3:
                    raise ValueError(T('gimi_malformed_version', 'Malformed GIMI version!'))

                self.version = result

                return

        raise ValueError(T('gimi_version_not_found', 'Failed to locate GIMI version!'))

    def __str__(self) -> str:
        return f'{self.version[0]}.{self.version[1]}.{self.version[2]}'

    def as_float(self):
        return float(f'{self.version[0]}.{self.version[1]}{self.version[2]}')

    def as_ints(self):
        return [map(int, self.version)]