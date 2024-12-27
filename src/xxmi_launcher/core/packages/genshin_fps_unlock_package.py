import logging
import re
import shutil
import subprocess
import json

from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import Package, PackageMetadata

from core.utils.dll_injector import DllInjector

log = logging.getLogger(__name__)


@dataclass
class MigotoManagerEvents:

    @dataclass
    class OpenModsFolder:
        pass


class GenshinFpsUnlockerPackage(Package):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='GI-FPS-Unlocker',
            auto_load=False,
            github_repo_owner='SpectrumQT',
            github_repo_name='GI-FPS-Unlocker-Package',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='GENSHIN-FPS-UNLOCK-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=False,
        ))

    def get_installed_version(self):
        try:
            with open(self.package_path / 'Manifest.json', 'r') as f:
                return json.load(f)['version']
        except Exception as e:
            return ''

    def install_latest_version(self, clean):
        Events.Fire(Events.PackageManager.InitializeInstallation())

        self.move_contents(self.downloaded_asset_path, self.package_path)

    def validate_package_files(self):
        pass
        # self.validate_files([self.package_path / f for f in ['3dmloader.dll', 'd3d11.dll', 'd3dcompiler_47.dll', 'nvapi64.dll']])

    def uninstall(self):
        log.debug(f'Uninstalling package {self.metadata.package_name}...')

        if self.package_path.is_dir():
            log.debug(f'Removing {self.package_path}...')
            shutil.rmtree(self.package_path)
