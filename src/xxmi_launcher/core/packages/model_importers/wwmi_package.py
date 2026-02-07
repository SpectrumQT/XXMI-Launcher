import re
import os
import json
import sqlite3
import logging

from dataclasses import dataclass, field
from typing import Dict, Union, Optional, Tuple, List
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
class WWMIConfig(ModelImporterConfig):
    game_exe_names: List[str] = field(default_factory=lambda: ['Wuthering Waves.exe'])
    game_folder_names: List[str] = field(default_factory=lambda: ['Wuthering Waves Game'])
    game_folder_children: List[str] = field(default_factory=lambda: ['Client', 'Data'])
    importer_folder: str = 'WWMI/'
    use_launch_options: bool = False
    launch_options: str = '-SkipSplash'
    xxmi_dll_init_delay: int = 500
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
        'dump_shaders': {
            'Hunting': {
                'marking_actions': {'on': 'clipboard hlsl asm regex', 'off': 'clipboard'},
            },
        },
    })
    apply_perf_tweaks: bool = False
    unlock_fps: bool = False
    force_max_lod_bias: bool = False
    disable_wounded_fx: bool = False
    disable_wounded_fx_warned: bool = False
    perf_tweaks: Dict[str, Dict[str, Union[str, int, float]]] = field(default_factory=lambda: {
        'SystemSettings': {
            'r.Streaming.HLODStrategy': 2,
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
    mesh_lod_distance_scale: float = 1.0
    mesh_lod_distance_offset: int = -10
    texture_streaming_boost: float = 20.0
    texture_streaming_min_boost: float = 0.0
    texture_streaming_use_all_mips: bool = True
    texture_streaming_pool_size: int = 0
    texture_streaming_limit_to_vram: bool = True
    texture_streaming_fixed_pool_size: bool = True


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
            github_repo_name='WWMI-Package',
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
            return str(Version(Config.Importers.WWMI.Importer.importer_path / 'Core' / 'WWMI' / 'WuWa-Model-Importer.ini', pattern=r'^global \$wwmi_version = (\d+)\.*(\d)(\d*)'))
        except Exception as e:
            return ''

    def normalize_game_path(self, game_path: Path) -> Path:
        if not game_path.is_absolute():
            raise ValueError(L('error_game_path_not_absolute', 'Failed to normalize path {path}: Path is not absolute!').format(path=game_path))

        if (game_path / 'Wuthering Waves.exe').is_file():
            return game_path

        game_path_original = game_path

        for path in self.scan_directory(game_path):
            if path.is_file() and path.name == 'Wuthering Waves.exe':
                return Path(path).parent

        for i in range(len(game_path.parents)):
            game_path = game_path.parent
            for path in game_path.iterdir():
                if path.is_file() and path.name == 'Wuthering Waves.exe':
                    return Path(path).parent

        raise ValueError(L('error_wuthering_waves_exe_not_found', 'Failed to normalize path {path}: Wuthering Waves.exe not found!').format(path=game_path_original))

    def autodetect_game_folders(self) -> List[Path]:
        paths = self.reg_search_game_folders(['Client-Win64-Shipping.exe'])

        kuro_launcher_path = Path(os.getenv('APPDATA')) / 'KRLauncher'
        for root, dirs, files in kuro_launcher_path.walk():
            for file in files:
                if file != 'kr_starter_game.json':
                    continue
                file_path = root / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        path = json.load(f).get('path', None)
                        if path is not None:
                            paths.append(path)
                except:
                    continue

        result = []

        for path in paths:
            try:
                result.append(self.normalize_game_path(path))
            except:
                pass

        return result

    def validate_game_path(self, game_folder):
        game_path = super().validate_game_path(game_folder)
        game_path = self.normalize_game_path(game_path)
        # Make sure that game folder contains critical resources
        exe_path = game_path / 'Wuthering Waves.exe'
        if not exe_path.is_file():
            raise ValueError(L('error_wwmi_game_folder_missing_files', 'Game folder must contain `Wuthering Waves.exe` and `Client` & `Engine` folders!'))
        else:
            common_folder = self.get_parent_directory(game_path, 'common')
            if common_folder is not None and common_folder.parent.name == 'steamapps':
                # Steam installation detected
                if game_path.parent.name != 'common':
                    # Invalid file structure, most likely caused by manual folder relocation
                    Events.Fire(Events.Application.ShowError(
                        modal=True,
                        confirm_text=L('message_button_ok', 'OK'),
                        message=L('message_text_wwmi_invalid_steam_installation', """
                            Invalid Wuthering Waves installation detected for Steam:
                            {game_path}
                            
                            {folder_name} folder with {exe_name} must be directly placed in:
                            {common_folder}
                            
                            Please run game file repair via Steam or fix it manually.
                        """).format(
                            game_path=game_path, folder_name=game_path.name, exe_name=exe_path.name, common_folder=common_folder
                        )
                    ))
                    raise ValueError(L('error_steam_game_repair_required', 'Game installation must be repaired via Steam!'))
        for dir_name in ['Client', 'Engine']:
            if dir_name not in [x.name for x in game_path.iterdir() if x.is_dir()]:
                raise ValueError(L('error_game_folder_missing_folder', 'Game folder must contain {dir_name} folder!').format(dir_name=dir_name))
        return game_path

    def validate_game_exe_path(self, game_path: Path) -> Path:
        game_exe_path = game_path / 'Client' / 'Binaries' / 'Win64' / 'Client-Win64-Shipping.exe'
        if not game_exe_path.is_file():
            raise ValueError(L('error_game_exe_not_found', 'Game executable {exe_name} not found!').format(exe_name=game_exe_path.name))
        return game_exe_path

    def get_start_cmd(self, game_path: Path) -> Tuple[Path, List[str], Optional[str]]:
        game_exe_path = self.validate_game_exe_path(game_path)
        if Config.Importers.WWMI.Importer.use_launch_options:
            # Start WW directly to support launch options customization
            return game_exe_path, ['-dx11'], str(game_exe_path.parent)
        else:
            # Start WW via wrapper exe (solves crashes for NVidia Optimus and some Steam version users)
            return game_path / 'Wuthering Waves.exe', ['-dx11'], str(game_path)

    def initialize_game_launch(self, game_path: Path):
        if Config.Active.Importer.custom_launch_inject_mode != 'Bypass':
            self.update_engine_ini(game_path)
            self.update_device_profiles_ini(game_path)
            self.update_game_user_settings_ini(game_path)
        self.configure_settings(game_path)

    def configure_settings(self, game_path: Path):
        if not any([Config.Importers.WWMI.Importer.configure_game, Config.Importers.WWMI.Importer.unlock_fps]):
            return

        Events.Fire(Events.Application.StatusUpdate(status=L('status_configuring_settings', 'Configuring in-game settings...')))

        try:
            with SettingsManager(game_path) as settings_manager:
                if Config.Importers.WWMI.Importer.unlock_fps:
                    # Set frame rate to 120
                    settings_manager.set_fps_setting(120)
                else:
                    # Remove any existing triggers locking the frame rate setting
                    settings_manager.reset_fps_setting()

                if Config.Active.Importer.custom_launch_inject_mode == 'Bypass':
                    return

                if not Config.Importers.WWMI.Importer.configure_game:
                    return

                # Set "LOD Bias" to "Ultra High" - required to force high quality textures mods are made for
                if Config.Importers.WWMI.Importer.force_max_lod_bias:
                    settings_manager.set_setting('ImageDetail', '3')

                # Force Ray Tracing Off as it doesn't work with DX11 aka WWMI
                settings_manager.set_setting('RayTracing', '0')
                settings_manager.set_setting('RayTracedReflection', '0')
                settings_manager.set_setting('RayTracedGI', '0')

                # Take care of Wounded Effect that 'breaks' modded textures if not handled properly
                if not Config.Importers.WWMI.Importer.disable_wounded_fx_warned:
                    if settings_manager.get_setting('SkinDamageMode') == '1':
                        user_dialogue = Events.Application.ShowWarning(
                            modal=True,
                            title=L('message_title_wounded_effect_detected', 'Wounded Effect Detected'),
                            confirm_text=L('message_button_disable', 'Disable'),
                            cancel_text=L('message_button_keep_enabled', 'Keep Enabled'),
                            message=L('message_text_wounded_effect_detected', """
                                Looks like Wounded Effect is enabled in game settings.
                                It is not supported by most mods and textures will break after few hits taken.
                                
                                Click `Disable` to turn it Off and ensure proper rendering of modded textures.
                                Click `Keep Enabled` if you never get hit or use Injured Effect Remover tool.
                            """),
                        )
                        Config.Importers.WWMI.Importer.disable_wounded_fx_warned = True
                        user_requested_injured_fx_disable = Events.Call(user_dialogue)
                        if user_requested_injured_fx_disable:
                            Config.Importers.WWMI.Importer.disable_wounded_fx = True

                if Config.Importers.WWMI.Importer.disable_wounded_fx:
                    settings_manager.set_setting('SkinDamageMode', '0')
                else:
                    settings_manager.set_setting('SkinDamageMode', '1')


        except Exception as e:

            if Config.Importers.WWMI.Importer.unlock_fps:
                raise Exception(L('error_wwmi_fps_unlock_failed', """
                    Failed to force 120 FPS!
                    Please disable `Force 120 FPS` in launcher's General Settings.
                    
                    {error_text}
                """).format(error_text=e)) from e

            if Config.Importers.WWMI.Importer.configure_game:
                raise Exception(L('error_wwmi_game_config_failed', """
                    Failed to configure in-game settings for WWMI!
                    Please disable `Configure Game Settings` in launcher's General Settings and check in-game settings:
                    * Graphics > `Graphics Quality` must be `Quality`.
                    
                    {error_text}
                """).format(error_text=e)) from e

    def update_engine_ini(self, game_path: Path):
        engine_ini_path = game_path / 'Client' / 'Saved' / 'Config' / 'WindowsNoEditor' / 'Engine.ini'

        Events.Fire(Events.Application.StatusUpdate(
            status=L('status_updating_file', 'Updating {file_name}...').format(file_name=engine_ini_path.name))
        )

        if not engine_ini_path.exists():
            Paths.verify_path(engine_ini_path.parent)
            with open(engine_ini_path, 'w', encoding='utf-8') as f:
                f.write('')

        Events.Fire(Events.Application.VerifyFileAccess(path=engine_ini_path, write=True))
        with open(engine_ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(option_value_spacing=False, inline_comments=True, add_section_spacing=True, right_split=True), f)

        # if '/Script/Engine.RendererRTXSettings' in Config.Active.Importer.engine_ini.keys():
        #     if ini.get_section('/Script/Engine.RendererRTXSettings') is not None:
        #         ini.remove_section('/Script/Engine.RendererRTXSettings')
        #     del Config.Active.Importer.engine_ini['/Script/Engine.RendererRTXSettings']
        #
        # for section_name, section_data in Config.Importers.WWMI.Importer.engine_ini.items():
        #     for option_name, option_value in section_data.items():
        #         ini.set_option(section_name, option_name, option_value)
        # console_variables = Config.Importers.WWMI.Importer.engine_ini.get('ConsoleVariables', None)
        # default_streaming_boost = console_variables.get('r.Streaming.Boost', None) if console_variables else None

        if Config.Importers.WWMI.Importer.apply_perf_tweaks:
            for section_name, section_data in Config.Importers.WWMI.Importer.perf_tweaks.items():
                for option_name, option_value in section_data.items():
                    ini.set_option(section_name, option_name, option_value)

    def update_device_profiles_ini(self, game_path: Path):
        device_profiles_ini_path = game_path / 'Client' / 'Saved' / 'Config' / 'WindowsNoEditor' / 'DeviceProfiles.ini'

        Events.Fire(Events.Application.StatusUpdate(
            status=L('status_updating_file', 'Updating {file_name}...').format(file_name=device_profiles_ini_path.name))
        )

        if not device_profiles_ini_path.exists():
            Paths.verify_path(device_profiles_ini_path.parent)
            with open(device_profiles_ini_path, 'w', encoding='utf-8') as f:
                f.write('')

        Events.Fire(Events.Application.VerifyFileAccess(path=device_profiles_ini_path, write=True))
        with open(device_profiles_ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(option_value_spacing=False, inline_comments=True, add_section_spacing=True, right_split=True), f)

        # # Remove UsingNewKuroStreaming option (ancient 3rd-party configs set it to 0 with bad results)
        # ini.remove_option('r.Streaming.UsingNewKuroStreaming')
        #
        # # Remove Boost option if it matches configured MinBoost (mostly to clear one from pre-3.0 auto-config)
        # ini.remove_option('r.Streaming.Boost',
        #                   section_name='ConsoleVariables',
        #                   option_value=Config.Importers.WWMI.Importer.texture_streaming_boost)

        console_variables_options = {
            # Controls how far game starts to replace weighted meshes with LoDs
            'r.Kuro.SkeletalMesh.LODDistanceScaleDeviceOffset': Config.Importers.WWMI.Importer.mesh_lod_distance_offset,
            # Controls how aggressively higher resolution textures are pushed to VRAM
            # Mods contain texture hashes only for original model and won't apply to LoDs
            'r.Streaming.Boost': Config.Importers.WWMI.Importer.texture_streaming_boost,
            # Controls the minimal texture boost floor value
            'r.Streaming.MinBoost': Config.Importers.WWMI.Importer.texture_streaming_min_boost,
            # Controls whether texture resolution limits imposed by LOD Bias are applied
            'r.Streaming.UseAllMips': int(Config.Importers.WWMI.Importer.texture_streaming_use_all_mips),
            # Controls amount of VRAM used for textures streaming
            # When set to 0, tends to keep full resolution textures in VRAM, so LoDs don't break mods
            'r.Streaming.PoolSize': Config.Importers.WWMI.Importer.texture_streaming_pool_size,
            # Prevents pool size from exceeding VRAM
            # Doesn't explicitly affect mods, but acts as failsafe for low and mid-range GPUs for PoolSize=0
            'r.Streaming.LimitPoolSizeToVRAM': int(Config.Importers.WWMI.Importer.texture_streaming_limit_to_vram),
            # Controls whether pool size can grow/shrink automatically or is locked to a fixed value
            # When enabled, minimizes mip levels pop in/out at cost of pool size being locked after game start
            'r.Streaming.UseFixedPoolSize': int(Config.Importers.WWMI.Importer.texture_streaming_fixed_pool_size),
        }
        log.debug(f'Using console variables: {console_variables_options}')

        section_names = [
            'Windows_Highest DeviceProfile', 'Windows_VeryHigh DeviceProfile', 'Windows_High DeviceProfile',
            'Windows_Mid DeviceProfile', 'Windows_Low DeviceProfile', 'Windows_Lowest DeviceProfile'
        ]

        for section_name in section_names:

            for option_name, option_value in console_variables_options.items():
                # Append `CVars=` "prefix" to option name
                option_name = f'CVars={option_name}'
                # Remove duplicate settings
                option_values = ini.get_option_values(option_name, section_name=section_name)
                if len(option_values) > 1:
                    ini.remove_option(option_name, section_name=section_name, option_value=option_value, not_equal=True)
                # Set option value
                ini.set_option(section_name, option_name, option_value)

        if ini.is_modified():
            with open(device_profiles_ini_path, 'w', encoding='utf-8') as f:
                f.write(ini.to_string())

    def update_game_user_settings_ini(self, game_path: Path):
        if not Config.Importers.WWMI.Importer.unlock_fps:
            return

        Events.Fire(Events.Application.StatusUpdate(status=L('status_updating_file', 'Updating {file_name}...').format(file_name='GameUserSettings.ini')))

        ini_path = game_path / 'Client' / 'Saved' / 'Config' / 'WindowsNoEditor' / 'GameUserSettings.ini'

        if not ini_path.exists():
            Paths.verify_path(ini_path.parent)
            with open(ini_path, 'w', encoding='utf-8') as f:
                f.write('')

        Events.Fire(Events.Application.VerifyFileAccess(path=ini_path, write=True))
        with open(ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(option_value_spacing=False, inline_comments=True, add_section_spacing=True), f)

        ini.set_option('/Script/Engine.GameUserSettings', 'FrameRateLimit', 120.000000)

        if ini.is_modified():
            with open(ini_path, 'w', encoding='utf-8') as f:
                f.write(ini.to_string())


class SettingsManager:
    def __init__(self, game_path: Path):
        self.path = game_path / 'Client' / 'Saved' / 'LocalStorage'
        self.db: Optional[LocalStorage] = None

    def __enter__(self):
        Paths.verify_path(self.path)

        default_db_path = self.path / 'LocalStorage.db'

        # Locate the most recently modified db file
        active_db_path, db_paths = self.get_active_db_path()

        # Remove all LocalStorage files except the most recently modified one
        for db_path in db_paths:
            if db_path != active_db_path:
                self.remove_db(db_path)

        # Rename active LocalStorage files to default
        if active_db_path is not None and active_db_path != default_db_path:
            self.rename_db(active_db_path, default_db_path)

        # Open active LocalStorage file for edits
        self.db = LocalStorage(default_db_path)
        self.db.connect()

        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.db.save()

    def get_setting(self, key: str) -> Union[str, None]:
        return self.db.get_value(key)

    def set_setting(self, key: str, value: Union[int, float, str], lock: bool = False):
        value = str(value)
        self.db.set_value(key, value)
        if lock:
            self.db.set_value_lock_trigger(f'{key}Lock', key, value)

    def set_fps_setting(self, value: int):
        triggers = self.db.get_all_triggers()

        lock_exist = False
        for trigger in triggers:
            # Our trigger already exists, we'll verify its behaviour later
            if trigger.name == 'CustomFrameRateLock':
                lock_exist = True
                continue
            # Delete 3-rd party triggers for CustomFrameRate
            if 'CustomFrameRate' in trigger.body:
                self.db.delete_trigger(trigger.name)

        # Ensure that our trigger is keeping correct FPS value
        if lock_exist:
            fps = self.db.get_value('CustomFrameRate')
            if fps != str(value):
                # FPS value doesn't match our expectations, lets remove potentially corrupted or old trigger
                self.db.delete_trigger('CustomFrameRateLock')
            else:
                return

        # Mix in the magic data (kudos to WakuWakuPadoru for dumping it), else some clients just refuse to go 120 FPS
        self.db.set_value('MenuData', json.dumps({
            '___MetaType___': '___Map___',
            'Content': [
                [1, 100], [2, 100], [3, 100], [4, 100], [5, 0], [6, 0],
                [7, -0.4658685302734375], [10, 3], [11, 3], [20, 0], [21, 0],
                [22, 0], [23, 0], [24, 0], [25, 0], [26, 0], [27, 0], [28, 0],
                [29, 0], [30, 0], [31, 0], [32, 0], [33, 0], [34, 0], [35, 0],
                [36, 0], [37, 0], [38, 0], [39, 0], [40, 0], [41, 0], [42, 0],
                [43, 0], [44, 0], [45, 0], [46, 0], [47, 0], [48, 0], [49, 0],
                [50, 0], [51, 1], [52, 1], [53, 0], [54, 3], [55, 1], [56, 2],
                [57, 1], [58, 1], [59, 1], [61, 0], [62, 0], [63, 1], [64, 1],
                [65, 0], [66, 0], [67, 3], [68, 2], [69, 100], [70, 100], [79, 1],
                [81, 0], [82, 1], [83, 1], [84, 0], [85, 0], [87, 0], [88, 0],
                [89, 50], [90, 50], [91, 50], [92, 50], [93, 1], [99, 0], [100, 30],
                [101, 0], [102, 1], [103, 0], [104, 50], [105, 0], [106, 0.3],
                [107, 0], [112, 0], [113, 0], [114, 0], [115, 0], [116, 0],
                [117, 0], [118, 0], [119, 0], [120, 0], [121, 1], [122, 1],
                [123, 0], [130, 0], [131, 0], [132, 1], [135, 1], [133, 0]
            ]
        }))
        self.db.set_value('PlayMenuInfo', json.dumps({
            '1': 100, '2': 100, '3': 100, '4': 100, '5': 0, '6': 0,
            '7': -0.4658685302734375, '10': 3, '11': 3, '20': 0, '21': 0,
            '22': 0, '23': 0, '24': 0, '25': 0, '26': 0, '27': 0, '28': 0,
            '29': 0, '30': 0, '31': 0, '32': 0, '33': 0, '34': 0, '35': 0,
            '36': 0, '37': 0, '38': 0, '39': 0, '40': 0, '41': 0, '42': 0,
            '43': 0, '44': 0, '45': 0, '46': 0, '47': 0, '48': 0, '49': 0,
            '50': 0, '51': 1, '52': 1, '53': 0, '54': 3, '55': 1, '56': 2,
            '57': 1, '58': 1, '59': 1, '61': 0, '62': 0, '63': 1, '64': 1,
            '65': 0, '66': 0, '67': 3, '68': 2, '69': 100, '70': 100, '79': 1,
            '81': 0, '82': 1, '83': 1, '84': 0, '85': 0, '87': 0, '88': 0,
            '89': 50, '90': 50, '91': 50, '92': 50, '93': 1, '99': 0, '100': 30,
            '101': 0, '102': 1, '103': 0, '104': 50, '105': 0, '106': 0.3,
            '107': 0, '112': 0, '113': 0, '114': 0, '115': 0, '116': 0,
            '117': 0, '118': 0, '119': 0, '120': 0, '121': 1, '122': 1,
            '123': 0, '130': 0, '131': 0, '132': 1
        }))

        # Set FPS setting and lock it from further changes via trigger
        self.set_setting('CustomFrameRate', str(value), True)

    def reset_fps_setting(self):
        triggers = self.db.get_all_triggers()
        # Delete all triggers for CustomFrameRate
        for trigger in triggers:
            if 'CustomFrameRate' in trigger.body:
                self.db.delete_trigger(trigger.name)

    def get_active_db_path(self):
        active_db_path = None
        db_paths = []
        for db_path in self.path.iterdir():
            # Skip anything that doesn't match `LocalStorage*.db` file mask
            if not db_path.is_file() or not db_path.name.startswith('LocalStorage') or db_path.suffix != '.db':
                continue
            # Make sure we can write db file
            Events.Fire(Events.Application.VerifyFileAccess(path=db_path, write=True))
            # Make sure we can write journal file if it exists
            journal_path = db_path.with_suffix('.db-journal')
            if journal_path.is_file():
                Events.Fire(Events.Application.VerifyFileAccess(path=journal_path, write=True))
            # Search for the most recently modified file
            if active_db_path is None or db_path.stat().st_mtime > active_db_path.stat().st_mtime:
                active_db_path = db_path
            # Add db to the list
            db_paths.append(db_path)
        return active_db_path, db_paths

    def rename_db(self, old_path: Path, new_path: Path):
        log.debug(f'Renaming {old_path} to {new_path}...')
        # Rename DB journal
        journal_path = old_path.with_suffix('.db-journal')
        if journal_path.is_file():
            journal_path.rename(new_path.with_suffix('.db-journal'))
        # Rename DB file
        old_path.rename(new_path)

    def remove_db(self, db_path: Path):
        log.debug(f'Removing {db_path}...')
        # Remove DB journal
        journal_path = db_path.with_suffix('.db-journal')
        if journal_path.is_file():
            journal_path.unlink()
        # Remove DB file
        db_path.unlink()


@dataclass
class SQLiteTrigger:
    name: str
    table: str
    body: str


class LocalStorage:
    def __init__(self, path: Path):
        self.path = path
        self.connection = None
        self.cursor = None
        self.modified = False

    def disconnect(self):
        if self.connection is None:
            return
        self.connection.close()
        self.cursor = None
        self.modified = False
        self.connection = None
        log.debug(f'[{self.path.name}]: Connection closed')

    def connect(self):
        self.disconnect()
        log.debug(f'[{self.path.name}]: Connecting...')
        self.connection = sqlite3.connect(self.path)
        try:
            self.cursor = self.connection.cursor()
            try:
                self.cursor.execute("SELECT * FROM LocalStorage")
            except sqlite3.OperationalError:
                log.debug(f'[{self.path.name}]: Creating new settings database...')
                self.cursor.execute("CREATE TABLE LocalStorage(key text primary key not null, value text not null)")
                data = [
                    ('NotFirstTimeOpenPush', '"___1B___"'),
                    ('HasLocalGameSettings', '"___1B___"'),
                    ('IsCustomImageQuality', '"___1B___"'),
                ]
                self.cursor.executemany(f"INSERT INTO LocalStorage VALUES (?,?)", data)
        except Exception as e:
            self.disconnect()
            raise Exception(L('error_local_storage_init_failed', 'Failed to initialize LocalStorage: {error_text}').format(error_text=e))

    def save(self):
        if not self.modified:
            self.disconnect()
            return
        self.connection.commit()
        self.disconnect()
        log.debug(f'[{self.path.name}]: File updated')

    def get_value(self, key) -> Union[str, None]:
        result = self.cursor.execute(f"SELECT value FROM LocalStorage WHERE key='{key}'")
        data = result.fetchone()
        if data is None or len(data) != 1:
            return None
        else:
            return data[0]

    def set_value(self, key: str, value: str):
        old_value = self.get_value(key)
        if value == old_value:
            log.debug(f'[{self.path.name}]: Skipped {key} value: {value} (already set)')
            return
        if old_value is None:
            self.cursor.execute(f"INSERT INTO LocalStorage VALUES ('{key}', '{value}')")
            log.debug(f'[{self.path.name}]: Added {key} value: {value}')
        else:
            self.cursor.execute(f"UPDATE LocalStorage SET value = '{value}' WHERE key='{key}'")
            log.debug(f'[{self.path.name}]: Updated {key} value: {old_value} -> {value}')
        self.modified = True

    def delete_value(self, key):
        if self.get_value(key) is None:
            return
        self.cursor.execute(f"DELETE FROM LocalStorage WHERE key='{key}'")
        log.debug(f'[{self.path.name}]: Removed {key} value')
        self.modified = True

    def get_trigger(self, name) -> Union[SQLiteTrigger, None]:
        result = self.cursor.execute(f"SELECT * FROM sqlite_master WHERE type='trigger' AND name='{name}'")
        data = result.fetchone()
        if data is None:
            return None
        else:
            return SQLiteTrigger(name=data[1], table=data[2], body=data[4])

    def get_all_triggers(self) -> Union[List[SQLiteTrigger], None]:
        result = self.cursor.execute(f"SELECT * FROM sqlite_master WHERE type='trigger'")
        data = result.fetchmany()
        if data is None:
            return None
        else:
            return [SQLiteTrigger(name=t[1], table=t[2], body=t[4]) for t in data]

    def set_value_lock_trigger(self, name, key, value):
        self.delete_trigger(name)
        self.cursor.execute(f'''
            CREATE TRIGGER {name}
            AFTER UPDATE OF value ON LocalStorage
            WHEN NEW.key = '{key}'
            BEGIN
                UPDATE LocalStorage
                SET value = {value}
                WHERE key = '{key}';
            END;
        ''')
        log.debug(f'[{self.path.name}]: Added lock trigger {name} for {key} value: {value}')
        self.modified = True

    def delete_trigger(self, name):
        if self.get_trigger(name) is None:
            return
        self.cursor.execute(f'DROP TRIGGER IF EXISTS {name}')
        log.debug(f'[{self.path.name}]: Removed trigger {name}')
        self.modified = True

