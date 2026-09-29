import re
import logging

from dataclasses import dataclass, field
from typing import Any
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.locale_manager import L
from core.package_manager import PackageMetadata

from core.config.enums import InjectMode
from core.packages.model_importers.model_importer import ModelImporterPackage, ModelImporterConfig, Version
from core.packages.migoto_package import MigotoManagerConfig
from core.platforms.game import Game

log = logging.getLogger(__name__)


@dataclass
class EFMIConfig(ModelImporterConfig):
    game: Game = Game.ARKNIGHTS_ENDFIELD
    game_exe_names: list[str] = field(default_factory=lambda: ['Endfield.exe'])
    game_folder_names: list[str] = field(default_factory=lambda: ['EndField Game'])
    game_folder_children: list[str] = field(default_factory=lambda: ['Endfield_Data'])
    game_process_exe: str = "Endfield.exe"
    process_timeout: int = 60
    importer_folder: str = 'EFMI/'
    launch_options: str = ''
    d3d11_mode_cmd_args: str = "-force-d3d11"
    xxmi_dll_inject_mode: InjectMode = InjectMode.DIRECT
    d3dx_ini: dict[str, dict[str, dict[str, Any]]] = field(default_factory=lambda: {
        'core': {
            'Loader': {
                'loader': 'XXMI Launcher.exe',
            },
        },
        'enforce_rendering': {
            'Rendering': {
                'texture_hash': 0,
                'track_texture_updates': 0,
                'track_region_hashes': 1,
                'track_implicit_index_buffers': 1,
                'allow_buffer_resize': 0,
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
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2}))\r?$',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=False,
            installation_path='EFMI/',
            requirements=['XXMI'],
            required_versions={'XXMI': '0.7.5'},
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

    def get_installed_version(self):
        try:
            return str(Version(Config.Importers.EFMI.Importer.importer_path / 'Core' / 'EFMI' / 'main.ini'))
        except Exception as e:
            return ''
