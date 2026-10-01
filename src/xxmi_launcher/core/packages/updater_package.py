import logging
import time

import core.path_manager as Paths
import core.event_manager as Events

from core.locale_manager import L
from core.package_manager import Package, PackageMetadata
from core.config.enums import StartMethod
from core.utils.process_manager import ProcessManager, LaunchContext, ExecutableLaunch

log = logging.getLogger(__name__)


class UpdaterPackage(Package):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='Updater',
            auto_load=True,
            github_repo_owner='SpectrumQT',
            github_repo_name='XXMI-Updater-Package',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='XXMI-UPDATER-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2}))\r?$',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=False,
        ))
        self.exe_path = self.package_path / 'XXMI Updater.exe'

        Events.Subscribe(Events.UpdaterManager.UpdateLauncher, self.update_launcher)

    def get_installed_version(self):
        if self.exe_path.exists():
            return self.get_file_version(self.exe_path, max_parts=3)
        else:
            return '0.0.0'

    def install_latest_version(self, clean):
        Events.Fire(Events.PackageManager.InitializeInstallation())

        self.move_contents(self.downloaded_asset_path, self.package_path)
        self.verify_files_integrity(self.package_path)

    def update_launcher(self, event: Events.UpdaterManager.UpdateLauncher):
        self.manager.update_package(self, force=True)

        Events.Fire(Events.PackageManager.InitializeInstallation())

        launch_context = LaunchContext(
            start_method=StartMethod.NATIVE,
            process_name=self.exe_path.name,
            target=ExecutableLaunch(
                exe_path=self.exe_path,
                cmd_args=f'--mode Updater --channel ZIP --dist_dir "{Paths.App.Root}" --src_dir "{event.downloaded_asset_path}"',
            ),
            work_dir=self.exe_path.parent,
        )

        manager = ProcessManager(launch_context)

        manager.start()

        Events.Fire(Events.Application.WaitForProcess(process_name=self.exe_path.name))

        window_found = manager.wait_until_running(
            timeout=15,
            wait_for_window=True
        )

        if not window_found:
            raise ValueError(L('error_updater_start_failed', """
                Failed to start XXMI Updater.exe!
                
                Was it blocked by Antivirus software or security settings?
            """))

        time.sleep(1)
