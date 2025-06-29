import re
import os
import logging
import shutil
import winreg
import json

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Union, Tuple, Optional, List
from core.locale_manager import T, L
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import PackageMetadata

from core.utils.ini_handler import IniHandler, IniHandlerSettings
from core.utils.process_tracker import wait_for_process_exit, WaitResult, ProcessPriority
from core.packages.model_importers.model_importer import ModelImporterPackage, ModelImporterConfig
from core.packages.migoto_package import MigotoManagerConfig

log = logging.getLogger(__name__)


@dataclass
class HIMIConfig(ModelImporterConfig):
    importer_folder: str = 'HIMI/'
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
    unlock_fps_value: int = 120
    disable_dcr: bool = True
    enable_hdr: bool = False


@dataclass
class HIMIPackageConfig:
    Importer: HIMIConfig = field(
        default_factory=lambda: HIMIConfig()
    )
    Migoto: MigotoManagerConfig = field(
        default_factory=lambda: MigotoManagerConfig()
    )


class HIMIPackage(ModelImporterPackage):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='HIMI',
            auto_load=False,
            github_repo_owner='leotorrez',
            github_repo_name='HIMI-Package',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='HIMI-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEeigvK7REsX3f/vb+RRuFkZt/6VRbykI2oQcEU3IiI3N9s6jWqKkxAE2cTC9wKXDlkeSzlHjPxgzrTrKdqwkFzROMjw5T2LixFB5BYaT633aU/cCiHDbArIJ46+GrqemG',
            exit_after_update=False,
            installation_path='HIMI/',
            requirements=['XXMI'],
        ))

    def get_installed_version(self):
        try:
            return str(Version(Config.Importers.HIMI.Importer.importer_path / 'Core' / 'HIMI' / 'main.ini'))
        except Exception as e:
            return ''

    def autodetect_game_folders(self) -> List[Path]:
        paths = self.reg_search_game_folders(['BH3.exe'])

        common_pattern = re.compile(r'([a-zA-Z]:[^:\"\']*Genshin[^:\"\']*)')
        known_children = ['BH3_Data']

        # "installPath":"D:\\Games\\Genshin Impact game"
        # "persistentInstallPath":"D:\\Games\\Genshin Impact game"
        hoyoplay_pattern = re.compile(r'\"(?:installPath|persistentInstallPath)\":\"([a-zA-Z]:[^:^\"]*)\"')

        paths += self.get_paths_from_hoyoplay([common_pattern, hoyoplay_pattern], known_children)

        # WwiseUnity: Setting Plugin DLL path to: D:/Games/Honkai Impact 3rd game/BH3_Data\Plugins\
        # TelemetryInterface path:D:\Games\Honkai Impact 3rd game\BH3_Data\SDKCaches, level:2, dest:0
        output_log_pattern = re.compile(r'([a-zA-Z]:[^:\"\']*)(?:Plugins|SDKCaches|StreamingAssets|Persistent)')

        output_log_path = Path(os.getenv('APPDATA')).parent / 'LocalLow' / 'miHoYo' / 'Honkai Impact 3rd' / 'output_log.txt'
        paths += self.find_paths_in_file(output_log_path, [common_pattern, output_log_pattern], known_children)

        return paths

    def validate_game_exe_path(self, game_path: Path) -> Path:
        game_exe_path = game_path / 'BH3.exe'
        if not game_exe_path.is_file():
            raise ValueError(T('himi_game_exe_not_found', 'Game executable {} not found!').format(game_exe_path.name))
        return game_exe_path

    def get_start_cmd(self, game_path: Path) -> Tuple[Path, List[str], Optional[str]]:
        game_exe_path = self.validate_game_exe_path(game_path)
        work_dir_path = str(game_exe_path.parent)
        return game_exe_path, [], work_dir_path

    def initialize_game_launch(self, game_path: Path):
        if Config.Active.Importer.custom_launch_inject_mode != 'Bypass':
            self.update_himi_ini()
        if Config.Importers.HIMI.Importer.unlock_fps:
            try:
                self.unlock_fps()
            except Exception as e:
                raise ValueError(T('himi_fps_unlock_failed', 'Failed to configure FPS: {}').format(str(e)))

    def update_himi_ini(self):
        Events.Fire(Events.Application.StatusUpdate(status=L('himi_updating_ini', 'Updating HIMI main.ini...')))

        himi_ini_path = Config.Importers.HIMI.Importer.importer_path / 'Core' / 'HIMI' / 'main.ini'
        if not himi_ini_path.exists():
            raise ValueError(T('himi_ini_not_found', 'Failed to locate Core/HIMI/main.ini!'))

        Events.Fire(Events.Application.VerifyFileAccess(path=himi_ini_path, write=True))

        # with open(himi_ini_path, 'r', encoding='utf-8') as f:
        #     ini = IniHandler(IniHandlerSettings(option_value_spacing=True, ignore_comments=False), f)
        #
        # if ini.is_modified():
        #     log.debug(f'Writing main.ini...')
        #     with open(himi_ini_path, 'w', encoding='utf-8') as f:
        #         f.write(ini.to_string())

    def unlock_fps(self):
        # Open HSR registry key
        try:
            settings_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\\miHoYo\\Honkai Impact 3rd', 0, winreg.KEY_ALL_ACCESS)
        except FileNotFoundError:
            raise ValueError(
                T('himi_registry_key_not_found',
                  'Honkai Impact 3rd registry key is not found!\n\n'
                  'Please start the game without FPS tweak, change FPS to any value to create the record and try again.\n\n'
                  'Note: Tweak is supported only for the Global client and will not work for CN.')
            )
        # Read binary Graphics Settings key
        try:
            (settings_bytes, regtype) = winreg.QueryValueEx(settings_key, 'GENERAL_DATA_V2_PersonalGraphicsSettingV2_h3480068519')
        except FileNotFoundError as e:
            raise ValueError(
                T('himi_graphics_settings_not_found',
                  'Graphics Settings record is not found in Honkai Impact 3rd registry!\n\n'
                  'Please start the game without FPS tweak, change FPS to any value to create the record and try again.')
            )
        if regtype != winreg.REG_BINARY:
            raise ValueError(T('himi_unknown_graphics_format', 'Unknown Graphics Settings format: Data type {} is not {} of REG_BINARY!').format(regtype, winreg.REG_BINARY))
        # Read bytes till the first null byte as settings ascii string
        null_byte_pos = settings_bytes.find(b'\x00')
        if null_byte_pos != -1:
            settings_bytes = settings_bytes[:null_byte_pos]
        else:
            log.debug(f'Binary record GENERAL_DATA_V2_PersonalGraphicsSettingV2_h3480068519 is not null-terminated!')
        settings_str = settings_bytes.decode('ascii')
        # Load settings string to dict
        settings_dict = json.loads(settings_str)
        # Ensure settings dict has known keys
        if 'TargetFrameRateForInLevel' not in settings_dict:
            raise ValueError(T('himi_fps_key_not_found', 'Unknown Graphics Settings format: "TargetFrameRateForInLevel" key not found!'))
        # Exit early if FPS is already set to Config.Importers.HIMI.Importer.unlock_fps_value
        if settings_dict['TargetFrameRateForInLevel'] == Config.Importers.HIMI.Importer.unlock_fps_value:
            return
        # Set new settings
        settings_dict['TargetFrameRateForInLevel'] = Config.Importers.HIMI.Importer.unlock_fps_value
        settings_dict['TargetFrameRateForOthers'] = Config.Importers.HIMI.Importer.unlock_fps_value
        # Serialize settings dict back to string
        settings_str = json.dumps(settings_dict, separators=(',', ':'))
        # Encode settings string as ascii bytes and terminate it with null
        settings_bytes = bytes(settings_str.encode('ascii')) + b'\x00'
        # Write encoded settings back to registry
        winreg.SetValueEx(settings_key, 'GENERAL_DATA_V2_PersonalGraphicsSettingV2_h3480068519', None, regtype, settings_bytes)


class Version:
    def __init__(self, himi_ini_path):
        self.himi_ini_path = himi_ini_path
        self.version = None
        self.parse_version()

    def parse_version(self):
        with open(self.himi_ini_path, 'r', encoding='utf-8') as f:

            version_pattern = re.compile(r'^global \$version = (\d+)\.*(\d)(\d*)')

            for line in f.readlines():

                result = version_pattern.findall(line)

                if len(result) != 1:
                    continue

                result = list(result[0])

                if len(result) == 2:
                    result.append(0)

                if len(result) != 3:
                    raise ValueError(T('himi_malformed_version', 'Malformed HIMI version!'))

                self.version = result

                return

        raise ValueError(T('himi_version_not_found', 'Failed to locate HIMI version!'))

    def __str__(self) -> str:
        return f'{self.version[0]}.{self.version[1]}.{self.version[2]}'

    def as_float(self):
        return float(f'{self.version[0]}.{self.version[1]}{self.version[2]}')

    def as_ints(self):
        return [map(int, self.version)]