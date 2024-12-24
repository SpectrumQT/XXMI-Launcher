import logging
import subprocess
import time

from dataclasses import dataclass
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
from core.config_manager import Config as Config

from core.package_manager import Package, PackageMetadata

from core.utils.process_tracker import wait_for_process, WaitResult

log = logging.getLogger(__name__)


@dataclass
class InstallerManagerEvents:

    @dataclass
    class UpdateLauncher:
        pass


class InstallerPackage(Package):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='Installer',
            auto_load=True,
            github_repo_owner='SpectrumQT',
            github_repo_name='XXMI-Installer',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='XXMI-Installer-v%s.exe',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=False,
            deploy_name='XXMI-Installer.exe',
        ))
        self.exe_path = self.package_path / self.metadata.deploy_name

        Events.Subscribe(Events.InstallerManager.UpdateLauncher, lambda event: self.update_launcher())

    def get_installed_version(self):
        if self.exe_path.exists():
            return self.get_file_version(self.exe_path, max_parts=3)
        else:
            return '0.0.0'

    def install_latest_version(self, clean):
        Events.Fire(Events.PackageManager.InitializeInstallation())
        self.move(self.downloaded_asset_path, self.exe_path)

    def update_launcher(self):
        self.manager.update_package(self, force=True)

        try:
            self.validate_files([self.exe_path])
        except Exception:
            self.manager.update_package(self, force=True, reinstall=True)

        Events.Fire(Events.PackageManager.InitializeInstallation())

        subprocess.Popen([self.exe_path, '--mode', 'Updater', '--channel', 'ZIP', '--dist_dir', str(Paths.App.Root)])

        Events.Fire(Events.Application.WaitForProcess(process_name=self.exe_path.name))

        result, pid = wait_for_process(self.exe_path.name, with_window=True, timeout=15)
        if result == WaitResult.Timeout:
            raise ValueError('Failed to start XXMI-Installer.exe in update mode!\n\n'
                             'Was it blocked by Antivirus software or security settings?')

        time.sleep(1)
