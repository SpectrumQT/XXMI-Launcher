import re
import os
import json
import shutil
import sqlite3
import logging
import ctypes

from dataclasses import field
from typing import Dict, Union, Optional, Tuple, List

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
class WWMIConfig(ModelImporterConfig):
    importer_folder: str = 'WWMI/'
    launch_options: str = '-SkipSplash'
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
                'texture_hash': 1,
                'track_texture_updates': 1,
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
        'shader_cache': {
            'Rendering': {
                'cache_shaders': {'on': 1, 'off': 0},
            },
        },
        'dump_shaders': {
            'Hunting': {
                'marking_actions': {'on': 'clipboard hlsl asm regex', 'off': 'clipboard'},
            },
        },
    })
    engine_ini: Dict[str, Dict[str, Union[str, int, float]]] = field(default_factory=lambda: {
        'ConsoleVariables': {
            'r.Kuro.SkeletalMesh.LODDistanceScale': 24,
            'r.Streaming.FullyLoadUsedTextures': 1,
        }
    })
    apply_perf_tweaks: bool = False
    unlock_fps: bool = False
    perf_tweaks: Dict[str, Dict[str, Union[str, int, float]]] = field(default_factory=lambda: {
        'SystemSettings': {
            'r.Streaming.HLODStrategy': 2,
            'r.Streaming.LimitPoolSizeToVRAM': 1,
            'r.Streaming.PoolSizeForMeshes': -1,
            'r.XGEShaderCompile': 0,
            'FX.BatchAsync': 1,
            'FX.EarlyScheduleAsync': 1,
            'fx.Niagara.ForceAutoPooling': 1,
            'wp.Runtime.KuroRuntimeStreamingRangeOverallScale': 0.5,
            'tick.AllowAsyncTickCleanup': 1,
            'tick.AllowAsyncTickDispatch': 1,
        }
    })


@dataclass
class WWMIPackageConfig:
    Importer: WWMIConfig = field(
        default_factory=lambda: WWMIConfig()
    )
    Migoto: MigotoManagerConfig = field(
        default_factory=lambda: MigotoManagerConfig()
    )


class WWMIPackage(ModelImporterPackage):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='WWMI',
            auto_load=False,
            github_repo_owner='SpectrumQT',
            github_repo_name='WWMI',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='WWMI-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=False,
            installation_path='WWMI/',
            requirements=['XXMI'],
        ))

    def get_installed_version(self):
        try:
            return str(
                Version(Config.Importers.WWMI.Importer.importer_path / 'Core' / 'WWMI' / 'WuWa-Model-Importer.ini'))
        except Exception as e:
            return ''

    def autodetect_game_folder(self) -> Path:
        kuro_config_path = Path(os.getenv('APPDATA')) / 'KRLauncher' / 'G153' / 'C50003' / 'kr_starter_game.json'
        if not kuro_config_path.is_file():
            raise ValueError(f'Launch config {kuro_config_path} does not exist!')
        with open(kuro_config_path, 'r', encoding='utf-8') as f:
            launch_path = json.load(f).get('path', None)
            if launch_path is None:
                raise ValueError(f'Failed to locate game path in launch config')
            return Path(launch_path)

    def validate_game_path(self, game_folder):
        Events.Fire(Events.Application.StatusUpdate(status='Validating game path...'))
        game_path = super().validate_game_path(game_folder)
        # Go down one level if specified folder is official launcher folder
        if 'Wuthering Waves Game' in [x.name for x in game_path.iterdir() if x.is_dir()]:
            game_path = game_path / 'Wuthering Waves Game'
        # Make sure that game folder contains critical resources
        for dir_name in ['Client', 'Engine']:
            if dir_name not in [x.name for x in game_path.iterdir() if x.is_dir()]:
                raise ValueError(f'Game folder must contain {dir_name} folder!')
        return game_path

    def validate_game_exe_path(self, game_path: Path) -> Path:
        game_exe_path = game_path / 'Client' / 'Binaries' / 'Win64' / 'Client-Win64-Shipping.exe'
        if not game_exe_path.is_file():
            raise ValueError(f'Game executable {game_exe_path} does not exist!')
        return game_exe_path

    def get_start_cmd(self, game_path: Path) -> Tuple[Path, List[str], Optional[str]]:
        game_exe_path = self.validate_game_exe_path(game_path)
        return game_exe_path, ['Client', '-DisableModule=streamline'], str(game_exe_path.parent)

    def initialize_game_launch(self, game_path: Path):
        self.restore_streamline(game_path)
        self.verify_plugins(game_path)
        self.update_engine_ini(game_path)
        self.update_wwmi_ini()
        if Config.Importers.WWMI.Importer.unlock_fps:
            self.update_local_storage_db(game_path)

    def update_engine_ini(self, game_path: Path):
        Events.Fire(Events.Application.StatusUpdate(status='Updating Engine.ini...'))

        engine_ini_path = game_path / 'Client' / 'Saved' / 'Config' / 'WindowsNoEditor' / 'Engine.ini'

        if not engine_ini_path.exists():
            Paths.verify_path(engine_ini_path.parent)
            with open(engine_ini_path, 'w', encoding='utf-8') as f:
                f.write('')

        Events.Fire(Events.Application.VerifyFileAccess(path=engine_ini_path, write=True))
        with open(engine_ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(option_value_spacing=False, inline_comments=True, add_section_spacing=True), f)

        for section_name, section_data in Config.Importers.WWMI.Importer.engine_ini.items():
            for option_name, option_value in section_data.items():
                ini.set_option(section_name, option_name, option_value)

        if Config.Importers.WWMI.Importer.apply_perf_tweaks:
            for section_name, section_data in Config.Importers.WWMI.Importer.perf_tweaks.items():
                for option_name, option_value in section_data.items():
                    ini.set_option(section_name, option_name, option_value)

        if ini.is_modified():
            with open(engine_ini_path, 'w', encoding='utf-8') as f:
                f.write(ini.to_string())

    def update_local_storage_db(self, game_path: Path):
        Events.Fire(Events.Application.StatusUpdate(status='Setting FPS limit to 120...'))
        local_storage_path = game_path / 'Client' / 'Saved' / 'LocalStorage'
        Paths.verify_path(local_storage_path)
        # Locate .db files within LocalStorage dir, there may be multiple files there, i.e. LocalStorage2.db
        db_paths = list(local_storage_path.glob('LocalStorage*.db'))
        log.debug(f'Found {len(db_paths)} database files in {local_storage_path}')
        if len(db_paths) == 0:
            raise ValueError(f'Failed to force 120 FPS!\n\n'
                             'Settings file does not exist! Please start the game at least once.')
        for db_path in db_paths:
            # Connect to the database file
            log.debug(f'Connecting {db_path}...')
            Events.Fire(Events.Application.VerifyFileAccess(path=db_path, write=True))
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            # Fetch existing FPS setting data
            result = cursor.execute("SELECT value FROM LocalStorage WHERE key='CustomFrameRate'")
            data = result.fetchone()
            # Extract FPS setting value
            if data is None or len(data) != 1:
                custom_frame_rate = -1
            else:
                custom_frame_rate = int(data[0])
            log.debug(f'Current FPS setting: {custom_frame_rate}')
            # Write new FPS setting value
            if custom_frame_rate != 120:
                log.debug(f'Changing FPS setting to {120}...')
                cursor.execute(f"UPDATE LocalStorage SET value = '{120}' WHERE key='CustomFrameRate'")
                connection.commit()
            # Close the database file
            connection.close()
            log.debug(f'Connection closed: {db_path}')

    def verify_plugins(self, game_path: Path):
        Events.Fire(Events.Application.StatusUpdate(status='Checking engine plugins integrity...'))

        plugins_path = game_path / 'Engine' / 'Plugins' / 'Runtime' / 'Nvidia'
        plugin_paths = [
            plugins_path / 'DLSS',
            plugins_path / 'Streamline',
        ]

        for path in plugin_paths:
            path = path / 'Binaries' / 'ThirdParty' / 'Win64'
            if not path.is_dir() or len([x for x in path.iterdir() if x.suffix == '.dll']) == 0:
                Events.Fire(Events.Application.ShowWarning(
                    modal=True,
                    message=f'Wuthering Waves installation is damaged!\n\n'
                            f'Removal of NVIDIA plugins is no longer required and may cause crashes!\n\n'
                            f'Please use official launcher to fix the game (wrench button in top-right corner).'
                ))
                break

    def remove_streamline(self, game_path: Path):
        Events.Fire(Events.Application.StatusUpdate(status='Checking Streamline plugin...'))

        streamline_path = game_path / 'Engine' / 'Plugins' / 'Runtime' / 'Nvidia' / 'Streamline'
        if not streamline_path.exists():
            return

        Events.Fire(Events.Application.StatusUpdate(status='Disabling Streamline plugin...'))

        plugin_backups_path = Paths.App.Backups / 'Plugins'

        self.move_contents(streamline_path, plugin_backups_path)

    def restore_streamline(self, game_path: Path):
        plugin_backups_path = Paths.App.Backups / 'Plugins'
        if not plugin_backups_path.is_dir():
            return
        Events.Fire(Events.Application.StatusUpdate(status='Restoring Streamline plugin...'))
        streamline_path = game_path / 'Engine' / 'Plugins' / 'Runtime' / 'Nvidia'
        self.move_contents(plugin_backups_path, streamline_path)

    def update_wwmi_ini(self):
        Events.Fire(Events.Application.StatusUpdate(status='Updating WuWa-Model-Importer.ini...'))

        wwmi_ini_path = Config.Importers.WWMI.Importer.importer_path / 'Core' / 'WWMI' / 'WuWa-Model-Importer.ini'
        if not wwmi_ini_path.exists():
            raise ValueError('Failed to locate Core/WWMI/WuWa-Model-Importer.ini!')

        Events.Fire(Events.Application.VerifyFileAccess(path=wwmi_ini_path, write=True))
        with open(wwmi_ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(option_value_spacing=True, ignore_comments=False), f)

        screen_width, screen_height = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
        ini.set_option('Constants', 'global $window_width', screen_width)
        ini.set_option('Constants', 'global $window_height', screen_height)

        if ini.is_modified():
            with open(wwmi_ini_path, 'w', encoding='utf-8') as f:
                f.write(ini.to_string())


class Version:
    def __init__(self, wwmi_ini_path):
        self.wwmi_ini_path = wwmi_ini_path
        self.version = None
        self.parse_version()

    def parse_version(self):
        with open(self.wwmi_ini_path, 'r', encoding='utf-8') as f:

            version_pattern = re.compile(r'^global \$wwmi_version = (\d+)\.*(\d)(\d*)')

            for line in f.readlines():

                result = version_pattern.findall(line)

                if len(result) != 1:
                    continue

                result = list(result[0])

                if len(result) == 2:
                    result.append(0)

                if len(result) != 3:
                    raise ValueError(f'Malformed WWMI version!')

                self.version = result

                return

        raise ValueError(f'Failed to locate WWMI version!')

    def __str__(self) -> str:
        return f'{self.version[0]}.{self.version[1]}.{self.version[2]}'

    def as_float(self):
        return float(f'{self.version[0]}.{self.version[1]}{self.version[2]}')

    def as_ints(self):
        return [map(int, self.version)]
