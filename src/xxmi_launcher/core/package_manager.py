import logging
import shutil
import time
import re
import zipfile
import os
import json

from dataclasses import dataclass, field, asdict
from typing import Union, List, Dict, Optional, Tuple
from pathlib import Path
from dacite import from_dict
from win32api import GetFileVersionInfo, HIWORD, LOWORD

import core.event_manager as Events
import core.path_manager as Paths
import core.config_manager as Config

from core.utils.security import Security
from core.utils.github_client import GitHubClient

log = logging.getLogger(__name__)


@dataclass
class PackageMetadata:
    package_name: str = ''
    auto_load: bool = False
    installation_path: str = ''
    requirements: List[str] = field(default_factory=lambda: [])
    github_repo_owner: str = ''
    github_repo_name: str = ''
    asset_version_pattern: str = ''
    asset_name_format: str = ''
    signature_pattern: str = ''
    signature_public_key: str = ''
    exit_after_update: bool = False
    deploy_name: str = ''


@dataclass
class PackageConfig:
    latest_version: str = ''
    skipped_version: str = ''
    deployed_version: str = ''
    update_check_time: int = 0
    latest_release_notes: str = ''
    deployed_release_notes: str = ''


@dataclass
class Manifest:
    version: str = ''
    signatures: Dict[str, str] = field(default_factory=lambda: {})

    def as_json(self):
        return json.dumps(asdict(self), indent=4)

    def from_json(self, file_path: Path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for key, value in from_dict(data_class=Manifest, data=json.load(f)).__dict__.items():
                if hasattr(self, key):
                    setattr(self, key, value)


class Package:
    def __init__(self, metadata: PackageMetadata):
        self.metadata = metadata
        self.cfg: Union[PackageConfig, None] = None
        self.asset_version_pattern = re.compile(self.metadata.asset_version_pattern)
        self.signature_pattern = re.compile(self.metadata.signature_pattern, re.MULTILINE)

        self.security = Security(public_key=self.metadata.signature_public_key)

        self.manager: Optional[PackageManager] = None
        self.active = False
        self.installed_version: str = ''
        self.state: PackageConfig
        self.download_url: str = ''
        self.signature: Union[str, None] = None
        self.manifest = None
        self.download_in_progress = False

        self.package_path = Paths.App.Resources / 'Packages' / self.metadata.package_name
        self.downloaded_asset_path: Union[Path, None] = None
        self.installed_asset_path: Union[Path, None] = None

    def get_installed_version(self) -> str:
        raise NotImplementedError(f'Method "get_installed_version" is not implemented for package {self.metadata.package_name}!')

    def detect_installed_version(self):
        try:
            self.installed_version = self.get_installed_version()
        except Exception as e:
            self.installed_version = ''
            raise ValueError(f'Failed to detect installed {self.metadata.package_name} version:\n\n{e}') from e

    def get_latest_version(self) -> Tuple[str, str, Union[str, None], str]:
        version, url, signature, release_notes = self.manager.github_client.fetch_latest_release(
            repo_owner=self.metadata.github_repo_owner,
            repo_name=self.metadata.github_repo_name,
            asset_version_pattern=self.asset_version_pattern,
            asset_name_format=self.metadata.asset_name_format,
            signature_pattern=self.signature_pattern)
        return version, url, signature, release_notes

    def detect_latest_version(self):
        try:
            self.cfg.latest_version, self.download_url, self.signature, self.cfg.latest_release_notes = self.get_latest_version()
        except ConnectionRefusedError as e:
            raise e
        except Exception as e:
            self.cfg.latest_version, self.download_url, self.signature, self.cfg.latest_release_notes = '', '', '', ''
            raise ValueError(f'Failed to detect latest {self.metadata.package_name} version:\n\n{e}') from e

    def update_available(self):
        return self.cfg.latest_version != '' and self.cfg.latest_version != self.get_installed_version()

    def download_latest_version_data(self):
        Events.Fire(Events.PackageManager.InitializeDownload())

        asset_file_name = self.metadata.asset_name_format % self.cfg.latest_version

        data = self.manager.github_client.download_data(
            self.download_url,
            block_size=128*1024,
            update_progress_callback=self.notify_download_progress
        )
        self.download_in_progress = False

        return asset_file_name, data

    def notify_download_progress(self, downloaded_bytes, total_bytes):
        if not self.download_in_progress:
            Events.Fire(Events.PackageManager.StartDownload(
                asset_name=self.metadata.asset_name_format % self.cfg.latest_version
            ))
            self.download_in_progress = True

        Events.Fire(Events.PackageManager.UpdateDownloadProgress(
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
        ))

    def save_downloaded_data(self, asset_path: Path, data):

        Events.Fire(Events.PackageManager.StartIntegrityVerification(asset_name='downloaded data'))

        if not self.security.verify(self.signature, data):
            raise ValueError(f'Downloaded data integrity verification failed!\n'
                             'Please restart the launcher and try again!')

        Events.Fire(Events.PackageManager.StartFileWrite(asset_name=asset_path.name))

        with open(asset_path, 'wb') as f:
            f.write(data)

        Events.Fire(Events.PackageManager.StartIntegrityVerification(asset_name=asset_path.name))

        with open(asset_path, 'rb') as f:
            if not self.security.verify(self.signature, f.read()):
                raise ValueError(f'{asset_path.name} data integrity verification failed!\n'
                                 'Please restart the launcher and try again!')

        return asset_path

    def download_latest_version(self):
        self.downloaded_asset_path = None

        asset_file_name, data = self.download_latest_version_data()

        Events.Fire(Events.Application.Busy())

        tmp_path = self.package_path / 'TMP'
        shutil.rmtree(tmp_path, ignore_errors=True)
        Paths.verify_path(tmp_path)

        if asset_file_name.endswith('.zip') or asset_file_name.endswith('.msi'):
            asset_path = tmp_path / asset_file_name
        elif asset_file_name.endswith('.exe'):
            asset_path = tmp_path / self.metadata.deploy_name

        self.save_downloaded_data(asset_path, data)

        if asset_path.suffix == '.zip':
            self.unpack(asset_path, tmp_path / self.metadata.deploy_name)
            self.downloaded_asset_path = tmp_path
        elif asset_path.suffix == '.exe' or asset_path.suffix == '.msi':
            self.downloaded_asset_path = asset_path

        manifest_path = tmp_path / f'Manifest.json'
        if not manifest_path.is_file():
            self.write_manifest(asset_path, self.cfg.latest_version, self.signature)
        else:
            self.move(manifest_path, self.package_path / manifest_path.name)

    def install_latest_version(self, clean):
        raise NotImplementedError(f'Method "install_latest_version" is not implemented for package {self.metadata.package_name}!')

    def write_manifest(self, asset_path, version, signature):
        manifest = Manifest(
            version=str(version),
            signatures={asset_path.name: signature},
        )
        with open(self.package_path / f'Manifest.json', 'w', encoding='utf-8') as f:
            f.write(manifest.as_json())

    def load_manifest(self):
        manifest = Manifest()
        manifest_path = self.package_path / 'Manifest.json'
        if not manifest_path.exists():
            raise ValueError(f'{self.metadata.package_name} package is missing manifest file!\n')
        try:
            manifest.from_json(manifest_path)
        except Exception as e:
            raise ValueError(f'Failed to parse {self.metadata.package_name} manifest file!\n') from e
        self.manifest = manifest

    def verify_signature(self, file_path: Path):
        if self.manifest is None:
            self.load_manifest()
        if not file_path.exists():
            raise ValueError(f'{self.metadata.package_name} package is missing critical file: {file_path.name}!\n')
        with open(file_path, 'rb') as f:
            if self.security.verify(self.get_signature(file_path), f.read()):
                return True
            else:
                raise ValueError(f'File {file_path.name} signature is invalid!')

    def get_signature(self, file_path: Path):
        if self.manifest is None:
            self.load_manifest()
        signature = self.manifest.signatures.get(file_path.name, None)
        if signature is None:
            raise ValueError(f'{self.metadata.package_name} manifest file is missing signature for {file_path.name}!\n')
        return signature

    def validate_files(self, file_paths: List[Path]):
        for file_path in file_paths:
            self.verify_signature(file_path)

    def unpack(self, file_path: Path, destination_path: Path):
        Events.Fire(Events.PackageManager.StartUnpack(asset_name=file_path.name))

        with zipfile.ZipFile(file_path, 'r') as zip:
            # Extract zip archive
            zip.extractall(destination_path)
            # Restore modification dates
            for zip_info in zip.infolist():
                extracted_file_path = os.path.join(destination_path, zip_info.filename)
                timestamp = time.mktime(zip_info.date_time + (0, 0, -1))
                os.utime(extracted_file_path, (timestamp, timestamp))

        file_path.unlink()

    def move(self, source_path: Path, destination_path: Path):
        Events.Fire(Events.PackageManager.StartFileMove(asset_name=source_path.name))
        if destination_path.exists():
            time.sleep(0.001)
            destination_path.unlink()
        time.sleep(0.001)
        shutil.move(source_path, destination_path)

    def move_contents(self, source_path: Path, destination_path: Path):
        Paths.verify_path(destination_path)
        for src_path in list(source_path.iterdir()):
            if src_path.is_file():
                self.move(src_path, destination_path / src_path.name)
            else:
                self.move_contents(src_path, destination_path / src_path.name)
        time.sleep(0.001)
        shutil.rmtree(source_path)

    def get_file_version(self, file_path, max_parts=4):
        version_info = GetFileVersionInfo(str(file_path), "\\")

        ms_file_version = version_info['FileVersionMS']
        ls_file_version = version_info['FileVersionLS']

        version = [str(HIWORD(ms_file_version)), str(LOWORD(ms_file_version)),
                   str(HIWORD(ls_file_version)), str(LOWORD(ls_file_version))]

        return '.'.join(version[:max_parts])

    def update(self, clean=False):
        if not self.download_url:
            self.detect_latest_version()

        try:
            self.download_latest_version()
        except Exception as e:
            raise Exception(f'Failed to download {self.cfg.latest_version} update for {self.metadata.package_name} package:\n{e}')

        try:
            self.install_latest_version(clean=clean)
        except Exception as e:
            manifest_path = self.package_path / f'Manifest.json'
            if manifest_path.is_file():
                manifest_path.unlink()
            raise Exception(f'Failed to install {self.cfg.latest_version} update for {self.metadata.package_name} package!\n'
                            f'Please restart the launcher or your PC and try again.\n\n'
                            f'{e}')

        self.load_manifest()
        self.detect_installed_version()
        self.cfg.deployed_version = self.installed_version
        self.cfg.deployed_release_notes = self.cfg.latest_release_notes

    def subscribe(self, event, callback):
        Events.Subscribe(event, callback, caller_id=self)

    def unsubscribe(self, callback_id=None, event=None, callback=None):
        Events.Unsubscribe(callback_id=callback_id, event=event, callback=callback, caller_id=self)

    def load(self):
        self.active = True
        log.debug(f'Loaded package: {self.metadata.package_name}')

    def unload(self):
        self.active = False
        log.debug(f'Unloaded package: {self.metadata.package_name}')

    def uninstall(self):
        pass


@dataclass
class PackageState:
    installed_version: str
    latest_version: str
    skipped_version: str


@dataclass
class PackageManagerConfig:
    packages: Dict[str, PackageConfig] = field(default_factory=lambda: {})


@dataclass
class PackageManagerEvents:

    @dataclass
    class StartCheckUpdate:
        pass

    @dataclass
    class InitializeDownload:
        pass

    @dataclass
    class StartDownload:
        asset_name: str

    @dataclass
    class UpdateDownloadProgress:
        downloaded_bytes: int
        total_bytes: int

    @dataclass
    class StartIntegrityVerification:
        asset_name: str

    @dataclass
    class InitializeInstallation:
        pass

    @dataclass
    class StartFileWrite:
        asset_name: str

    @dataclass
    class StartFileMove:
        asset_name: str

    @dataclass
    class StartUnpack:
        asset_name: str

    @dataclass
    class VersionNotification:
        auto_update: bool
        package_states: Dict[str, PackageState]

    @dataclass
    class GetPackage:
        package_name: str


class PackageManager:
    def __init__(self, packages: Optional[List[Package]] = None):
        self.github_client = GitHubClient()
        self.packages: Dict[str, Package] = {}
        if packages is not None:
            for package in packages:
                self.register_package(package)
        self.update_running = False
        self.api_connection_refused = False
        self.api_connection_refused_notified = False
        Events.Subscribe(Events.PackageManager.GetPackage, lambda event: self.get_package(event.package_name))
        Events.Subscribe(Events.Application.ConfigUpdate, self.handle_config_update)

    def handle_config_update(self, event):
        self.github_client.configure(
            access_token=Config.Launcher.github_token,
            verify_ssl=Config.Launcher.verify_ssl,
            proxy_config=Config.Launcher.proxy
        )

    def register_package(self, package: Package):
        self.packages[package.metadata.package_name] = package

        package.manager = self

        if package.metadata.package_name not in Config.Packages.packages:
            Config.Packages.packages[package.metadata.package_name] = PackageConfig()
        package.cfg = Config.Packages.packages[package.metadata.package_name]

        if package.metadata.auto_load:
            self.load_package(package)

    def load_package(self, package: Union[Package, str]):
        package = self.get_package(package)
        # Load required packages
        for required_package in package.metadata.requirements:
            self.load_package(required_package)
        # Mark package as active
        package.load()
        # Detect installed version to do a basic integrity check
        package.detect_installed_version()
        # Mark installed version as deployed on empty deployed version record
        if not package.cfg.deployed_version:
            package.cfg.deployed_version = package.installed_version

    def unload_package(self, package: Union[Package, str]):
        package = self.get_package(package)
        package.unload()
        for required_package in package.metadata.requirements:
            self.unload_package(required_package)

    def get_package(self, package: Union[Package, str]) -> Package:
        if isinstance(package, str):
            return self.packages[package]
        else:
            return package

    def get_version_notification(self) -> PackageManagerEvents.VersionNotification:
        return PackageManagerEvents.VersionNotification(
            auto_update=Config.Launcher.auto_update,
            package_states={
                package.metadata.package_name: PackageState(
                    installed_version=package.installed_version,
                    latest_version=package.cfg.latest_version,
                    skipped_version=package.cfg.skipped_version,
                ) for package in self.packages.values() if package.active
            },
        )

    def detect_package_versions(self):
        for package_name, package in self.packages.items():
            if package.active:
                package.detect_installed_version()

    def notify_package_versions(self, detect_installed: bool = False):
        if detect_installed:
            self.detect_package_versions()
        Events.Fire(self.get_version_notification())

    def update_available(self):
        for package in self.packages.values():
            if not package.active:
                continue
            if package.update_available():
                log.debug(f'Package {package.metadata.package_name} update available {package.installed_version} -> {package.cfg.latest_version}')
                return True

    def update_packages(self, no_install=False, no_check=False, force=False, reinstall=False, packages=None, silent=False):
        log.debug(f'Initializing packages update (no_install={no_install}, no_check={no_check}, force={force}, reinstall={reinstall}, silent={silent}, packages={packages})...')

        if self.update_running:
            log.debug(f'Packages update canceled: update is already in progress!')
            return
        self.update_running = True
        self.api_connection_refused = False

        if not silent:
            Events.Fire(Events.Application.Busy())
            Events.Fire(Events.PackageManager.StartCheckUpdate())

        requirements = []
        if packages:
            for package_name in packages:
                package = self.packages[package_name]
                requirements += package.metadata.requirements

        try:
            for package_name, package in self.packages.items():

                # Skip package processing if it's not active, intended for multiple model importers support
                if not package.active:
                    continue

                # Skip package processing if it's name isn't listed in provided package list
                if (packages is not None) and (package_name not in packages) and (package_name not in requirements):
                    continue

                # Download and install the latest package version, it can take a while
                updated = self.update_package(package, no_install=no_install, no_check=no_check, force=force, reinstall=reinstall)

                if no_install:
                    continue

                if package.metadata.exit_after_update and updated:
                    Events.Fire(Events.Application.Close(delay=500))
                    return

            if self.api_connection_refused and not self.api_connection_refused_notified:
                if not silent:
                    self.api_connection_refused_notified = True
                raise ConnectionRefusedError(f'Unauthorized GitHub API requests limit reached for your IP!\n\n'
                                             f'GitHub servers will ignore further connection attempts for an hour.\n\n'
                                             f'Set (another) *Proxy* or *GitHub Token* in *Launcher Settings* for instant access.')

        except Exception as e:
            if silent:
                log.exception(e)
            else:
                raise e

        finally:
            self.update_running = False
            self.notify_package_versions()
            if not silent:
                Events.Fire(Events.Application.Ready())

    def update_package(self, package: Package, no_install=False, no_check=False, force=False, reinstall=False):
        # Check if installation is pending, as we'll need download url from update check
        install = not no_install and (package.update_available() or reinstall) and (Config.Launcher.auto_update or force)

        # Check local files for the installed package version
        package.detect_installed_version()

        # Query GitHub for the latest available package version
        current_time = int(time.time())
        # Force update check if installation is pending or the last check time is somewhere in the future
        force_check = not no_check and (force or install or package.cfg.update_check_time > current_time)
        # We're going to throttle query to 1 per hour by default, else user can be temporary banned by GitHub
        if force_check or package.cfg.update_check_time + 3600 < current_time:
            package.cfg.update_check_time = current_time
            if self.api_connection_refused:
                self.api_connection_refused_notified = False
                return False
            try:
                package.detect_latest_version()
            except ConnectionRefusedError as e:
                self.api_connection_refused = True
                self.api_connection_refused_notified = False
                log.exception(e)
                return False

        # Check if installation is pending again, as update check may find new version
        install = not no_install and (package.update_available() or reinstall) and (Config.Launcher.auto_update or force)

        # Download and install the latest package version, it can take a while
        if install:
            package.update(clean=reinstall)
            return True

        return False

    def skip_latest_updates(self):
        for package in self.packages.values():
            package.cfg.skipped_version = package.cfg.latest_version

    def uninstall_packages(self):
        for package_name, package in self.packages.items():
            package.uninstall()