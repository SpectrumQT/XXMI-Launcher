import re
import os
import logging
import ctypes
import winreg
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
            raise ValueError(I18n._('errors.packages.model_importers.srmi.executable_not_found').format(process_name=game_exe_path.name))
        return game_exe_path

    def initialize_game_launch(self, game_path: Path):
        if Config.Active.Importer.custom_launch_inject_mode != 'Bypass':
            self.update_srmi_ini()
            if Config.Importers.SRMI.Importer.unlock_fps:
                try:
                    self.configure_fps_unlock()
                except Exception as e:
                    raise ValueError(I18n._('errors.packages.model_importers.srmi.force_fps_failed').format(error=str(e)))

    def update_srmi_ini(self):
        Events.Fire(Events.Application.StatusUpdate(status=I18n._('status.updating_gimi_ini')))

        srmi_ini_path = Config.Importers.SRMI.Importer.importer_path / 'Core' / 'SRMI' / 'main.ini'
        if not srmi_ini_path.exists():
            raise ValueError(I18n._('errors.packages.model_importers.srmi.ini_not_found'))

        Events.Fire(Events.Application.VerifyFileAccess(path=srmi_ini_path, write=True))
        with open(srmi_ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(option_value_spacing=True, ignore_comments=False), f)

        screen_width, screen_height = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
        ini.set_option('Constants', 'global $window_width', screen_width)
        ini.set_option('Constants', 'global $window_height', screen_height)

        if ini.is_modified():
            with open(srmi_ini_path, 'w', encoding='utf-8') as f:
                f.write(ini.to_string())

    def configure_fps_unlock(self):
        Events.Fire(Events.Application.StatusUpdate(status=I18n._('status.configuring_in_game_settings')))

        # Open SR registry settings key
        settings_key = None
        sr_reg_keys = [
            (winreg.HKEY_CURRENT_USER, 'SOFTWARE\\miHoYo\\Star Rail'),
            (winreg.HKEY_CURRENT_USER, 'SOFTWARE\\miHoYo\\崩坏：星穹铁道'),
        ]
        for (key, subkey) in sr_reg_keys:
            try:
                settings_key = winreg.OpenKey(key, subkey, 0, winreg.KEY_ALL_ACCESS)
                break
            except FileNotFoundError:
                continue
        if settings_key is None:
            raise ValueError(I18n._('errors.packages.model_importers.srmi.registry_key_not_found'))

        # Read current settings
        try:
            (settings_data, regtype) = winreg.QueryValueEx(settings_key, 'GraphicsSettings_Model_h2986158309')
        except FileNotFoundError:
            raise ValueError(I18n._('errors.packages.model_importers.srmi.registry_key_not_found'))

        if regtype != winreg.REG_BINARY:
            raise ValueError(I18n._('errors.packages.model_importers.srmi.unknown_graphics_settings_format').format(regtype=regtype, reg_binary=winreg.REG_BINARY))

        # Parse settings
        settings_str = settings_data.decode('utf-8', 'ignore').rstrip('\0')
        settings_dict = json.loads(settings_str)

        # Check if FPS key exists
        if 'FPS' not in settings_dict:
            raise ValueError(I18n._('errors.packages.model_importers.srmi.fps_key_not_found'))

        # Set FPS to 120
        settings_dict['FPS'] = 120

        # Save settings
        settings_str = json.dumps(settings_dict)
        settings_data = settings_str.encode('utf-8') + b'\0'
        winreg.SetValueEx(settings_key, 'GraphicsSettings_Model_h2986158309', 0, regtype, settings_data)


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
                    raise ValueError(I18n._('errors.packages.model_importers.srmi.malformed_version'))

                self.version = result

                return

        raise ValueError(I18n._('errors.packages.model_importers.srmi.version_not_found'))

    def __str__(self) -> str:
        return f'{self.version[0]}.{self.version[1]}.{self.version[2]}'

    def as_float(self):
        return float(f'{self.version[0]}.{self.version[1]}{self.version[2]}')

    def as_ints(self):
        return [map(int, self.version)]