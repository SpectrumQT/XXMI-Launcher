import winreg

from pathlib import Path
from typing import Any
from dataclasses import dataclass

from core.platforms.app_locator import RegistryValuePath, AppInfo
from core.platforms.platform_locator import PlatformLocator
from core.platforms.steam.vdf_file import VdfFile


STEAM_APP_INFO = AppInfo(
    exe_names={
        "steam.exe",
    },
    display_names={
        "Steam",
    },
    known_paths={
        Path("C:/Program Files (x86)/Epic Games/Launcher/Portal/Binaries/Win64/EpicGamesLauncher.exe"),
    },
    known_registry_paths={
        RegistryValuePath(root=winreg.HKEY_CURRENT_USER, key=r"Software\Valve\Steam", value="SteamExe"),
        RegistryValuePath(root=winreg.HKEY_CURRENT_USER, key=r"Software\Valve\Steam", value="SteamPath"),
        RegistryValuePath(root=winreg.HKEY_LOCAL_MACHINE, key=r"SOFTWARE\Valve\Steam", value="InstallPath"),
        RegistryValuePath(root=winreg.HKEY_LOCAL_MACHINE, key=r"SOFTWARE\WOW6432Node\Valve\Steam", value="InstallPath"),
    },
    expected_relative_paths={},
)


@dataclass(frozen=True)
class SteamUser:
    """
    A Steam user account.

    steam_id64:
        Steam's 64-bit identifier.

    account_id:
        The 32-bit Steam3/account ID used by the userdata directory.
    """

    steam_id64: int
    account_id: int
    account_name: str
    timestamp: int
    auto_login: bool


class SteamLocator(PlatformLocator):
    """
    Locate a Steam installation and its user-specific configuration.
    """
    APP_INFO = STEAM_APP_INFO

    def find_loginusers(self) -> Path | None:
        """
        Find Steam's loginusers.vdf file.
        """
        exe_path = self.find_executable()

        if exe_path is None:
            return None

        path = exe_path.parent / "config" / "loginusers.vdf"

        if path.is_file():
            return path

        return None

    def find_active_user(self) -> SteamUser | None:
        """
        Find the currently selected Steam account.

        Resolution order:
            1. Most recent Timestamp
            2. Single known account

        Returns:
            The active Steam user, or None if it cannot be determined.
        """
        loginusers = self.find_loginusers()

        if loginusers is None:
            return None

        data = VdfFile(loginusers).load()

        users = data.get("users")

        if not isinstance(users, dict):
            return None

        accounts = self._parse_users(users)

        if not accounts:
            return None

        # If there is only one account, there is no ambiguity.
        if len(accounts) == 1:
            return accounts[0]

        # Fall back to the most recent login timestamp.
        return max(
            accounts,
            key=lambda user: user.timestamp,
        )

    def find_userdata(self) -> Path | None:
        """
        Find Steam's userdata directory.
        """
        exe_path = self.find_executable()

        if exe_path is None:
            return None

        path = exe_path.parent / "userdata"

        if path.is_dir():
            return path

        return None

    def find_user_directory(self) -> Path | None:
        """
        Find the userdata directory belonging to the active Steam account.
        """
        userdata = self.find_userdata()

        if userdata is None:
            return None

        user = self.find_active_user()

        if user is None:
            return None

        path = userdata / str(user.account_id)

        if path.is_dir():
            return path

        return None

    def find_localconfig(self) -> Path | None:
        """
        Find localconfig.vdf for the active Steam account.
        """
        user_directory = self.find_user_directory()

        if user_directory is None:
            return None

        path = user_directory / "config" / "localconfig.vdf"

        if path.is_file():
            return path

        return None

    @staticmethod
    def _steam_id64_to_account_id(steam_id64: int) -> int:
        """
        Convert SteamID64 to the 32-bit account ID used by userdata.
        """
        return steam_id64 & 0xFFFFFFFF

    def _parse_users(
        self,
        users: dict[str, Any],
    ) -> list[SteamUser]:
        accounts: list[SteamUser] = []

        for steam_id, user_data in users.items():
            if not isinstance(user_data, dict):
                continue

            try:
                steam_id64 = int(steam_id)
            except (TypeError, ValueError):
                continue

            account_name = user_data.get("AccountName")

            if not isinstance(account_name, str):
                continue

            try:
                timestamp = int(user_data.get("Timestamp", "0"))
            except (TypeError, ValueError):
                timestamp = 0

            auto_login = str(
                user_data.get("AutoLogin", "0")
            ).lower() in {"1", "true"}

            accounts.append(
                SteamUser(
                    steam_id64=steam_id64,
                    account_id=self._steam_id64_to_account_id(steam_id64),
                    account_name=account_name,
                    timestamp=timestamp,
                    auto_login=auto_login,
                )
            )

        return accounts
