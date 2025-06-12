import re
import os
import logging
import winreg
import json

from dataclasses import dataclass, field
from typing import Dict, Union, List

from core.locale_manager import T, L
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import PackageMetadata

from core.utils.ini_handler import IniHandler, IniHandlerSettings
from core.packages.model_importers.model_importer import ModelImporterPackage, ModelImporterConfig
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
            raise ValueError(T('srmi_game_exe_not_found', 'Game executable {} not found!').format(game_exe_path.name))
        return game_exe_path

    def initialize_game_launch(self, game_path: Path):
        if Config.Active.Importer.custom_launch_inject_mode != 'Bypass':
            self.update_srmi_ini()
        if Config.Importers.SRMI.Importer.unlock_fps:
            try:
                self.unlock_fps()
            except Exception as e:
                raise ValueError(T('srmi_fps_unlock_failed', 'Failed to force 120 FPS: {}').format(str(e)))

    def update_srmi_ini(self):
        Events.Fire(Events.Application.StatusUpdate(status=L('srmi_updating_ini', 'Updating SRMI main.ini...')))

        srmi_ini_path = Config.Importers.SRMI.Importer.importer_path / 'Core' / 'SRMI' / 'main.ini'
        if not srmi_ini_path.exists():
            raise ValueError(T('srmi_ini_not_found', 'Failed to locate Core/SRMI/main.ini!'))

        Events.Fire(Events.Application.VerifyFileAccess(path=srmi_ini_path, write=True))
        # with open(srmi_ini_path, 'r', encoding='utf-8') as f:Add commentMore actions
        #     ini = IniHandler(IniHandlerSettings(option_value_spacing=True, ignore_comments=False), f)
        #
        # if ini.is_modified():Add commentMore actions
        #     with open(srmi_ini_path, 'w', encoding='utf-8') as f:
        #         f.write(ini.to_string())

    def unlock_fps(self):
        # Open HSR registry key
        try:
            settings_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\\Cognosphere\\Star Rail', 0, winreg.KEY_ALL_ACCESS)
        except FileNotFoundError:
            raise ValueError(
                T('srmi_registry_key_not_found',
                  'Star Rail registry key is not found!\n\n'
                  'Please start the game without 120 FPS tweak, change FPS to any value to create the record and try again.\n\n'
                  'Note: Tweak is supported only for the Global HSR client and will not work for CN.')
            )
        # Read binary Graphics Settings key
        try:
            (settings_bytes, regtype) = winreg.QueryValueEx(settings_key, 'GraphicsSettings_Model_h2986158309')
        except FileNotFoundError as e:
            raise ValueError(
                T('srmi_graphics_settings_not_found',
                  'Graphics Settings record is not found in HSR registry!\n\n'
                  'Please start the game without 120 FPS tweak, change FPS to any value to create the record and try again.')
            )
        if regtype != winreg.REG_BINARY:
            raise ValueError(T('srmi_unknown_graphics_format', 'Unknown Graphics Settings format: Data type {} is not {} of REG_BINARY!').format(regtype, winreg.REG_BINARY))
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
            raise ValueError(T('srmi_fps_key_not_found', 'Unknown Graphics Settings format: "FPS" key no found!'))
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


class Version:
    def __init__(self, srmi_ini_path):
        self.srmi_ini_path = srmi_ini_path
        self.version = None
        self.parse_version()

    def parse_version(self):
        with open(self.srmi_ini_path, 'r', encoding='utf-8') as f:

            version_pattern = re.compile(r'^global \$version = (\d+)\.*(\d)(\d*)')

            for line in f.readlines():

                result = version_pattern.findall(line)

                if len(result) != 1:
                    continue

                result = list(result[0])

                if len(result) == 2:
                    result.append(0)

                if len(result) != 3:
                    raise ValueError(T('srmi_malformed_version', 'Malformed SRMI version!'))

                self.version = result

                return

        raise ValueError(T('srmi_version_not_found', 'Failed to locate SRMI version!'))

    def __str__(self) -> str:
        return f'{self.version[0]}.{self.version[1]}.{self.version[2]}'

    def as_float(self):
        return float(f'{self.version[0]}.{self.version[1]}{self.version[2]}')

    def as_ints(self):
        return [map(int, self.version)]