import sys
import logging

from dataclasses import dataclass

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import Package, PackageMetadata

log = logging.getLogger(__name__)


@dataclass
class LauncherManagerConfig:
    auto_update: bool = True
    auto_close: bool = True
    theme_mode: str = 'System'
    active_importer: str = 'WWMI'
    config_path: str = 'XXMI Launcher Config.json'
    log_level: str = 'DEBUG'
    config_version: str = ''


@dataclass
class LauncherManagerEvents:

    @dataclass
    class Update:
        pass


class LauncherPackage(Package):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='Launcher',
            auto_load=True,
            github_repo_owner='SpectrumQT',
            github_repo_name='XXMI-Launcher',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='XXMI-LAUNCHER-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=True,
        ))
        installed_version = self.get_installed_version()
        if Config.Launcher.config_version < installed_version:
            Config.Config.upgrade(installed_version)

    def get_installed_version(self):
        if getattr(sys, 'frozen', False):
            return self.get_file_version(sys.executable, max_parts=3)
        else:
            return '0.0.0'

    def download_latest_version(self):
        # This package is supposed to be downloaded via Installer
        pass

    def install_latest_version(self, clean):
        Events.Fire(Events.PackageManager.InitializeInstallation())
        Events.Fire(Events.InstallerManager.UpdateLauncher())
