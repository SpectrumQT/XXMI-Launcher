import re
import os
import json
import shutil
import logging

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

log = logging.getLogger(__name__)


@dataclass
class ZZMIConfig(ModelImporterConfig):
    importer_folder: str = 'ZZMI/'
    launcher_theme: str = 'Default'
    launch_options: str = ''
    d3dx_ini: Dict[
        str, Dict[str, Dict[str, Union[str, int, float, Dict[str, Union[str, int, float]]]]]
    ] = field(default_factory=lambda: {
        'core': {
            'Loader': {
                'target': 'ZenlessZoneZero.exe',
                'loader': 'XXMI Launcher.exe',
            },
            'Rendering': {
                'texture_hash': 0,
                'track_texture_updates': 0,
            },
        },
        'debug_logging': {
            'Logging': {
                'calls': {'on': 1, 'off': 0},
                'debug': {'on': 1, 'off': 0},
                'unbuffered': {'on': 1, 'off': 0},
                'force_cpu_affinity': {'on': 1, 'off': 0},
                'debug_locks': {'on': 1, 'off': 0},
                'crash': {'on': 1, 'off': 0},
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
            github_repo_name='ZZMI-TEST',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='ZZMI-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEb11GjbKQS6SmRe8TcIc5VMu5Ob3moo5v2YeD+s53xEe4bVPGcToUNLu3Jgqo0OwWZ4RsNy1nR0HId6pR09HedyEMifxebsyPT3T5PH82QozEXHQlTDySklWUfGItoOdf',
            exit_after_update=False,
            installation_path='ZZMI/',
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
        pass

    def get_game_data_path(self):
        player_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'miHoYo' / 'ZenlessZoneZero' / 'Player.log'

        # [Subsystems] Discovering subsystems at path C:/Games/ZenlessZoneZero Game/ZenlessZoneZero_Data/UnitySubsystems
        subsystems_pattern = re.compile(r'Discovering subsystems at path (.*)UnitySubsystems')
        data_path = self.find_in_file(subsystems_pattern, player_log_path)
        if data_path is not None:
            return data_path

        # WwiseUnity: Setting Plugin DLL path to: C:/Games/ZenlessZoneZero Game/ZenlessZoneZero_Data\Plugins\x86_64
        plugin_pattern = re.compile(r'Setting Plugin DLL path to: (.*)Plugins')
        data_path = self.find_in_file(plugin_pattern, player_log_path)
        if data_path is not None:
            return data_path

        output_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'miHoYo' / 'ZenlessZoneZero' / 'output_log.txt'

        # [0704/170821.845:INFO:API.cpp(331)] zfb_init: Using --apm_config={"astrolabePath":"Astrolabe.dll","reportPath":"C:\\Games\\ZenlessZoneZero Game\\ZenlessZoneZero_Data\\SDKCaches\\webview","logLevel":2"}
        report_path_pattern = re.compile(r'"reportPath":"(.*)SDKCaches"')
        data_path = self.find_in_file(report_path_pattern, output_log_path)
        if data_path is not None:
            return data_path

        return None

    def find_in_file(self, pattern, file_path: Path):
        if not file_path.exists():
            raise ValueError(f'File {file_path} does not exist!')
        with open(file_path, 'r') as f:
            for line in f.readlines():
                result = pattern.findall(line)
                if len(result) == 1:
                    data_path = Path(result[0])
                    if data_path.exists():
                        return data_path


class Version:
    def __init__(self, zzmi_ini_path):
        self.zzmi_ini_path = zzmi_ini_path
        self.version = None
        self.parse_version()

    def parse_version(self):
        with open(self.zzmi_ini_path, "r") as f:

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