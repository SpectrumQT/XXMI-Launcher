import re
import os
import logging
import ctypes
import json

from dataclasses import field
from typing import Dict, Union


from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import PackageMetadata

from core.utils.ini_handler import IniHandler, IniHandlerSettings
from core.packages.model_importers.model_importer import ModelImporterPackage, ModelImporterConfig
from core.packages.migoto_package import MigotoManagerConfig
from core.utils.sleepy import Sleepy, JsonSerializer

log = logging.getLogger(__name__)


@dataclass
class ZZMIConfig(ModelImporterConfig):
    importer_folder: str = 'ZZMI/'
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
    configure_game: bool = True


@dataclass
class ZZMIPackageConfig:
    Importer: ZZMIConfig = field(
        default_factory=lambda: ZZMIConfig()
    )
    Migoto: MigotoManagerConfig = field(
        default_factory=lambda: MigotoManagerConfig()
    )


class ZZMIPackage(ModelImporterPackage):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='ZZMI',
            auto_load=False,
            github_repo_owner='leotorrez',
            github_repo_name='ZZMI-Package',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='ZZMI-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEb11GjbKQS6SmRe8TcIc5VMu5Ob3moo5v2YeD+s53xEe4bVPGcToUNLu3Jgqo0OwWZ4RsNy1nR0HId6pR09HedyEMifxebsyPT3T5PH82QozEXHQlTDySklWUfGItoOdf',
            exit_after_update=False,
            installation_path='ZZMI/',
            requirements=['XXMI'],
        ))

    def get_installed_version(self):
        try:
            return str(Version(Config.Importers.ZZMI.Importer.importer_path / 'Core' / 'ZZMI' / 'main.ini'))
        except Exception as e:
            return ''

    def autodetect_game_folder(self) -> Path:
        data_path = self.get_game_data_path()
        return Path(str(data_path.parent).replace('\\', '/'))

    def validate_game_exe_path(self, game_path: Path) -> Path:
        game_exe_path = game_path / 'ZenlessZoneZero.exe'
        if not game_exe_path.is_file():
            raise ValueError(f'Game executable {game_exe_path} does not exist!')
        return game_exe_path

    def initialize_game_launch(self, game_path: Path):
        self.update_zzmi_ini()
        if Config.Importers.ZZMI.Importer.configure_game:
            try:
                self.configure_game_settings(game_path)
            except FileNotFoundError as e:
                raise ValueError(f'Failed to configure in-game settings for ZZMI!\n'
                                 f'Please start the game with official launcher once.\n\n'
                                 f'{e}') from e
            except Exception as e:
                raise ValueError(f'Failed to configure in-game settings for ZZMI!\n'
                      f"Please disable `Configure Game` in launcher's General Settings and check in-game settings:\n"
                      f'* Graphics > `Character Quality` must be `High`.\n'
                      f'* Graphics > `High-Precision Character Animation` must be `Disabled`.\n\n'
                      f'{e}') from e

    def get_game_data_path(self):
        player_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'miHoYo' / 'ZenlessZoneZero' / 'Player.log'

        # WwiseUnity: Setting Plugin DLL path to: C:/Games/ZenlessZoneZero Game/ZenlessZoneZero_Data\Plugins\x86_64
        # [Subsystems] Discovering subsystems at path C:/Games/ZenlessZoneZero Game/ZenlessZoneZero_Data/UnitySubsystems
        subsystems_pattern = re.compile(r'([a-zA-Z]:[^:]*)(?:Plugins|UnitySubsystems)')
        data_path = self.find_in_file(subsystems_pattern, player_log_path)
        if data_path is not None:
            return data_path

        output_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'miHoYo' / 'ZenlessZoneZero' / 'output_log.txt'

        # [0704/170821.845:INFO:API.cpp(331)] zfb_init: Using --apm_config={"astrolabePath":"Astrolabe.dll","reportPath":"C:\\Games\\ZenlessZoneZero Game\\ZenlessZoneZero_Data\\SDKCaches\\webview","logLevel":2"}
        report_path_pattern = re.compile(r'([a-zA-Z]:[^:]*)SDKCaches"')
        data_path = self.find_in_file(report_path_pattern, output_log_path)
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

    def update_zzmi_ini(self):
        Events.Fire(Events.Application.StatusUpdate(status='Updating ZZMI main.ini...'))

        zzmi_ini_path = Config.Importers.ZZMI.Importer.importer_path / 'Core' / 'ZZMI' / 'main.ini'
        if not zzmi_ini_path.exists():
            raise ValueError('Failed to locate Core/ZZMI/main.ini!')

        Events.Fire(Events.Application.VerifyFileAccess(path=zzmi_ini_path, write=True))
        with open(zzmi_ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(option_value_spacing=True, ignore_comments=False), f)

        screen_width, screen_height = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
        ini.set_option('Constants', 'global $window_width', screen_width)
        ini.set_option('Constants', 'global $window_height', screen_height)

        if ini.is_modified():
            with open(zzmi_ini_path, 'w', encoding='utf-8') as f:
                f.write(ini.to_string())

    def configure_game_settings(self, game_path: Path):
        log.debug(f'Configuring in-game settings for ZZMI...')

        config_path = game_path / 'ZenlessZoneZero_Data' / 'Persistent' / 'LocalStorage' / 'GENERAL_DATA.bin'

        settings_manager = SettingsManager(config_path)

        # Load settings from GENERAL_DATA.bin or initialize new settings container
        settings_manager.load_settings()

        # Set "Image Quality" to "Custom"
        settings_manager.set_system_setting('3', 3)
        # Set "High-Precision Character Animation" to "Disabled"
        settings_manager.set_system_setting('13162', 0)
        # Set "Character Quality" to "High"
        settings_manager.set_system_setting('99', 1)

        # Write settings to GENERAL_DATA.bin
        settings_manager.save_settings()


class SettingsManager:
    def __init__(self, config_path: Path):
        self.path = config_path
        self.json = JsonSerializer()
        self.sleepy = Sleepy()
        self.magic = bytes([85, 110, 209, 150, 116, 209, 131, 206, 149, 110, 103, 105, 110, 208, 181, 46, 71, 208, 176, 109, 101, 206, 159, 98, 106, 101, 209, 129, 116])
        self.settings = {}
        self.modified = False

    def load_settings(self):
        if self.path.is_file():
            content = self.sleepy.read_file(self.path, self.magic)
            self.settings = json.loads(content)
        else:
            self.settings = {
                '$Type': 'MoleMole.GeneralLocalDataItem',
                'userLocalDataVersionId': '0.0.1',
            }

    def save_settings(self):
        if not self.modified:
            return
        content = self.json.dumps(self.settings)
        self.sleepy.write_file(self.path, self.magic, content)

    def set_system_setting(self, setting_id: str, new_value: int):
        system_settings = self.settings.get('SystemSettingDataMap', {})
        setting = system_settings.get(setting_id, None)
        if setting is None:
            system_settings[setting_id] = {
                '$Type': 'MoleMole.SystemSettingLocalData',
                'Version': 0,
                'Data': new_value
            }
            self.modified = True
            log.debug(f'Added new setting {setting_id}: {new_value}')
        else:
            old_value = setting.get('Data', None)
            if old_value is None:
                raise ValueError(f'Unknown system settings entry format: {setting}!')
            if old_value == new_value:
                log.debug(f'Setting {setting_id} is already set to {old_value}')
                return
            setting['Data'] = new_value
            self.modified = True
            log.debug(f'Updated setting {setting_id}: {old_value} -> {new_value}')
        self.settings['SystemSettingDataMap'] = system_settings


class Version:
    def __init__(self, zzmi_ini_path):
        self.zzmi_ini_path = zzmi_ini_path
        self.version = None
        self.parse_version()

    def parse_version(self):
        with open(self.zzmi_ini_path, 'r', encoding='utf-8') as f:

            version_pattern = re.compile(r'^global \$version = (\d+)\.*(\d)(\d*)')

            for line in f.readlines():

                result = version_pattern.findall(line)

                if len(result) != 1:
                    continue

                result = list(result[0])

                if len(result) == 2:
                    result.append(0)

                if len(result) != 3:
                    raise ValueError(f'Malformed ZZMI version!')

                self.version = result

                return

        raise ValueError(f'Failed to locate ZZMI version!')

    def __str__(self) -> str:
        return f'{self.version[0]}.{self.version[1]}.{self.version[2]}'

    def as_float(self):
        return float(f'{self.version[0]}.{self.version[1]}{self.version[2]}')

    def as_ints(self):
        return [map(int, self.version)]