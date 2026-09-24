import winreg

from pathlib import Path

from core.platforms.app_locator import RegistryValuePath, AppInfo
from core.platforms.platform_locator import PlatformLocator


EPIC_APP_INFO = AppInfo(
    exe_names={
        "EpicGamesLauncher.exe",
    },
    display_names={
        "Epic Games Launcher",
    },
    known_paths={
        Path("C:/Program Files (x86)/Epic Games/Launcher/Portal/Binaries/Win64/EpicGamesLauncher.exe"),
    },
    known_registry_paths={
        RegistryValuePath(root=winreg.HKEY_CURRENT_USER, key=r"Software\Epic Games\EOS", value="ModSdkCommand"),
        RegistryValuePath(root=winreg.HKEY_LOCAL_MACHINE, key=r"SOFTWARE\WOW6432Node\EpicGames\Epic Games Updater", value="EpicGamesLauncherExecutable"),
    },
    expected_relative_paths={},
)


class EpicLocator(PlatformLocator):
    """
    Locate an Epic Games installation.
    """
    APP_INFO = EPIC_APP_INFO
