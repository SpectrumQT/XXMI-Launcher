from pathlib import Path
from contextlib import contextmanager
from collections.abc import Iterator

from core.platforms.game import Game
from core.platforms.game_platform import GamePlatform
from core.platforms.steam.vdf_file import VdfFile
from core.platforms.steam.steam_locator import SteamLocator
from core.platforms.steam.steam_library import SteamLibrary, SteamApp
from core.platforms.steam.steam_config import SteamConfig

from core.utils.process_manager import ProcessManager


class SteamManager:
    """
    Manage the Steam client and expose Steam-specific operations.

    SteamManager coordinates:
        - Steam process lifecycle
        - Steam configuration
        - Steam library
    """
    platform = GamePlatform.STEAM

    def __init__(
        self,
        locator: SteamLocator,
        process_manager: ProcessManager,
        config: SteamConfig,
        library: SteamLibrary,
    ):
        self.locator = locator
        self.process_manager = process_manager
        self.config = config
        self.library = library

        self.app_cache : dict[Game, SteamApp | None] = {}

    @classmethod
    def create(cls) -> 'SteamManager':
        """
        Create a SteamManager using the Steam installation discovered by SteamLocator.

        Raises:
            RuntimeError:
                If Steam or its required configuration cannot be found.
        """
        locator = SteamLocator()

        steam_exe_path = locator.find_executable()

        if steam_exe_path is None:
            raise RuntimeError("Steam executable not found.")

        localconfig = locator.find_localconfig()

        if localconfig is None:
            raise RuntimeError("Steam localconfig.vdf not found.")

        return cls(
            locator=locator,
            process_manager=ProcessManager(steam_exe_path),
            config=SteamConfig(
                VdfFile(localconfig),
            ),
            library=SteamLibrary(steam_exe_path.parent),
        )

    # region GamePlatformProtocol

    def refresh(self):
        self.app_cache.clear()

    def is_installed(self, game: Game) -> bool:
        return self._get_game(game) is not None

    def get_game_path(self, game: Game) -> Path | None:
        game = self._get_game(game)
        return game.install_directory if game else None

    def get_launch_options(self, game: Game) -> str | None:
        """
        Get the launch options configured for a Steam application.
        """
        app = self._require_game(game)
        return self.config.get_launch_options(app.app_id)

    def set_launch_options(
            self,
            game: Game,
            options: str | None,
    ) -> str | None:
        """
        Set or remove the launch options for a Steam application.

        Steam is temporarily stopped while localconfig.vdf is modified.
        If Steam was running before the operation, it is restarted afterward.

        Returns:
            The previous launch options.
        """
        app = self._require_game(game)

        with self._temporarily_stopped():
            return self.config.set_launch_options(app.app_id, options)

    def launch(self, game: Game, args: str) -> bool:
        app = self._require_game(game)
        return  self.launch_app(app.app_id, args)

    # endregion

    # region Steam Process Management

    def is_running(self) -> bool:
        """
        Return whether Steam is currently running.
        """
        return self.process_manager.is_running()

    def start(self) -> bool:
        """
        Start Steam.

        Returns:
            True if Steam is running after the operation.
        """
        return self.process_manager.start()

    def shutdown(
        self,
        *,
        timeout: float = 30.0,
    ) -> bool:
        """
        Gracefully shut down Steam.

        Returns:
            True if Steam is stopped after the operation.
        """
        return self.process_manager.stop_with_args(
            "-shutdown",
            timeout=timeout,
        )

    def restart(
        self,
        *,
        timeout: float = 30.0,
    ) -> bool:
        """
        Gracefully restart Steam.

        Returns:
            True if Steam is running after the operation.
        """
        return self.process_manager.restart(
            stop_args="-shutdown",
            timeout=timeout,
        )

    # endregion

    # region Steam Application API

    def launch_app(self, app_id: str, args: str) -> bool:
        """
        Launch a Steam application by App ID.

        Steam is responsible for resolving the application and its
        configured launch options.

        Returns:
            True if the launch command was started successfully.
        """
        cmd_args = f"-applaunch {app_id}"
        if args:
            cmd_args += ' ' + args
        self.process_manager.start(cmd_args, check_running=False)

        return True

    def find_app(self, app_id: str):
        """
        Find an installed Steam application.
        """
        return self.library.find_app(app_id)

    def find_install_directory(self, app_id: str) -> Path | None:
        """
        Find the installation directory for a Steam application.
        """
        return self.library.find_install_directory(app_id)

    def find_app_id(
        self,
        game_directory: Path,
        expected_app_id: str | None = None,
    ) -> str | None:
        """
        Find the Steam App ID associated with a game directory.
        """
        return self.library.find_app_id(
            game_directory,
            expected_app_id,
        )

    # endregion

    # region Helpers

    def _require_game(self, game: Game) -> SteamApp:
        app = self._get_game(game)

        if app is None:
            raise RuntimeError(f"{game.value} is not installed.")

        return app

    def _get_game(self, game: Game) -> SteamApp | None:
        if game not in self.app_cache:
            self.app_cache[game] = self.library.find_game(game)

        return self.app_cache[game]

    def _require_stopped(self) -> None:
        """
        Ensure Steam is not running before modifying its local configuration.
        """
        if self.is_running():
            raise RuntimeError(
                "Steam must be stopped before modifying localconfig.vdf."
            )

    @contextmanager
    def _temporarily_stopped(self) -> Iterator[None]:
        """
        Temporarily stop Steam if it is currently running.

        Steam is restarted when leaving the context if it was running when entering it.
        """
        was_running = self.is_running()

        if was_running and not self.shutdown():
            raise RuntimeError("Failed to stop Steam.")

        try:
            self._require_stopped()
            yield
        except BaseException:
            if was_running:
                self.start()
            raise
        else:
            if was_running and not self.start():
                raise RuntimeError("Failed to restart Steam.")

    # endregion
