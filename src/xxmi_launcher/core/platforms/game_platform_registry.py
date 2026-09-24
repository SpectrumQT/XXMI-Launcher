from enum import Enum
from typing import Iterable

from core.platforms.game import Game
from core.platforms.game_platform import GamePlatform
from core.platforms.game_platform_protocol import GamePlatformProtocol


class PlatformRegistry:
    def __init__(
        self,
        managers: Iterable[type[GamePlatformProtocol]],
    ) -> None:
        self._managers: dict[GamePlatform, GamePlatformProtocol] = {}

        for manager_type in managers:
            try:
                manager = manager_type.create()
            except Exception:
                continue

            self._managers[manager.platform] = manager

    def get_game_platforms(
        self,
        game: Game,
    ) -> list[GamePlatform]:
        return [
            manager.platform
            for manager in self._managers.values()
            if manager.is_installed(game)
        ]

    def is_installed(
        self,
        game: Game,
        platform: GamePlatform,
    ) -> bool:
        manager = self._managers.get(platform)

        if manager is None:
            return False

        return manager.is_installed(game)

    def get_platform_manager(
        self,
        platform: GamePlatform,
    ) -> GamePlatformProtocol | None:
        return self._managers.get(platform)