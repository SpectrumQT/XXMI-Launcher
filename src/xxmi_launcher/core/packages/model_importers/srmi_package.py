import re
import os
import logging
import winreg
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

log = logging.getLogger(__name__)


@dataclass
class SRMIConfig(ModelImporterConfig):
    importer_folder: str = 'SRMI/'
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


@dataclass
class SRMIPackageConfig:
    Importer: SRMIConfig = field(
        default_factory=lambda: SRMIConfig()
    )
    Migoto: MigotoManagerConfig = field(
        default_factory=lambda: MigotoManagerConfig()
    )


class SRMIPackage(ModelImporterPackage):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='SRMI',
            auto_load=False,
            github_repo_owner='SpectrumQT',
            github_repo_name='SRMI-Package',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='SRMI-TEST-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=False,
            installation_path='SRMI/',
            requirements=['XXMI'],
        ))

    def get_installed_version(self):
        try:
            return str(Version(Config.Importers.SRMI.Importer.importer_path / 'Core' / 'SRMI' / 'main.ini'))
        except Exception as e:
            return ''

    def autodetect_game_folders(self) -> List[Path]:
        paths = self.reg_search_game_folders(['StarRail.exe'])

        common_pattern = re.compile(r'([a-zA-Z]:[^:\"\']*Rail[^:\"\']*)')
        known_children = ['StarRail_Data']

        # "installPath":"D:\\Games\\Star Rail Games"
        # "persistentInstallPath":"D:\\Games\\Star Rail Games"
        hoyoplay_pattern = re.compile(r'\"(?:installPath|persistentInstallPath)\":\"([a-zA-Z]:[^:^\"]*)\"')

        paths += self.get_paths_from_hoyoplay([common_pattern, hoyoplay_pattern], known_children)

        # WwiseUnity: Setting Plugin DLL path to: C:/Games/HonkaiStarRail/DATA/Games/StarRail_Data\Plugins\x86_64
        # [Subsystems] Discovering subsystems at path C:/Games/HonkaiStarRail/DATA/Games/StarRail_Data/UnitySubsystems
        player_log_pattern = re.compile(r'([a-zA-Z]:[^:\"\']*)(?:Plugins|UnitySubsystems)')

        player_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'Cognosphere' / 'Star Rail' / 'Player.log'
        paths += self.find_paths_in_file(player_log_path, [common_pattern, player_log_pattern], known_children)

        player_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'Cognosphere' / 'Star Rail' / 'Player-prev.log'
        paths += self.find_paths_in_file(player_log_path, [common_pattern, player_log_pattern], known_children)

        # [0314/092021.404:ERROR:cache_util.cc(146)] Unable to move cache folder C:\Games\HonkaiStarRail\DATA\Games\StarRail_Data\webCaches\2.20.0.0\GPUCache to C:\Games\HonkaiStarRail\DATA\Games\StarRail_Data\webCaches\2.20.0.0\old_GPUCache_000
        output_log_pattern = re.compile(r'([a-zA-Z]:[^:\"\']*)webCaches"')

        output_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'Cognosphere' / 'Star Rail' / 'output_log.txt'
        paths += self.find_paths_in_file(output_log_path, [common_pattern, output_log_pattern], known_children)

        return paths

    def validate_game_exe_path(self, game_path: Path) -> Path:
        game_exe_path = game_path / 'StarRail.exe'
        if not game_exe_path.is_file():
            raise ValueError(L('error_game_exe_not_found', 'Game executable {exe_name} not found!').format(exe_name=game_exe_path.name))
        return game_exe_path

    def initialize_game_launch(self, game_path: Path):
        # if Config.Active.Importer.custom_launch_inject_mode != 'Bypass':
        #     pass
        if Config.Importers.SRMI.Importer.unlock_fps:
            try:
                self.unlock_fps()
            except Exception as e:
                raise ValueError(L('error_srmi_fps_unlock_failed', 'Failed to force 120 FPS: {error_text}').format(error_text=e))

    def unlock_fps(self):
        # Open HSR registry key
        try:
            settings_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\\Cognosphere\\Star Rail', 0, winreg.KEY_ALL_ACCESS)
        except FileNotFoundError:
            raise ValueError(
                L('error_srmi_registry_key_not_found', """
                    Star Rail registry key is not found!
                    
                    Please start the game without 120 FPS tweak, change FPS to any value to create the record and try again.
                    
                    Note: Tweak is supported only for the Global HSR client and will not work for CN.
                """)
            )
        # Read binary Graphics Settings key
        try:
            (settings_bytes, regtype) = winreg.QueryValueEx(settings_key, 'GraphicsSettings_Model_h2986158309')
        except FileNotFoundError as e:
            raise ValueError(
                L('error_srmi_graphics_settings_not_found', """
                    Graphics Settings record is not found in HSR registry!
                    
                    Please start the game without 120 FPS tweak, change FPS to any value to create the record and try again.
                """)
            )
        if regtype != winreg.REG_BINARY:
            raise ValueError(L('error_srmi_unknown_graphics_format',
                'Unknown Graphics Settings format: Data type {regtype} is not {expected_type} of REG_BINARY!'
            ).format(regtype=regtype, expected_type=winreg.REG_BINARY))
        # Read bytes till the first null byte as settings ascii string
        null_byte_pos = settings_bytes.find(b'\x00')
        if null_byte_pos != -1:
            settings_bytes = settings_bytes[:null_byte_pos]
        else:
            log.debug(f'Binary record GraphicsSettings_Model_h2986158309 is not null-terminated!')
        settings_str = settings_bytes.decode('ascii')
        # Load settings string to dict
        settings_dict = json.loads(settings_str)
        # Ensure settings dict has known keys
        if 'FPS' not in settings_dict:
            raise ValueError(L('error_srmi_fps_key_not_found', 'Unknown Graphics Settings format: "FPS" key no found!'))
        # Exit early if FPS is already set to 120
        if settings_dict['FPS'] == 120:
            return
        # Set new settings
        settings_dict['FPS'] = 120
        # Serialize settings dict back to string
        settings_str = json.dumps(settings_dict, separators=(',', ':'))
        # Encode settings string as ascii bytes and terminate it with null
        settings_bytes = bytes(settings_str.encode('ascii')) + b'\x00'
        # Write encoded settings back to registry
        winreg.SetValueEx(settings_key, 'GraphicsSettings_Model_h2986158309', None, regtype, settings_bytes)
