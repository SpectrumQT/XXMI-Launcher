from pathlib import Path
from typing import ClassVar

from core.platforms.app_locator import AppLocator, AppInfo


class PlatformLocator:
    """
    Base class for locators that discover a platform's executable.
    """
    APP_INFO: ClassVar[AppInfo]

    def __init__(self) -> None:
        self._app_locator = AppLocator(self.APP_INFO)
        self._exe_path: Path | None = None
        self._searched = False

    def find_executable(self) -> Path | None:
        """
        Find platform's .exe.

        Returns:
            Path to platform's .exe, or None if it cannot be located.
        """
        if self._searched:
            return self._exe_path

        self._searched = True
        self._exe_path = self._app_locator.find()

        return self._exe_path
