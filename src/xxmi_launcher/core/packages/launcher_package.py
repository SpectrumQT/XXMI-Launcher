import shutil
import sys
import logging
import subprocess
import os
import time
import winshell
import pythoncom

from dataclasses import dataclass, field
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import Package, PackageMetadata

from core.utils.process_tracker import wait_for_process, WaitResult

log = logging.getLogger(__name__)


@dataclass
class LauncherManagerConfig:
    auto_update: bool = True
    auto_close: bool = True
    theme_mode: str = 'System'
    active_importer: str = 'XXMI'
    enabled_importers: list = field(default_factory=lambda: [])
    log_level: str = 'DEBUG'
    config_version: str = ''

    @property
    def theme_path(self) -> Path:
        if self.active_importer == 'XXMI':
            return Paths.App.Themes / 'Default'
        else:
            return Paths.App.Themes / Config.Active.Importer.launcher_theme


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
        installed_version = self.get_installed_version()
        if Config.Launcher.config_version < installed_version:
            if Config.Launcher.config_version and Config.Launcher.config_version < '1.0.2':
                self.create_shortcut()
            Config.Config.upgrade(installed_version)
            self.cleanup_old_version()

    def get_installed_version(self):
        if getattr(sys, 'frozen', False):
            return self.get_file_version(sys.executable, max_parts=3)
        else:
            return '0.0.0'

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

    def cleanup_old_version(self):
        # Cleanup pre-0.9.7
        old_exe_path = Paths.App.Root / 'XXMI Launcher.exe'
        if old_exe_path.is_file():
            Events.Fire(Events.Application.StatusUpdate(status='Removing old files...'))
            # Remove pre-0.9.7 files and folders from `XXMI Launcher/Resources`
            for path in Paths.App.Resources.iterdir():
                if path.name in ['Bin', 'Packages', 'Security']:
                    continue
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                time.sleep(0.01)
            # Remove pre-0.9.7 Installer
            installer_path = Paths.App.Resources / 'Packages' / 'Installer'
            if installer_path.is_dir():
                shutil.rmtree(installer_path)
            # Remove pre-0.9.7 exe
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
