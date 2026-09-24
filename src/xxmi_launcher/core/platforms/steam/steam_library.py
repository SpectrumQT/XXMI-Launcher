from pathlib import Path
from typing import Any
from dataclasses import dataclass

from core.platforms.game import Game
from core.platforms.steam.vdf_file import VdfFile


@dataclass(frozen=True)
class SteamApp:
    """
    Information about an installed Steam application.
    """

    app_id: str
    name: str | None
    install_directory: Path
    manifest_path: Path


STEAM_APP_IDS: dict[Game, frozenset[str]] = {
    Game.ARKNIGHTS_ENDFIELD: frozenset({"4732690"}),
    Game.GENSHIN_IMPACT: frozenset(),
    Game.HONKAI_IMPACT: frozenset({"1671200"}),
    Game.HONKAI_STAR_RAIL: frozenset(),
    Game.WUTHERING_WAVES: frozenset({"3513350"}),
    Game.ZENLESS_ZONE_ZERO: frozenset({"4162040"}),
}


class SteamLibrary:
    """
    Discover Steam libraries and installed applications.

    This class is responsible for Steam library and app-manifest discovery.
    It does not manage Steam processes or user-specific configuration.
    """

    def __init__(self, steam_path: Path):
        self.steam_path = steam_path

    def find_game(self, game: Game) -> SteamApp | None:
        """
        Find an installed Steam game.

        Matching is attempted using known Steam AppIDs first, followed by
        keywords in the installation directory and Steam application name.

        Args:
            game: Game to find.

        Returns:
            The matching SteamApp, or None if the game is not installed.
        """
        apps = self._find_installed_apps()

        # AppID is the strongest and most reliable match.
        app_ids = STEAM_APP_IDS.get(game, frozenset())

        for app in apps:
            if app.app_id in app_ids:
                return app

        # Fall back to platform-independent game keywords.
        for app in apps:
            if self._matches_game(app, game):
                return app

        return None

    def find_app(self, app_id: str) -> SteamApp | None:
        """
        Find an installed Steam application by app ID.

        Args:
            app_id: Steam application ID.

        Returns:
            SteamApp if the application is installed, otherwise None.
        """
        for library in self.find_libraries():
            manifest = library / "steamapps" / f"appmanifest_{app_id}.acf"

            if not manifest.is_file():
                continue

            app = self._read_app_manifest(manifest)

            if app is not None:
                return app

        return None

    def find_install_directory(self, app_id: str) -> Path | None:
        """
        Find the installation directory of a Steam application.

        Args:
            app_id: Steam application ID.

        Returns:
            The application's installation directory, or None if it
            cannot be found.
        """
        app = self.find_app(app_id)

        if app is None:
            return None

        return app.install_directory

    def find_app_id(
            self,
            game_directory: Path,
            expected_app_id: str | None = None,
    ) -> str | None:
        """
        Find the Steam app ID associated with a game directory.

        Args:
            game_directory: Game installation directory.
            expected_app_id: Optional app ID to check directly.

        Returns:
            The matching app ID, or None if no manifest matches.
        """
        game_directory = game_directory.resolve()

        if expected_app_id is not None:
            app = self.find_app(expected_app_id)

            if app is None:
                return None

            if app.install_directory.resolve() == game_directory:
                return app.app_id

            return None

        for app in self._find_installed_apps():
            try:
                install_directory = app.install_directory.resolve()
            except OSError:
                continue

            if install_directory == game_directory:
                return app.app_id

        return None

    def find_libraries(self) -> list[Path]:
        """
        Find all Steam library directories.

        The Steam installation directory is always considered a library,
        followed by any additional libraries listed in libraryfolders.vdf.

        Returns:
            A list of existing Steam library directories.
        """
        libraries: list[Path] = []

        self._add_library(libraries, self.steam_path)

        libraryfolders = self._find_libraryfolders()

        if libraryfolders is None:
            return libraries

        data = VdfFile(libraryfolders).load()

        root = data.get("libraryfolders")

        if not isinstance(root, dict):
            return libraries

        for value in root.values():
            path = self._extract_library_path(value)

            if path is not None:
                self._add_library(libraries, path)

        return libraries

    # region Helpers

    @staticmethod
    def _matches_game(
            app: SteamApp,
            game: Game,
    ) -> bool:
        """
        Check whether a Steam application matches a game by keyword.

        Keywords are matched against both the installation directory name
        and the Steam application name.
        """
        values = (
            app.install_directory.name,
            app.name or "",
        )

        for value in values:
            normalized = SteamLibrary._normalize(value)

            if any(
                    SteamLibrary._normalize(keyword) in normalized
                    for keyword in game.keywords
            ):
                return True

        return False

    @staticmethod
    def _normalize(value: str) -> str:
        """
        Normalize text for loose keyword matching.

        Removes case, whitespace, punctuation, underscores, and separators.
        """
        return "".join(
            character.casefold()
            for character in value
            if character.isalnum()
        )

    def _find_installed_apps(self) -> list[SteamApp]:
        """
        Find all installed Steam applications across all libraries.
        """
        apps: list[SteamApp] = []

        for library in self.find_libraries():
            steamapps = library / "steamapps"

            if not steamapps.is_dir():
                continue

            for manifest in steamapps.glob("appmanifest_*.acf"):
                app = self._read_app_manifest(manifest)

                if app is not None:
                    apps.append(app)

        return apps

    def _find_libraryfolders(self) -> Path | None:
        """
        Find Steam's libraryfolders.vdf.

        Steam clients can have this file in either steamapps or config,
        so check both locations.
        """
        candidates = (
            self.steam_path / "steamapps" / "libraryfolders.vdf",
            self.steam_path / "config" / "libraryfolders.vdf",
        )

        for path in candidates:
            if path.is_file():
                return path

        return None

    @staticmethod
    def _extract_library_path(value: Any) -> Path | None:
        """
        Extract a library path from an entry in libraryfolders.vdf.

        Supports both:

            "1" "D:\\SteamLibrary"

        and:

            "1"
            {
                "path" "D:\\SteamLibrary"
                ...
            }
        """
        if isinstance(value, str):
            return Path(value)

        if not isinstance(value, dict):
            return None

        path = value.get("path")

        if not isinstance(path, str):
            return None

        return Path(path)

    @staticmethod
    def _add_library(
        libraries: list[Path],
        library: Path,
    ) -> None:
        """
        Add an existing library if it is not already present.
        """
        try:
            library = library.resolve()
        except OSError:
            return

        if not library.is_dir():
            return

        if library not in libraries:
            libraries.append(library)

    @staticmethod
    def _read_app_manifest(
        manifest: Path,
    ) -> SteamApp | None:
        """
        Read a Steam appmanifest_<appid>.acf file.
        """
        try:
            data = VdfFile(manifest).load()
        except (OSError, ValueError):
            return None

        app_state = data.get("AppState")

        if not isinstance(app_state, dict):
            return None

        app_id = app_state.get("appid")
        install_dir = app_state.get("installdir")
        name = app_state.get("name")

        if not isinstance(app_id, str):
            return None

        if not isinstance(install_dir, str) or not install_dir:
            return None

        if name is not None and not isinstance(name, str):
            name = None

        library = manifest.parent.parent

        return SteamApp(
            app_id=app_id,
            name=name,
            install_directory=library / "steamapps" / "common" / install_dir,
            manifest_path=manifest,
        )

    # endregion
