import os
import logging
import json

from pathlib import Path
from dataclasses import dataclass, field, fields
from typing import Union, Dict, Any, Optional, List

from dacite import from_dict

import core.path_manager as Paths
import core.event_manager as Events

from core.locale_manager import L
from core.utils.security import Security
from core import package_manager
from core.packages import launcher_package
from core.packages.model_importers import gimi_package
from core.packages.model_importers import srmi_package
from core.packages.model_importers import wwmi_package
from core.packages.model_importers import zzmi_package
from core.packages.model_importers import himi_package
from core.packages.model_importers import efmi_package

log = logging.getLogger(__name__)


@dataclass
class ImportersConfig:
    WWMI: wwmi_package.WWMIPackageConfig = field(default_factory=lambda: wwmi_package.WWMIPackageConfig())
    ZZMI: zzmi_package.ZZMIPackageConfig = field(default_factory=lambda: zzmi_package.ZZMIPackageConfig())
    EFMI: efmi_package.EFMIPackageConfig = field(default_factory=lambda: efmi_package.EFMIPackageConfig())
    SRMI: srmi_package.SRMIPackageConfig = field(default_factory=lambda: srmi_package.SRMIPackageConfig())
    GIMI: gimi_package.GIMIPackageConfig = field(default_factory=lambda: gimi_package.GIMIPackageConfig())
    HIMI: himi_package.HIMIPackageConfig = field(default_factory=lambda: himi_package.HIMIPackageConfig())


@dataclass
class SecurityConfig:
    user_signature: str = ''


@dataclass
class AppConfig:
    # Config fields
    Launcher: launcher_package.LauncherManagerConfig = field(
        default_factory=lambda: launcher_package.LauncherManagerConfig()
    )
    Packages: package_manager.PackageManagerConfig = field(
        default_factory=lambda: package_manager.PackageManagerConfig()
    )
    Importers: ImportersConfig = field(
        default_factory=lambda: ImportersConfig()
    )
    Security: SecurityConfig = field(
        default_factory=lambda: SecurityConfig()
    )
    # State fields
    # Active: Optional[WWMIConfig] = field(init=False, default=None)

    active_theme: Optional[str] = field(init=False, default=None)

    def __post_init__(self):
        self.active_theme = 'Default'

    @property
    def theme_path(self) -> Path:
        return Paths.App.Themes / Config.active_theme

    @property
    def config_path(self):
        return Paths.App.Root / 'XXMI Launcher Config.json'

    @property
    def Active(self) -> Union[gimi_package.GIMIPackageConfig, srmi_package.SRMIPackageConfig,
                              zzmi_package.ZZMIPackageConfig, wwmi_package.WWMIPackageConfig,
                              himi_package.HIMIPackageConfig, efmi_package.EFMIPackageConfig]:
        global Active
        return Active

    def as_dict(self, obj: Any) -> Dict[str, Any]:
        result = {}

        if hasattr(obj, '__dataclass_fields__'):
            # Process dataclass object
            for obj_field in fields(obj):
                # Fields with 'init=False' contain app state data that isn't supposed to be saved
                if not obj_field.init:
                    continue
                # Recursively process nested dataclass
                value = getattr(obj, obj_field.name)

                if hasattr(value, '__dataclass_fields__') or isinstance(value, dict | list | tuple):
                    result[obj_field.name] = self.as_dict(value)
                else:
                    result[obj_field.name] = value

        elif isinstance(obj, dict):
            # Process dict object
            for obj_field, value in obj.items():
                if hasattr(value, '__dataclass_fields__') or isinstance(value, dict | list | tuple):
                    result[obj_field] = self.as_dict(value)
                else:
                    result[obj_field] = value

        elif isinstance(obj, list | tuple):
            # Process list or tuple object
            result = []
            for value in obj:
                if hasattr(value, '__dataclass_fields__') or isinstance(value, dict | list | tuple):
                    result.append(self.as_dict(value))
                else:
                    result.append(value)

        return result

    def as_json(self):
        cfg = self.as_dict(self)
        return json.dumps(cfg, indent=4)

    def from_json(self, config_path: Path):
        cfg = self.as_dict(self)
        if config_path.is_file():
            cfg.update(json.loads(Paths.App.read_text(config_path)))
        for key, value in from_dict(data_class=AppConfig, data=cfg).__dict__.items():
            if hasattr(self, key):
                setattr(self, key, value)
        if self.Launcher.gui_theme:
            self.active_theme = self.Launcher.gui_theme

    def load(self, cfg_path=None):
        try:
            Config.from_json(cfg_path or self.config_path)
        except Exception as e:
            log.exception(e)
            raise e
        finally:
            global Launcher
            Launcher = self.Launcher
            global Packages
            Packages = self.Packages
            global Importers
            Importers = self.Importers

    def save(self):
        Paths.App.write_file(self.config_path, Config.as_json())

    def run_patch_195(self):
        importer = self.Importers.__dict__['WWMI']
        try:
            if importer.Importer.texture_streaming_boost < 20 or importer.Importer.texture_streaming_boost == 30:
                importer.Importer.texture_streaming_boost = 20
        except:
            pass

    def run_patch_201(self):
        importer = self.Importers.__dict__['WWMI']
        try:
            importer.Importer.force_max_lod_bias = False
            importer.Importer.texture_streaming_use_all_mips = True
            importer.Importer.mesh_lod_distance_scale = 1.0
            importer.Importer.mesh_lod_distance_offset = -10
        except:
            pass

    def run_patch_216(self):
        try:
            importer = self.Importers.__dict__['WWMI']
            importer.Importer.game_exe_names = ['Client-Win64-Shipping.exe']
        except:
            pass
        try:
            importer = self.Importers.__dict__['ZZMI']
            importer.Importer.game_exe_names = ['ZenlessZoneZero.exe', 'ZenlessZoneZeroBeta.exe']
        except:
            pass

    def upgrade(self, old_version, new_version):
        # Save config to file and exit early if old version is empty (aka fresh installation)
        if not old_version:
            log.debug(f'Saving new config...')
            self.Launcher.config_version = new_version
            self.save()
            return

        # Apply patches
        patches = {
            '1.9.5': self.run_patch_195,
            '2.0.1': self.run_patch_201,
            '2.1.6': self.run_patch_216,
        }
        applied_patches = []
        for patch_version, patch_func in patches.items():
            if old_version < patch_version:
                log.debug(f'Upgrading launcher config from {old_version} to {patch_version}...')
                patch_func()
                applied_patches.append(patch_version)

        # Save patched config to file
        if len(applied_patches) > 0:
            log.debug(f'Saving patched config...')
            self.Launcher.config_version = new_version
            self.save()


class AppConfigSecurity:
    def __init__(self):
        self.security = None

    def load(self, save_config: bool = True):
        global Config

        self.security = Security()

        keys_path = Paths.App.Resources / 'Security'
        Paths.verify_path(keys_path)
        try:
            self.security.read_key_pair(Paths.App.Resources / keys_path)
        except Exception as e:
            pass

        if self.security.public_key is None or not self.security.verify(Config.Security.user_signature,
                                                                        os.getlogin().encode()):
            self.security.generate_key_pair()
            self.security.write_key_pair(keys_path)
            Config.Security.user_signature = self.security.sign(os.getlogin())
            if save_config:
                Config.save()

    def validate_config(self):
        global Config

        unsecure_settings = [
            Config.Active.Migoto.unsafe_mode,
            Config.Active.Importer.run_pre_launch,
            Config.Active.Importer.custom_launch,
            Config.Active.Importer.run_post_load,
            Config.Active.Importer.extra_libraries,
        ]

        if not any(unsecure_settings):
            return

        if self.security is None:
            self.load()

        wrong_signatures = {}

        if Config.Active.Migoto.unsafe_mode:
            if not self.security.verify(Config.Active.Migoto.unsafe_mode_signature, os.getlogin().encode()):
                wrong_signatures['Unsafe Mode'] = 'Enabled'

        if Config.Active.Importer.run_pre_launch:
            if not self.security.verify(Config.Active.Importer.run_pre_launch_signature, Config.Active.Importer.run_pre_launch.encode()):
                wrong_signatures['Run Pre Launch'] = Config.Active.Importer.run_pre_launch

        if Config.Active.Importer.custom_launch:
            if not self.security.verify(Config.Active.Importer.custom_launch_signature, Config.Active.Importer.custom_launch.encode()):
                wrong_signatures['Custom Launch'] = Config.Active.Importer.custom_launch

        if Config.Active.Importer.run_post_load:
            if not self.security.verify(Config.Active.Importer.run_post_load_signature, Config.Active.Importer.run_post_load.encode()):
                wrong_signatures['Run Post Load'] = Config.Active.Importer.run_post_load

        if Config.Active.Importer.extra_libraries:
            if not self.security.verify(Config.Active.Importer.extra_libraries_signature, Config.Active.Importer.extra_libraries.encode()):
                wrong_signatures['Extra Libraries'] = Config.Active.Importer.extra_libraries

        if len(wrong_signatures) > 0:
            msg = '\n'.join([f'{k}: "{v}"' for k, v in wrong_signatures.items()])
            user_requested_reset = Events.Call(Events.Application.ShowError(
                modal=True,
                confirm_text=L('message_button_reset_unsecure_setting', 'Reset'),
                cancel_text=L('message_button_keep_unsecure_setting', 'Keep'),
                message=L('message_text_unsecure_setting_validation_failed', """
                    Failed to validate unsecure settings!
                    
                    {msg}
                """).format(msg=msg)
            ))
            if user_requested_reset:
                if 'Unsafe Mode' in wrong_signatures:
                    Config.Active.Migoto.unsafe_mode = False
                if 'Run Pre Launch' in wrong_signatures:
                    Config.Active.Importer.run_pre_launch = ''
                if 'Custom Launch' in wrong_signatures:
                    Config.Active.Importer.custom_launch = ''
                if 'Run Post Load' in wrong_signatures:
                    Config.Active.Importer.run_post_load = ''
                if 'Extra Libraries' in wrong_signatures:
                    Config.Active.Importer.extra_libraries = ''
            else:
                self.sign_settings()

    def sign_settings(self, save_config: bool = True):
        global Active
        global Config
        if self.security is None:
            self.load(save_config=False)
        if Active.Migoto.unsafe_mode:
            Active.Migoto.unsafe_mode_signature = self.security.sign(os.getlogin().encode())
        if Active.Importer.run_pre_launch:
            Active.Importer.run_pre_launch_signature = self.security.sign(Active.Importer.run_pre_launch.encode())
        if Active.Importer.custom_launch:
            Active.Importer.custom_launch_signature = self.security.sign(Active.Importer.custom_launch.encode())
        if Active.Importer.run_post_load:
            Active.Importer.run_post_load_signature = self.security.sign(Active.Importer.run_post_load.encode())
        if Active.Importer.extra_libraries:
            Active.Importer.extra_libraries_signature = self.security.sign(Active.Importer.extra_libraries.encode())
        if save_config:
            Config.save()


Config: AppConfig = AppConfig()
ConfigSecurity: AppConfigSecurity = AppConfigSecurity()

# Config aliases, intended to shorten dot names
Launcher: launcher_package.LauncherManagerConfig
Packages: package_manager.PackageManagerConfig
Importers: ImportersConfig
Active: Union[gimi_package.GIMIPackageConfig, srmi_package.SRMIPackageConfig,
              wwmi_package.WWMIPackageConfig, zzmi_package.ZZMIPackageConfig,
              himi_package.HIMIPackageConfig, efmi_package.EFMIPackageConfig]


def get_resource_path(element, filename: Union[str, Path], extensions: Optional[Union[str, List[str]]] = None):
    filename = Path(filename)
    search_extensions = [filename.suffix]
    if extensions is not None:
        search_extensions += [ext for ext in list(extensions) if ext != filename.suffix]
    class_path = element.get_resource_path() / filename
    for extension in search_extensions:
        resource_path = Config.theme_path / class_path.with_suffix(extension)
        if resource_path.is_file():
            return resource_path
    resource_path = Paths.App.Themes / 'Default' / class_path
    if not resource_path.is_file():
        raise FileNotFoundError(L('error_theme_resource_not_found', """
            Resource not found:
            
            {resource_path}
            
            Hint: You can also use other extensions: {extensions}
        """).format(
            resource_path=resource_path,
            extensions = ", ".join(extensions or []))
        )
    return resource_path
