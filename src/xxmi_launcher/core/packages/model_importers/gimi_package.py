import re
import os
import logging
import ctypes
import shutil
import winreg
import json

from dataclasses import field
from enum import Enum
from typing import Dict, Union, Tuple, Optional, List

from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import PackageMetadata

from core.utils.ini_handler import IniHandler, IniHandlerSettings
from core.utils.process_tracker import wait_for_process_exit, WaitResult, ProcessPriority
from core.packages.model_importers.model_importer import ModelImporterPackage, ModelImporterConfig
from core.packages.migoto_package import MigotoManagerConfig

log = logging.getLogger(__name__)


@dataclass
class GIMIConfig(ModelImporterConfig):
    importer_folder: str = 'GIMI/'
    launch_options: str = ''
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
            github_repo_owner='SpectrumQT',
            github_repo_name='GIMI-TEST',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='GIMI-TEST-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=False,
            installation_path='GIMI/',
            requirements=['XXMI', 'GI-FPS-Unlocker'],
        ))

    def get_installed_version(self):
        try:
            return str(Version(Config.Importers.GIMI.Importer.importer_path / 'Core' / 'GIMI' / 'main.ini'))
        except Exception as e:
            return ''

    def autodetect_game_folder(self) -> Path:
        data_path = self.get_game_data_path()
        return Path(str(data_path.parent).replace('\\', '/'))

    def validate_game_exe_path(self, game_path: Path) -> Path:
        game_exe_path = game_path / 'GenshinImpact.exe'
        if not game_exe_path.is_file():
            game_exe_cn_path = game_path / 'YuanShen.exe'
            if not game_exe_cn_path.is_file():
                raise ValueError(f'Game executable {game_exe_path} or {game_exe_cn_path} does not exist!')
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
        self.disable_duplicate_libraries(Config.Active.Importer.importer_path / 'Core' / 'GIMI' / 'Libraries')
        self.update_gimi_ini()
        if Config.Importers.GIMI.Importer.unlock_fps:
            self.configure_fps_unlocker()
            self.use_hook = False
        else:
            self.use_hook = True

        if Config.Importers.GIMI.Importer.disable_dcr:
            try:
                self.update_dcr()
            except Exception as e:
                raise ValueError(f'Failed to disable DCR (Dynamic Character Resolution)!\n\n{str(e)}')

    def get_game_data_path(self):
        output_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'miHoYo' / 'Genshin Impact' / 'output_log.txt'

        # dll path: C:/Games/Genshin Impact/DATA/Genshin Impact game/GenshinImpact_Data\Plugins\EOSSDK-Win64-Shipping.dll
        # TelemetryInterface path:C:\Games\Genshin Impact\DATA\Genshin Impact game\GenshinImpact_Data\SDKCaches, level:2, dest:0
        path_pattern = re.compile(r'([a-zA-Z]:[^:]*)(?:Plugins|SDKCaches|StreamingAssets|Persistent)')
        data_path = self.find_in_file(path_pattern, output_log_path)
        if data_path is not None:
            return data_path

        return None

    def find_in_file(self, pattern, file_path: Path):
        if not file_path.exists():
            raise ValueError(f'File {file_path} does not exist!')
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f.readlines():
                result = pattern.findall(line)
                if len(result) == 1:
                    data_path = Path(result[0])
                    if data_path.exists():
                        return data_path

    def update_gimi_ini(self):
        Events.Fire(Events.Application.StatusUpdate(status='Updating GIMI main.ini...'))

        gimi_ini_path = Config.Importers.GIMI.Importer.importer_path / 'Core' / 'GIMI' / 'main.ini'
        if not gimi_ini_path.exists():
            raise ValueError('Failed to locate Core/GIMI/main.ini!')

        Events.Fire(Events.Application.VerifyFileAccess(path=gimi_ini_path, write=True))

        log.debug(f'Reading main.ini...')
        with open(gimi_ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(option_value_spacing=True, ignore_comments=False), f)

        log.debug(f'Reading monitor resolution...')
        screen_width, screen_height = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
        ini.set_option('Constants', 'global $window_width', screen_width)
        ini.set_option('Constants', 'global $window_height', screen_height)

        if ini.is_modified():
            log.debug(f'Writing main.ini...')
            with open(gimi_ini_path, 'w', encoding='utf-8') as f:
                f.write(ini.to_string())

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
            raise ValueError(f'Failed to locate Genshin Impact registry key!')

        # Read binary Graphics Settings key
        try:
            (settings_bytes, regtype) = winreg.QueryValueEx(settings_key, 'GENERAL_DATA_h2389025596')
            if regtype != winreg.REG_BINARY:
                raise ValueError(f'Unknown Settings format: Data type {regtype} is not {winreg.REG_BINARY} of REG_BINARY!')
        except FileNotFoundError:
            raise ValueError('Graphics Settings are not found!\n\nPlease start the game once with official launcher!')

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
            raise ValueError('Unknown Graphics Settings format: "graphicsData" key not found!')
        if 'globalPerfData' not in settings_dict:
            raise ValueError('Unknown Graphics Settings format: "globalPerfData" key not found!')

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

    def configure_fps_unlocker(self):
        Events.Fire(Events.Application.StatusUpdate(status='Configuring FPS Unlocker...'))

        result, pid = wait_for_process_exit('unlockfps_nc.exe', timeout=10, kill_timeout=5)
        if result == WaitResult.Timeout:
            Events.Fire(Events.Application.ShowError(
                modal=True,
                message='Failed to terminate FPS Unlocker!\n\n'
                        'Please close it manually and press [OK] to continue.',
            ))

        fps_config_template_path = Paths.App.Resources / 'Packages' / 'GI-FPS-Unlocker' / 'fps_config_template.json'
        fps_config_path = fps_config_template_path.parent / 'fps_config.json'

        if not fps_config_path.is_file():
            shutil.copy2(fps_config_template_path, fps_config_path)
        with open(fps_config_path, 'r', encoding='utf-8') as f:
            fps_config = json.load(f)

        game_path = self.validate_game_path(Config.Active.Importer.game_folder)
        game_exe_path = self.validate_game_exe_path(game_path)

        modified = False

        if fps_config['GamePath'] != str(game_exe_path):
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

        if fps_config['Priority'] != process_priority:
            fps_config['Priority'] = process_priority
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
            if fps_config[setting] != value:
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
                    raise ValueError(f'Malformed GIMI version!')

                self.version = result

                return

        raise ValueError(f'Failed to locate GIMI version!')

    def __str__(self) -> str:
        return f'{self.version[0]}.{self.version[1]}.{self.version[2]}'

    def as_float(self):
        return float(f'{self.version[0]}.{self.version[1]}{self.version[2]}')

    def as_ints(self):
        return [map(int, self.version)]