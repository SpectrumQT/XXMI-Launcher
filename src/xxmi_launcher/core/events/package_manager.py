from dataclasses import dataclass


@dataclass
class PackageState:
    installed_version: str
    deployed_version: str
    latest_version: str
    skipped_version: str


@dataclass
class PackageManagerEvents:

    @dataclass
    class NotifyPackageVersions:
        detect_installed: bool = True

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
        package_states: dict[str, PackageState]

    @dataclass
    class GetPackage:
        package_name: str