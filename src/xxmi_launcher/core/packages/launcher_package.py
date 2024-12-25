import shutil
import sys
import logging
import subprocess
import time
import winshell
import pythoncom
import winreg

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import Package, PackageMetadata

from core.utils.process_tracker import wait_for_process, WaitResult

log = logging.getLogger(__name__)


@dataclass
class LauncherManagerConfig:
    auto_update: bool = True
    update_channel: str = 'AUTO'
    auto_close: bool = True
    gui_theme: str = 'Default'
    theme_mode: str = 'System'
    active_importer: str = 'XXMI'
    enabled_importers: list = field(default_factory=lambda: [])
    log_level: str = 'DEBUG'
    config_version: str = ''


@dataclass
class LauncherManagerEvents:

    @dataclass
    class Update:
        pass

    @dataclass
    class CreateShortcut:
        pass


class LauncherPackage(Package):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='Launcher',
            auto_load=True,
            github_repo_owner='SpectrumQT',
            github_repo_name='XXMI-Launcher',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='XXMI-Launcher-Installer-Online-v%s.msi',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=True,
        ))
        self.subscribe(Events.LauncherManager.CreateShortcut, lambda event: self.create_shortcut())

        self.upgrade_installation()

    def get_installed_version(self):
        if '__compiled__' in globals() or getattr(sys, 'frozen', False):
            return self.get_file_version(sys.executable, max_parts=3)
        else:
            return '0.0.0'

    def get_last_installed_version(self):
        return self.get_installed_version()

    def install_latest_version(self, clean):
        Events.Fire(Events.PackageManager.InitializeInstallation())

        cmd = f'msiexec /i "{self.downloaded_asset_path}" /qr /norestart APPDIR="{Paths.App.Root}" CREATE_SHORTCUTS=""'
        log.debug(f'Calling `{cmd}`...')
        subprocess.Popen(cmd, shell=True)

        installer_process_name = 'EnhancedUI.exe'

        Events.Fire(Events.Application.StatusUpdate(status='Waiting for installer to start...'))

        result, pid = wait_for_process(installer_process_name, with_window=True, timeout=15)
        if result == WaitResult.Timeout:
            raise ValueError(f'Failed to start {self.downloaded_asset_path.name}!\n\n'
                             f'Was it blocked by Antivirus software or security settings?')

        time.sleep(1)

    def detect_update_channel(self):
        try:
            launcher_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\SpectrumQT\\XXMI Launcher', 0, winreg.KEY_READ)
        except FileNotFoundError:
            return 'ZIP'

        try:
            (path_value, regtype) = winreg.QueryValueEx(launcher_key, 'Path')
            if regtype != winreg.REG_SZ:
                return 'ZIP'
        except FileNotFoundError:
            return 'ZIP'

        if Path(path_value) != Paths.App.Root:
            return 'ZIP'

        return 'MSI'

    def update(self, clean=False):
        # Launcher releases come in 2 formats:
        # * .msi (installer) - updated via Windows Installer
        # * .zip (portable) - updated via custom exe (https://github.com/SpectrumQT/XXMI-Updater)
        if Config.Launcher.update_channel.upper() in ['MSI', 'ZIP']:
            # Use update channel override provided by user
            update_channel = Config.Launcher.update_channel.upper()
        else:
            # Autodetect installation format based (check for .msi registry record)
            update_channel = self.detect_update_channel()
        log.debug(f'Using {update_channel} update channel')

        if update_channel == 'MSI':
            # Use default package update method (targeted at .msi) and let Windows Installer do the heavy lifting
            super().update()
        else:
            # Use installer (updater) package (targeted at .zip)
            # If we're not relying on Windows Installer for self-update, we'll have to do the heavy lifting ourselves
            from core.packages.updater_package import UpdaterPackage
            self.manager.register_package(UpdaterPackage())
            Events.Fire(Events.UpdaterManager.UpdateLauncher())

    def upgrade_installation(self):
        # Grab old version info from config
        old_version = Config.Launcher.config_version

        # Grab new version info from exe
        new_version = self.get_installed_version()

        # Exit early if no version upgrade required
        if old_version == new_version:
            return

        # Upgrade existing config to the latest version
        Config.Config.upgrade(old_version, new_version)

        # Exit early if old version is empty (aka fresh installation)
        if not old_version:
            return

        # Cleanup existing pre-msi installation
        if old_version < '0.9.7':
            old_exe_path = Paths.App.Root / 'XXMI Launcher.exe'
            if old_exe_path.is_file():
                Events.Fire(Events.Application.StatusUpdate(status='Removing old files...'))
                # Remove pre-nuitka files and folders from `XXMI Launcher/Resources`
                for path in Paths.App.Resources.iterdir():
                    if path.name in ['Bin', 'Packages', 'Security']:
                        continue
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    time.sleep(0.01)
                # Remove pre-msi installer
                installer_path = Paths.App.Resources / 'Packages' / 'Installer'
                if installer_path.is_dir():
                    shutil.rmtree(installer_path)
                # Remove pre-nuitka exe
                old_exe_path.unlink()
                # Notify user about new exe path
                msg = ''
                msg += f'Launcher .exe file location was changed to:\n\n'
                msg += f'{Paths.App.Resources / "Bin" / "XXMI Launcher.exe"}\n\n'
                msg += f'Desktop shortcut was updated automatically. Sorry for bothering!'
                Events.Fire(Events.Application.ShowInfo(title='Update Notification', message=msg))

    def create_shortcut(self):
        pythoncom.CoInitialize()

        with winshell.shortcut(str(Path(winshell.desktop()) / f'XXMI Launcher.lnk')) as link:
            link.path = str(Path(sys.executable))
            link.description = f'Shortcut to XXMI Launcher'
            link.working_directory = str(Paths.App.Resources / 'Bin')
            link.icon_location = (str(Paths.App.Themes / 'Default' / 'window-icon.ico'), 0)

        with winshell.shortcut(str(Paths.App.Root / f'XXMI Launcher.lnk')) as link:
            link.path = str(Path(sys.executable))
            link.description = f'Shortcut to XXMI Launcher'
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
