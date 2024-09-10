import os
import json

from pathlib import Path
from dataclasses import dataclass, field, fields
from typing import Union, Dict, Any

from dacite import from_dict

import core.path_manager as Paths
import core.event_manager as Events

from core.utils.security import Security
from core import package_manager
from core.packages import launcher_package
from core.packages.model_importers import wwmi_package
from core.packages.model_importers import zzmi_package


@dataclass
class ImportersConfig:
    WWMI: wwmi_package.WWMIPackageConfig = field(default_factory=lambda: wwmi_package.WWMIPackageConfig())
    ZZMI: zzmi_package.ZZMIPackageConfig = field(default_factory=lambda: zzmi_package.ZZMIPackageConfig())


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

    @property
    def Active(self) -> Union[wwmi_package.WWMIPackageConfig, zzmi_package.ZZMIPackageConfig]:
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
            with open(config_path, 'r') as f:
                cfg.update(json.load(f))
        for key, value in from_dict(data_class=AppConfig, data=cfg).__dict__.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def load(self):
        try:
            Config.from_json(Paths.App.Root / self.Launcher.config_path)

        except Exception as e:
            raise e
        finally:
            global Launcher
            Launcher = self.Launcher
            global Packages
            Packages = self.Packages
            global Importers
            Importers = self.Importers

    def save(self):
        cfg = Config.as_json()
        with open(Paths.App.Root / self.Launcher.config_path, 'w') as f:
            return f.write(cfg)


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
            Config.Active.Importer.run_post_load,
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

        if Config.Active.Importer.run_post_load:
            if not self.security.verify(Config.Active.Importer.run_post_load_signature, Config.Active.Importer.run_post_load.encode()):
                wrong_signatures['Run Post Load'] = Config.Active.Importer.run_post_load

        if len(wrong_signatures) > 0:
            msg = '\n'.join([f'{k}: "{v}"' for k, v in wrong_signatures.items()])
            user_requested_reset = Events.Call(Events.Application.ShowError(
                modal=True,
                lock_master=False,
                screen_center=True,
                confirm_text='Reset',
                cancel_text='Keep',
                message=f'Failed to validate unsecure settings!\n\n'
                        f'{msg}\n'
            ))
            if user_requested_reset:
                if 'Unsafe Mode' in wrong_signatures:
                    Config.Active.Migoto.unsafe_mode = False
                if 'Run Pre Launch' in wrong_signatures:
                    Config.Active.Importer.run_pre_launch = ''
                if 'Run Post Load' in wrong_signatures:
                    Config.Active.Importer.run_post_load = ''
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
        if Active.Importer.run_post_load:
            Active.Importer.run_post_load_signature = self.security.sign(Active.Importer.run_post_load.encode())
        if save_config:
            Config.save()


Config: AppConfig = AppConfig()
ConfigSecurity: AppConfigSecurity = AppConfigSecurity()

# Config aliases, intended to shorten dot names
Launcher: launcher_package.LauncherManagerConfig
Packages: package_manager.PackageManagerConfig
Importers: ImportersConfig
Active: Union[wwmi_package.WWMIPackageConfig, zzmi_package.ZZMIPackageConfig]


def get_resource_path(element):
    return Active.Importer.theme_path / element.get_resource_path()
