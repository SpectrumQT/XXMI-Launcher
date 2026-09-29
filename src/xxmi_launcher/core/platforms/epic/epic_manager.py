import os

from pathlib import Path

from core.platforms.game import Game
from core.platforms.game_platform import GamePlatform
from core.platforms.epic.epic_library import EpicLibrary, EpicApp
from core.platforms.epic.epic_locator import EpicLocator


class EpicManager:
    platform = GamePlatform.EPIC

    def __init__(
        self,
        library: EpicLibrary,
    ):
        self.library = library
        self.app_cache: dict[Game, EpicApp | None] = {}

    @classmethod
    def create(cls) -> "EpicManager":
        locator = EpicLocator()

        epic_exe_path = locator.find_executable()

        if epic_exe_path is None:
            raise RuntimeError("Epic Games executable not found.")

        return cls(
            library=EpicLibrary(),
        )

    # region GamePlatformProtocol

    def refresh(self) -> None:
        self.app_cache.clear()

    def is_installed(self, game: Game) -> bool:
        return self._get_game(game) is not None

    def get_game_path(self, game: Game) -> Path | None:
        game = self._get_game(game)
        return game.install_location if game else None

    def get_launch_options(self, game: Game) -> str | None:
        # Epic doesn't have an equivalent to Steam's per-game launch options
        # in this abstraction.
        return None

    def set_launch_options(
        self,
        game: Game,
        options: str | None,
    ) -> str | None:
        raise NotImplementedError(
            "Epic Games does not support configurable launch options "
            "through this platform implementation."
        )

    def launch(
        self,
        game: Game,
        args: str,
    ) -> bool:
        installation = self._require_game(game)

        return self.launch_app(installation, args)

    # endregion

    # region Epic Application API

    def launch_app(
        self,
        installation: EpicApp,
        args: str,
    ) -> bool:
        uri = self._build_launch_uri(installation, args)

        try:
            os.startfile(uri)
        except OSError:
            return False

        return True

    @staticmethod
    def _build_launch_uri(
        installation: EpicApp,
        args: str,
    ) -> str:
        app = f"{installation.namespace_id}%3A{installation.item_id}%3A{installation.artifact_id}"

        query = "action=launch&silent=true"

        if args:
            query += f'&args="{args.replace(' ', "%20")}"'

        return f"com.epicgames.launcher://apps/{app}?{query}"

    # endregion

    # region Helpers

    def _get_game(self, game: Game) -> EpicApp | None:
        if game not in self.app_cache:
            self.app_cache[game] = self.library.find_game(game)

        return self.app_cache[game]

    def _require_game(self, game: Game) -> EpicApp:
        installation = self._get_game(game)

        if installation is None:
            raise RuntimeError(
                f"{game.value} is not installed through Epic Games."
            )

        return installation

    # endregion
