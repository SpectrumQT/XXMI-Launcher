import re
import os
import logging
import json

from dataclasses import dataclass, field
from typing import Dict, Union, List

from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.locale_manager import L
from core.package_manager import PackageMetadata

from core.utils.ini_handler import IniHandler, IniHandlerSettings
from core.packages.model_importers.model_importer import ModelImporterPackage, ModelImporterConfig, Version
from core.packages.migoto_package import MigotoManagerConfig
from core.utils.sleepy import Sleepy, JsonSerializer

log = logging.getLogger(__name__)


@dataclass
class ZZMIConfig(ModelImporterConfig):
    game_exe_names: List[str] = field(default_factory=lambda: ['ZenlessZoneZero.exe'])
    game_folder_names: List[str] = field(default_factory=lambda: ['ZenlessZoneZero Game'])
    game_folder_children: List[str] = field(default_factory=lambda: ['ZenlessZoneZero_Data'])
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
        self.autodetect_patterns = {
            'common': re.compile(r'([a-zA-Z]:[^:\"\']*Zenless[^:\"\']*)'),
            # "installPath":"D:\\Games\\ZenlessZoneZero Game"
            # "persistentInstallPath":"D:\\Games\\ZenlessZoneZero Game"
            'hoyoplay': re.compile(r'\"(?:installPath|persistentInstallPath)\":\"([a-zA-Z]:[^:^\"]*)\"'),
            # WwiseUnity: Setting Plugin DLL path to: C:/Games/ZenlessZoneZero Game/ZenlessZoneZero_Data\Plugins\x86_64
            # [Subsystems] Discovering subsystems at path C:/Games/ZenlessZoneZero Game/ZenlessZoneZero_Data/UnitySubsystems
            'player_log': re.compile(r'([a-zA-Z]:[^:\"\']*)(?:Plugins|UnitySubsystems)'),
            # [0704/170821.845:INFO:API.cpp(331)] zfb_init: Using --apm_config={"astrolabePath":"Astrolabe.dll","reportPath":"C:\\Games\\ZenlessZoneZero Game\\ZenlessZoneZero_Data\\SDKCaches\\webview","logLevel":2"}
            'output_log': re.compile(r'([a-zA-Z]:[^:\"\']*)SDKCaches"'),
        }
        self.autodetect_files = {
            '{HOYOPLAY}': ['common', 'hoyoplay'],
            '{APPDATA}/LocalLow/miHoYo/ZenlessZoneZero/Player.log': ['common', 'player_log'],
            '{APPDATA}/LocalLow/miHoYo/ZenlessZoneZero/Player-prev.log': ['common', 'player_log'],
            '{APPDATA}/LocalLow/miHoYo/ZenlessZoneZero/output_log.txt': ['common', 'output_log'],
        }

    def get_installed_version(self):
        try:
            return str(Version(Config.Importers.ZZMI.Importer.importer_path / 'Core' / 'ZZMI' / 'main.ini'))
        except Exception as e:
            return ''

    def validate_game_exe_path(self, game_path: Path) -> Path:
        game_exe_path = game_path / 'ZenlessZoneZero.exe'
        if not game_exe_path.is_file():
            raise ValueError(L('error_game_exe_not_found', 'Game executable {exe_name} not found!').format(exe_name=game_exe_path.name))
        return game_exe_path

    def initialize_game_launch(self, game_path: Path):
        # Prevent further configuration if ZZMI isn't going to be used
        if not Config.Active.Importer.is_xxmi_dll_used():
            return
        # Configure GENERAL_DATA.bin
        if Config.Importers.ZZMI.Importer.configure_game:
            try:
                self.configure_game_settings(game_path)
            except Exception as e:
                raise ValueError(L('error_zzmi_game_config_failed', """
                    Failed to configure in-game settings for ZZMI!
                    Please disable `Configure Game Settings` in launcher's General Settings and check in-game settings:
                    * Graphics > `Character Quality` must be `High`.
                    * Graphics > `High-Precision Character Animation` must be `Disabled`.
                    
                    {error_text}
                """).format(error_text=e)) from e

    def configure_game_settings(self, game_path: Path):
        Events.Fire(Events.Application.StatusUpdate(status=L('status_configuring_settings', 'Configuring in-game settings...')))

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
            Events.Fire(Events.PathManager.VerifyFileAccess(path=self.path, write=True))
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
                raise ValueError(L('error_zzmi_unknown_settings_format', 'Unknown system settings entry format: {setting}!').format(setting=setting))
            if old_value == new_value:
                log.debug(f'Setting {setting_id} is already set to {old_value}')
                return
            setting['Data'] = new_value
            self.modified = True
            log.debug(f'Updated setting {setting_id}: {old_value} -> {new_value}')
        self.settings['SystemSettingDataMap'] = system_settings
