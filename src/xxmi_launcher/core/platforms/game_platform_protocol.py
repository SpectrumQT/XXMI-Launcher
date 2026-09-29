from typing import Protocol
from pathlib import Path

from core.platforms.game import Game
from core.platforms.game_platform import GamePlatform


class GamePlatformProtocol(Protocol):
    """
    Common interface for game platform integrations.

    Implementations provide platform-independent game operations while hiding platform-specific details
    such as AppIDs, installation discovery, and launch mechanisms.
    """
    platform: GamePlatform

    @classmethod
    def create(cls) -> "GamePlatformProtocol":
        ...

    def refresh(self) -> None:
        """
        Invalidate cached platform state.

        Call this when the platform's installed games or configuration may have changed.
        """
        ...

    def is_installed(self, game: Game) -> bool:
        """
        Return whether the specified game is installed on this platform.
        """
        ...

    def get_game_path(self, game: Game) -> Path | None:
        """
        Return installation directory of the specified game or None if not installed.
        """
        ...

    def get_launch_options(self, game: Game) -> str | None:
        """
        Return the launch options configured for the specified game.

        Returns:
            The configured launch options, or None if no options are set.
        """
        ...

    def set_launch_options(
        self,
        game: Game,
        options: str | None,
    ) -> str | None:
        """
        Set or remove the launch options for the specified game.

        Args:
            game: Game whose launch options should be changed.
            options: New launch options, or None to remove them.

        Returns:
            The previous launch options.
        """
        ...

    def launch(
        self,
        game: Game,
        args: str,
    ) -> bool:
        """
        Launch the specified game with additional arguments.

        Args:
            game: Game to launch.
            args: Additional arguments passed to the platform launcher.

        Returns:
            True if the launch request was successfully issued.
        """
        ...
