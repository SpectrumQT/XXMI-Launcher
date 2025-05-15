import re
import os
import json
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
import core.i18n_manager as I18n

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
            'r.Streaming.UsingNewKuroStreaming': 1,
        },
        '/Script/Engine.RendererRTXSettings': {
            'r.RayTracing': 0,
            'r.RayTracing.LimitDevice': 1,
            'r.RayTracing.EnableInGame': 0,
            'r.RayTracing.EnableOnDemand': 0,
            'r.RayTracing.EnableInEditor': 0,
        }
    })
    apply_perf_tweaks: bool = False
    unlock_fps: bool = False
    disable_wounded_fx: bool = False
    disable_wounded_fx_warned: bool = False
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
            return str(
                Version(Config.Importers.WWMI.Importer.importer_path / 'Core' / 'WWMI' / 'WuWa-Model-Importer.ini'))
        except Exception as e:
            return ''

    def normalize_game_path(self, game_path: Path) -> Path:
        if not game_path.is_absolute():
            raise ValueError(I18n._('errors.packages.model_importers.wwmi.path_not_absolute').format(game_path=game_path))

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

        raise ValueError(I18n._('errors.packages.model_importers.wwmi.exe_not_found').format(game_path_original=game_path_original))

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
        Events.Fire(Events.Application.StatusUpdate(status='Validating game path...'))
        game_path = super().validate_game_path(game_folder)
        game_path = self.normalize_game_path(game_path)
        # Make sure that game folder contains critical resources
        exe_path = game_path / 'Wuthering Waves.exe'
        if not exe_path.is_file():
            raise ValueError(I18n._('errors.packages.model_importers.wwmi.invalid_folder_structure'))
        else:
            common_folder = self.get_parent_directory(game_path, 'common')
            if common_folder is not None and common_folder.parent.name == 'steamapps':
                # Steam installation detected
                if game_path.parent.name != 'common':
                    # Invalid file structure, most likely caused by manual folder relocation
                    Events.Fire(Events.Application.ShowError(
                        modal=True,
                        confirm_text='Ok',
                        message=I18n._('messages.invalid_ww_installation').format(
                            game_path=game_path,
                            folder_name=game_path.name,
                            exe_name=exe_path.name,
                            common_folder=common_folder
                        )
                    ))
                    raise ValueError(I18n._('errors.packages.model_importers.wwmi.steam_repair_required'))
        for dir_name in ['Client', 'Engine']:
            if dir_name not in [x.name for x in game_path.iterdir() if x.is_dir()]:
                raise ValueError(I18n._('errors.packages.model_importers.wwmi.missing_folder').format(dir_name=dir_name))
        return game_path

    def validate_game_exe_path(self, game_path: Path) -> Path:
        game_exe_path = game_path / 'Client' / 'Binaries' / 'Win64' / 'Client-Win64-Shipping.exe'
        if not game_exe_path.is_file():
            raise ValueError(I18n._('errors.packages.model_importers.wwmi.executable_not_found').format(process_name=game_exe_path.name))
        return game_exe_path

    def get_start_cmd(self, game_path: Path) -> Tuple[Path, List[str], Optional[str]]:
        game_exe_path = self.validate_game_exe_path(game_path)
        return game_exe_path, ['Client', '-DisableModule=streamline', '-d3d11', '-dx11'], str(game_exe_path.parent)

    def initialize_game_launch(self, game_path: Path):
        # self.verify_plugins(game_path)
        # self.restore_streamline(game_path)
        # self.remove_streamline(game_path)
        if Config.Active.Importer.custom_launch_inject_mode != 'Bypass':
            self.update_engine_ini(game_path)
            self.update_game_user_settings_ini(game_path)
            self.update_wwmi_ini()
        self.configure_settings(game_path)

    def configure_settings(self, game_path: Path):
        if not any([Config.Importers.WWMI.Importer.configure_game, Config.Importers.WWMI.Importer.unlock_fps]):
            return

        Events.Fire(Events.Application.StatusUpdate(status=I18n._('status.configuring_in_game_settings')))

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

                # Set internal custom quality flag to True
                settings_manager.set_setting('IsCustomImageQuality', '"___1B___"')

                # Set "Image Quality" to "Quality" - required to force high quality textures mods are made for
                settings_manager.set_setting('ImageQuality', '3')

                # Force Ray Tracing Off as it doesn't work with DX11 aka WWMI
                settings_manager.set_setting('RayTracing', '0')
                settings_manager.set_setting('RayTracedReflection', '0')
                settings_manager.set_setting('RayTracedGI', '0')

                # Take care of Wounded Effect that 'breaks' modded textures if not handled properly
                if not Config.Importers.WWMI.Importer.disable_wounded_fx_warned:
                    if settings_manager.get_setting('SkinDamageMode') == '1':
                        user_dialogue = Events.Application.ShowWarning(
                            modal=True,
                            title=I18n._('messages.wounded_effect_title'),
                            confirm_text=I18n._('buttons.disable'),
                            cancel_text=I18n._('buttons.keep'),
                            message=I18n._('messages.wounded_effect_message'),
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
                raise Exception(I18n._('errors.packages.model_importers.wwmi.force_fps_failed').format(error=e))

            if Config.Importers.WWMI.Importer.configure_game:
                raise Exception(I18n._('errors.packages.model_importers.wwmi.configure_settings_failed').format(error=e))

    def update_engine_ini(self, game_path: Path):
        Events.Fire(Events.Application.StatusUpdate(status=I18n._('status.updating_engine_ini')))

        engine_ini_path = game_path / 'Client' / 'Saved' / 'Config' / 'WindowsNoEditor' / 'Engine.ini'

        if not engine_ini_path.exists():
            Paths.verify_path(engine_ini_path.parent)
            with open(engine_ini_path, 'w', encoding='utf-8') as f:
                f.write('')

        Events.Fire(Events.Application.VerifyFileAccess(path=engine_ini_path, write=True))
        with open(engine_ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(option_value_spacing=False, inline_comments=True, add_section_spacing=True), f)

        if '/Script/Engine.RendererRTXSettings' in Config.Active.Importer.engine_ini.keys():
            if ini.get_section('/Script/Engine.RendererRTXSettings') is not None:
                ini.remove_section('/Script/Engine.RendererRTXSettings')
            del Config.Active.Importer.engine_ini['/Script/Engine.RendererRTXSettings']

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

    def update_game_user_settings_ini(self, game_path: Path):
        if not Config.Importers.WWMI.Importer.unlock_fps:
            return

        Events.Fire(Events.Application.StatusUpdate(status=I18n._('status.updating_game_user_settings_ini')))

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

    def verify_plugins(self, game_path: Path):
        Events.Fire(Events.Application.StatusUpdate(status=I18n._('status.checking_engine_plugins')))

        plugins_path = game_path / 'Engine' / 'Plugins' / 'Runtime' / 'Nvidia'
        plugin_paths = [
            plugins_path / 'DLSS',
            plugins_path / 'Streamline_Old',
        ]

        for path in plugin_paths:
            path = path / 'Binaries' / 'ThirdParty' / 'Win64'
            if not path.is_dir() or len([x for x in path.iterdir() if x.suffix == '.dll']) == 0:
                Events.Fire(Events.Application.ShowWarning(
                    modal=True,
                    message=I18n._('errors.packages.model_importers.wwmi.installation_damaged')
                ))
                break

    def remove_streamline(self, game_path: Path):
        streamline_path = game_path / 'Engine' / 'Plugins' / 'Runtime' / 'Nvidia' / 'Streamline_Old'
        if not streamline_path.exists():
            return

        interposer_path = streamline_path / 'Binaries' / 'ThirdParty' / 'Win64' / 'sl.interposer.dll'

        if interposer_path.is_file():
            Events.Fire(Events.Application.StatusUpdate(status=I18n._('status.disabling_streamline_plugin')))
            plugin_backups_path = Paths.App.Backups / 'Plugins' / 'Streamline_Old'
            plugin_backups_path.mkdir(parents=True, exist_ok=True)
            self.move(interposer_path, plugin_backups_path / interposer_path.name)

    def restore_streamline(self, game_path: Path):
        interposer_backup_path = Paths.App.Backups / 'Plugins' / 'Streamline_Old' / 'sl.interposer.dll'
        if not interposer_backup_path.is_file():
            return
        Events.Fire(Events.Application.StatusUpdate(status=I18n._('status.restoring_streamline_plugin')))
        streamline_path = game_path / 'Engine' / 'Plugins' / 'Runtime' / 'Nvidia' / 'Streamline_Old'
        interposer_path = streamline_path / 'Binaries' / 'ThirdParty' / 'Win64' / 'sl.interposer.dll'
        if interposer_path.is_file():
            interposer_backup_path.unlink()
        else:
            self.move(interposer_backup_path, interposer_path)

    def update_wwmi_ini(self):
        Events.Fire(Events.Application.StatusUpdate(status=I18n._('status.updating_wwmi_ini')))

        wwmi_ini_path = Config.Importers.WWMI.Importer.importer_path / 'Core' / 'WWMI' / 'WuWa-Model-Importer.ini'
        if not wwmi_ini_path.exists():
            raise ValueError(I18n._('errors.packages.model_importers.wwmi.ini_not_found'))

        Events.Fire(Events.Application.VerifyFileAccess(path=wwmi_ini_path, write=True))
        with open(wwmi_ini_path, 'r', encoding='utf-8') as f:
            ini = IniHandler(IniHandlerSettings(option_value_spacing=True, ignore_comments=False), f)

        screen_width, screen_height = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
        ini.set_option('Constants', 'global $window_width', screen_width)
        ini.set_option('Constants', 'global $window_height', screen_height)

        if ini.is_modified():
            with open(wwmi_ini_path, 'w', encoding='utf-8') as f:
                f.write(ini.to_string())


class SettingsManager:
    def __init__(self, game_path: Path):
        self.path = game_path / 'Client' / 'Saved' / 'LocalStorage'
        self.db: Optional[LocalStorage] = None

    def __enter__(self):
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
            raise Exception(f'Failed to initialize LocalStorage: {e}')

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


class Version:
    def __init__(self, wwmi_ini_path):
        self.wwmi_ini_path = wwmi_ini_path
        self.version = None
        self.parse_version()

    def parse_version(self):
        with open(self.wwmi_ini_path, 'r', encoding='utf-8') as f:

            version_pattern = re.compile(r'^global \$version = (\d+)\.*(\d)(\d*)')

            for line in f.readlines():

                result = version_pattern.findall(line)

                if len(result) != 1:
                    continue

                result = list(result[0])

                if len(result) == 2:
                    result.append(0)

                if len(result) != 3:
                    raise ValueError(I18n._('errors.packages.model_importers.wwmi.malformed_version'))

                self.version = result

                return

        raise ValueError(I18n._('errors.packages.model_importers.wwmi.version_not_found'))

    def __str__(self) -> str:
        return f'{self.version[0]}.{self.version[1]}.{self.version[2]}'

    def as_float(self):
        return float(f'{self.version[0]}.{self.version[1]}{self.version[2]}')

    def as_ints(self):
        return [map(int, self.version)]
