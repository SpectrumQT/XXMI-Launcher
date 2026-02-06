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

from core.locale_manager import L
from core.package_manager import PackageMetadata

from core.utils.ini_handler import IniHandler, IniHandlerSettings
from core.utils.process_tracker import wait_for_process_exit, WaitResult, ProcessPriority
from core.packages.model_importers.model_importer import ModelImporterPackage, ModelImporterConfig, Version
from core.packages.migoto_package import MigotoManagerConfig

log = logging.getLogger(__name__)


@dataclass
class EFMIConfig(ModelImporterConfig):
    game_exe_names: List[str] = field(default_factory=lambda: ['Endfield.exe'])
    game_folder_names: List[str] = field(default_factory=lambda: ['EndField Game'])
    game_folder_children: List[str] = field(default_factory=lambda: ['Endfield_Data'])
    importer_folder: str = 'EFMI/'
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
    custom_launch_inject_mode: str = 'Inject'


@dataclass
class EFMIPackageConfig:
    Importer: EFMIConfig = field(
        default_factory=lambda: EFMIConfig()
    )
    Migoto: MigotoManagerConfig = field(
        default_factory=lambda: MigotoManagerConfig()
    )


class EFMIPackage(ModelImporterPackage):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='EFMI',
            auto_load=False,
            github_repo_owner='SpectrumQT',
            github_repo_name='EFMI-Package',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='EFMI-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEeigvK7REsX3f/vb+RRuFkZt/6VRbykI2oQcEU3IiI3N9s6jWqKkxAE2cTC9wKXDlkeSzlHjPxgzrTrKdqwkFzROMjw5T2LixFB5BYaT633aU/cCiHDbArIJ46+GrqemG',
            exit_after_update=False,
            installation_path='EFMI/',
            requirements=['XXMI'],
        ))
        self.autodetect_patterns = {
            'common': re.compile(r'([a-zA-Z]:[^:\"\']*EndField[^:\"\']*)'),
        }
        self.autodetect_files = {
            '{APPDATA}/LocalLow/Gryphline/Endfield/Player.log': ['common'],
        }
        self.autodetect_known_paths = [
            r"C:\Program Files\GRYPHLINK\games\EndField Game",
            r"D:\GRYPHLINK\games\EndField Game"
        ]
        self.use_hook: bool = False

    def get_installed_version(self):
        try:
            return str(Version(Config.Importers.EFMI.Importer.importer_path / 'Core' / 'EFMI' / 'main.ini'))
        except Exception as e:
            return ''

    def validate_game_exe_path(self, game_path: Path) -> Path:
        for game_exe_name in Config.Importers.EFMI.Importer.game_exe_names:
            game_exe_path = game_path / game_exe_name
            if game_exe_path.is_file():
                return game_exe_path
        raise ValueError(L('error_game_exe_not_found', 'Game executable {exe_name} not found!').format(exe_name=' / '.join(Config.Importers.EFMI.Importer.game_exe_names)))

    def get_start_cmd(self, game_path: Path) -> Tuple[Path, List[str], Optional[str]]:
        game_exe_path = self.validate_game_exe_path(game_path)
        work_dir_path = str(game_exe_path.parent)
        return game_exe_path, ['-force-d3d11'], work_dir_path

    def initialize_game_launch(self, game_path: Path):
        # if Config.Active.Importer.custom_launch_inject_mode != 'Bypass':
        pass

