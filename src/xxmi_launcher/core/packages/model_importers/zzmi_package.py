import re
import os
import logging
import ctypes
import json

from dataclasses import field
from typing import Dict, Union, List


from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config
import core.i18n_manager as I18n

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

    def autodetect_game_folders(self) -> List[Path]:
        paths = self.reg_search_game_folders(['ZenlessZoneZero.exe'])

        common_pattern = re.compile(r'([a-zA-Z]:[^:\"\']*Zenless[^:\"\']*)')
        known_children = ['ZenlessZoneZero_Data']

        # "installPath":"D:\\Games\\ZenlessZoneZero Game"
        # "persistentInstallPath":"D:\\Games\\ZenlessZoneZero Game"
        hoyoplay_pattern = re.compile(r'\"(?:installPath|persistentInstallPath)\":\"([a-zA-Z]:[^:^\"]*)\"')

        paths += self.get_paths_from_hoyoplay([common_pattern, hoyoplay_pattern], known_children)

        # WwiseUnity: Setting Plugin DLL path to: C:/Games/ZenlessZoneZero Game/ZenlessZoneZero_Data\Plugins\x86_64
        # [Subsystems] Discovering subsystems at path C:/Games/ZenlessZoneZero Game/ZenlessZoneZero_Data/UnitySubsystems
        player_log_pattern = re.compile(r'([a-zA-Z]:[^:\"\']*)(?:Plugins|UnitySubsystems)')

        player_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'miHoYo' / 'ZenlessZoneZero' / 'Player.log'
        paths += self.find_paths_in_file(player_log_path, [common_pattern, player_log_pattern], known_children)

        player_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'miHoYo' / 'ZenlessZoneZero' / 'Player-prev.log'
        paths += self.find_paths_in_file(player_log_path, [common_pattern, player_log_pattern], known_children)

        # [0704/170821.845:INFO:API.cpp(331)] zfb_init: Using --apm_config={"astrolabePath":"Astrolabe.dll","reportPath":"C:\\Games\\ZenlessZoneZero Game\\ZenlessZoneZero_Data\\SDKCaches\\webview","logLevel":2"}
        output_log_pattern = re.compile(r'([a-zA-Z]:[^:\"\']*)SDKCaches"')

        output_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'miHoYo' / 'ZenlessZoneZero' / 'output_log.txt'
        paths += self.find_paths_in_file(output_log_path, [common_pattern, output_log_pattern], known_children)

        return paths

    def validate_game_exe_path(self, game_path: Path) -> Path:
        game_exe_path = game_path / 'ZenlessZoneZero.exe'
        if not game_exe_path.is_file():
            raise ValueError(I18n._('errors.packages.model_importers.zzmi.executable_not_found').format(process_name=game_exe_path.name))
        return game_exe_path

    def initialize_game_launch(self, game_path: Path):
        if Config.Active.Importer.custom_launch_inject_mode != 'Bypass':
            self.update_zzmi_ini()
            try:
                self.configure_settings(game_path)
            except Exception as e:
                raise ValueError(I18n._('errors.packages.model_importers.zzmi.configure_settings_failed').format(error=str(e)))

    def update_zzmi_ini(self):
        Events.Fire(Events.Application.StatusUpdate(status=I18n._('status.updating_gimi_ini')))

        zzmi_ini_path = Config.Importers.ZZMI.Importer.importer_path / 'Core' / 'ZZMI' / 'main.ini'
        if not zzmi_ini_path.exists():
            raise ValueError(I18n._('errors.packages.model_importers.zzmi.ini_not_found'))

        Events.Fire(Events.Application.VerifyFileAccess(path=zzmi_ini_path, write=True))
        with open(zzmi_ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(option_value_spacing=True, ignore_comments=False), f)

        screen_width, screen_height = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
        ini.set_option('Constants', 'global $window_width', screen_width)
        ini.set_option('Constants', 'global $window_height', screen_height)

        if ini.is_modified():
            with open(zzmi_ini_path, 'w', encoding='utf-8') as f:
                f.write(ini.to_string())

    def configure_settings(self, game_path: Path):
        if not Config.Importers.ZZMI.Importer.configure_game:
            return

        Events.Fire(Events.Application.StatusUpdate(status=I18n._('status.configuring_in_game_settings')))

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
            Events.Fire(Events.Application.VerifyFileAccess(path=self.path, write=True))
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
                raise ValueError(I18n._('errors.packages.model_importers.zzmi.unknown_settings_format').format(setting=setting))
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
                    raise ValueError(I18n._('errors.packages.model_importers.zzmi.malformed_version'))

                self.version = result

                return

        raise ValueError(I18n._('errors.packages.model_importers.zzmi.version_not_found'))

    def __str__(self) -> str:
        return f'{self.version[0]}.{self.version[1]}.{self.version[2]}'

    def as_float(self):
        return float(f'{self.version[0]}.{self.version[1]}{self.version[2]}')

    def as_ints(self):
        return [map(int, self.version)]