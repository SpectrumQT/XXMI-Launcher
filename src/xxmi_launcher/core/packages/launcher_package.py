import sys
import logging
import subprocess
import time
import re
import winshell
import pythoncom
import winreg

from dataclasses import dataclass, field
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.locale_manager import L
from core.package_manager import Package, PackageMetadata

from core.config.enums import UpdateChannel
from core.utils.proxy import ProxyConfig
from core.config.enums import StartMethod
from core.utils.process_manager import ProcessManager, LaunchContext, CommandLaunch

log = logging.getLogger(__name__)


@dataclass
class LauncherManagerConfig:
    auto_update: bool = True
    pre_release: bool = False
    update_channel: UpdateChannel = UpdateChannel.AUTO
    auto_close: bool = True
    start_timeout: int = 30
    gui_theme: str = 'Default'
    theme_mode: str = 'System'
    active_importer: str = 'XXMI'
    enabled_importers: list = field(default_factory=lambda: [])
    log_level: str = 'DEBUG'
    config_version: str = ''
    theme_dev_mode: bool = False
    github_token: str = ''
    verify_ssl: bool = True
    proxy: ProxyConfig = field(default_factory=lambda: ProxyConfig())
    credits_shown: bool = False
    locale: str = ''


class LauncherPackage(Package):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='Launcher',
            auto_load=True,
            github_repo_owner='SpectrumQT',
            github_repo_name='XXMI-Launcher',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='XXMI-Launcher-Installer-Online-v%s.msi',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2}))\r?$',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=True,
        ))
        self.subscribe(Events.LauncherManager.CreateShortcut, lambda event: self.create_shortcut())

        # Launcher releases come in 2 formats:
        # * .msi (installer) - updated via Windows Installer
        # * .zip (portable) - updated via custom exe (https://github.com/SpectrumQT/XXMI-Updater)
        self._auto_update_channel: UpdateChannel = self.detect_update_channel()

        self.upgrade_installation()

    def get_installed_version(self) -> str:
        if '__compiled__' in globals() or getattr(sys, 'frozen', False):
            return self.get_file_version(sys.executable, max_parts=3)
        else:
            return '0.0.0'

    def get_last_installed_version(self):
        return self.get_installed_version()

    def update_available(self) -> bool:
        installed_version = self.get_installed_version()
        if installed_version == "0.0.0":
            return False
        return self.cfg.latest_version != "" and self.cfg.latest_version > installed_version

    def install_latest_version(self, clean):
        Events.Fire(Events.PackageManager.InitializeInstallation())

        if self.get_update_channel() == UpdateChannel.MSI:
            # Run MSI and let Windows Installer do the heavy lifting
            self.run_msi_installer()
        else:
            # Use installer (updater) package (targeted at .zip)
            # If we're not relying on Windows Installer for self-update, we'll have to do the heavy lifting ourselves
            from core.packages.updater_package import UpdaterPackage
            self.manager.register_package(UpdaterPackage())
            Events.Fire(Events.UpdaterManager.UpdateLauncher(downloaded_asset_path=self.downloaded_asset_path))

    def run_msi_installer(self):
        cmd = f'msiexec /i "{self.downloaded_asset_path}" /qr /norestart APPDIR="{Paths.App.Root}" CREATE_SHORTCUTS=""'

        launch_context = LaunchContext(
            start_method=StartMethod.NATIVE,
            target=CommandLaunch(
                cmd=cmd,
                process_name="EnhancedUI.exe",
            ),
        )

        manager = ProcessManager(launch_context)

        manager.start()

        Events.Fire(Events.Application.StatusUpdate(status=L('status_waiting_installer', 'Waiting for installer to start...')))

        window_found = manager.wait_until_running(
            timeout=15,
            wait_for_window=True
        )

        if not window_found:
            raise ValueError(L('error_launcher_installer_start_failed', """
                Failed to start {asset_name}!
                
                Was it blocked by Antivirus software or security settings?
            """).format(asset_name=self.downloaded_asset_path.name))

        time.sleep(1)

    def detect_update_channel(self) -> UpdateChannel:
        try:
            launcher_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\SpectrumQT\\XXMI Launcher', 0, winreg.KEY_READ)
        except FileNotFoundError:
            return UpdateChannel.ZIP

        try:
            (path_value, regtype) = winreg.QueryValueEx(launcher_key, 'Path')
            if regtype != winreg.REG_SZ:
                return UpdateChannel.ZIP
        except FileNotFoundError:
            return UpdateChannel.ZIP

        if Path(path_value) != Paths.App.Root:
            return UpdateChannel.ZIP

        return UpdateChannel.MSI

    def get_update_channel(self) -> UpdateChannel:
        if Config.Launcher.update_channel == UpdateChannel.AUTO:
            # Use automatically detected channel.
            return self._auto_update_channel
        else:
            return Config.Launcher.update_channel

    def detect_latest_version(self):
        # Download .msi or .zip using default package update method.
        # Deployment is handled by install_latest_version above.
        update_channel = self.get_update_channel()
        if update_channel == UpdateChannel.MSI:
            self.metadata.asset_name_format = "XXMI-Launcher-Installer-Online-v%s.msi"
            self.metadata.signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2}))\r?$'
        else:
            self.metadata.asset_name_format = "XXMI-Launcher-Portable-v%s.zip"
            self.metadata.signature_pattern=r'^## Signature Extra[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2}))\r?$'
        self.signature_pattern = re.compile(self.metadata.signature_pattern, re.MULTILINE)

        log.debug(f'Using {update_channel} update channel')

        super().detect_latest_version()

    def upgrade_installation(self):
        # Grab new version info from exe
        new_version = self.get_installed_version()

        if new_version == "0.0.0":
            return

        # Upgrade existing config to the latest version
        Config.Manager.migrate(new_version)

    def create_shortcut(self):
        pythoncom.CoInitialize()

        with winshell.shortcut(str(Path(winshell.desktop()) / f'XXMI Launcher.lnk')) as link:
            link.path = str(Path(sys.executable))
            link.description = L('launcher_shortcut_description', 'Shortcut to XXMI Launcher')
            link.working_directory = str(Paths.App.Resources / 'Bin')
            link.icon_location = (str(Paths.App.Themes / 'Default' / 'window-icon.ico'), 0)

        with winshell.shortcut(str(Paths.App.Root / f'XXMI Launcher.lnk')) as link:
            link.path = str(Path(sys.executable))
            link.description = L('launcher_shortcut_description', 'Shortcut to XXMI Launcher')
            link.working_directory = str(Paths.App.Resources / 'Bin')
            link.icon_location = (str(Paths.App.Themes / 'Default' / 'window-icon.ico'), 0)

    def uninstall(self):
        log.debug(f'Uninstalling package {self.metadata.package_name}...')

        shortcut_path = Path(winshell.desktop()) / f'XXMI Launcher.lnk'
        if shortcut_path.is_file():
            log.debug(f'Removing {shortcut_path}...')
            shortcut_path.unlink()

        shortcut_path = Paths.App.Root / f'XXMI Launcher.lnk'
        if shortcut_path.is_file():
            log.debug(f'Removing {shortcut_path}...')
            shortcut_path.unlink()
