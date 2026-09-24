import logging

from pathlib import Path
from dataclasses import dataclass, field

import core.path_manager as Paths

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
    WWMI: wwmi_package.WWMIPackageConfig = field(default_factory=wwmi_package.WWMIPackageConfig)
    ZZMI: zzmi_package.ZZMIPackageConfig = field(default_factory=zzmi_package.ZZMIPackageConfig)
    EFMI: efmi_package.EFMIPackageConfig = field(default_factory=efmi_package.EFMIPackageConfig)
    SRMI: srmi_package.SRMIPackageConfig = field(default_factory=srmi_package.SRMIPackageConfig)
    GIMI: gimi_package.GIMIPackageConfig = field(default_factory=gimi_package.GIMIPackageConfig)
    HIMI: himi_package.HIMIPackageConfig = field(default_factory=himi_package.HIMIPackageConfig)


@dataclass
class SecurityConfig:
    user_signature: str = ''


@dataclass
class AppConfig:
    # Config fields
    Launcher: launcher_package.LauncherManagerConfig = field(default_factory=launcher_package.LauncherManagerConfig)
    Packages: package_manager.PackageManagerConfig = field(default_factory=package_manager.PackageManagerConfig)
    Importers: ImportersConfig = field(default_factory=ImportersConfig)
    Security: SecurityConfig = field(default_factory=SecurityConfig)

    # State fields
    Active: (
        gimi_package.GIMIPackageConfig | srmi_package.SRMIPackageConfig | zzmi_package.ZZMIPackageConfig
        | wwmi_package.WWMIPackageConfig | himi_package.HIMIPackageConfig | efmi_package.EFMIPackageConfig
        | None
    ) = field(init=False, default=None)

    active_theme: str | None = field(init=False, default=None)

    def __post_init__(self):
        self.active_theme = 'Default'

    @property
    def theme_path(self) -> Path:
        return Paths.App.Themes / self.active_theme
