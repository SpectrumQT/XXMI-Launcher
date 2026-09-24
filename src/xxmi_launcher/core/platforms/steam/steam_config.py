from typing import Any

from core.platforms.steam.vdf_file import VdfFile


class SteamConfigError(RuntimeError):
    """
    Base exception for Steam configuration errors.
    """


class SteamConfigStructureError(SteamConfigError):
    """
    Raised when the expected Steam VDF structure is missing or invalid.
    """


class SteamAppNotFoundError(SteamConfigError):
    """
    Raised when an application's configuration does not exist.
    """


class SteamConfig:
    """
    Access Steam-specific settings stored in localconfig.vdf.

    This class only modifies existing Steam configuration. It never creates
    missing VDF structure or application entries.
    """

    ROOT_KEY = "UserLocalConfigStore"
    SOFTWARE_KEY = "Software"
    VALVE_KEY = "Valve"
    STEAM_KEY = "Steam"
    APPS_KEY = "apps"
    LAUNCH_OPTIONS_KEY = "LaunchOptions"

    def __init__(self, vdf_file: VdfFile):
        self.vdf_file = vdf_file

    def get_launch_options(self, app_id: str) -> str | None:
        """
        Get the launch options configured for an existing Steam app.

        Returns:
            The configured launch options, or None if no LaunchOptions
            value exists.

        Raises:
            SteamConfigStructureError:
                If the expected Steam configuration structure is missing.
            SteamAppNotFoundError:
                If the application has no configuration entry.
        """
        data = self.vdf_file.load()

        app = self._get_app(data, app_id)

        value = app.get(self.LAUNCH_OPTIONS_KEY)

        if value is None:
            return None

        if not isinstance(value, str):
            raise SteamConfigStructureError(
                f"Invalid LaunchOptions value for app {app_id!r}."
            )

        return value

    def set_launch_options(
        self,
        app_id: str,
        options: str | None,
    ) -> str | None:
        """
        Set or remove launch options for an existing Steam app.

        Args:
            app_id:
                Steam application ID.
            options:
                Launch options to set. Pass None to remove LaunchOptions.

        Returns:
            The previous launch options, or None if none were configured.

        Raises:
            SteamConfigStructureError:
                If the expected Steam configuration structure is missing.
            SteamAppNotFoundError:
                If the application has no configuration entry.
        """
        data = self.vdf_file.load()

        app = self._get_app(data, app_id)

        previous = app.get(self.LAUNCH_OPTIONS_KEY)

        if previous is not None and not isinstance(previous, str):
            raise SteamConfigStructureError(
                f"Invalid LaunchOptions value for app {app_id!r}."
            )

        if options is None:
            # app.pop(self.LAUNCH_OPTIONS_KEY, None)
            app[self.LAUNCH_OPTIONS_KEY] = ""
        else:
            app[self.LAUNCH_OPTIONS_KEY] = options

        self.vdf_file.save(data)

        return previous

    def _get_app(
        self,
        data: dict[str, Any],
        app_id: str,
    ) -> dict[str, Any]:
        """
        Return an existing application's configuration.

        No VDF nodes are created.
        """
        steam = self._get_steam(data)

        apps = steam.get(self.APPS_KEY)

        if not isinstance(apps, dict):
            raise SteamConfigStructureError(
                f"Missing or invalid '{self.APPS_KEY}' section."
            )

        app = apps.get(str(app_id))

        if app is None:
            raise SteamAppNotFoundError(
                f"Steam app {app_id!r} was not found in localconfig.vdf."
            )

        if not isinstance(app, dict):
            raise SteamConfigStructureError(
                f"Invalid configuration for Steam app {app_id!r}."
            )

        return app

    def _get_steam(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Return the existing Steam configuration node.

        No VDF nodes are created.
        """
        root = data.get(self.ROOT_KEY)

        if not isinstance(root, dict):
            raise SteamConfigStructureError(
                f"Missing or invalid '{self.ROOT_KEY}' section."
            )

        software = root.get(self.SOFTWARE_KEY)

        if not isinstance(software, dict):
            raise SteamConfigStructureError(
                f"Missing or invalid '{self.SOFTWARE_KEY}' section."
            )

        valve = software.get(self.VALVE_KEY)

        if not isinstance(valve, dict):
            raise SteamConfigStructureError(
                f"Missing or invalid '{self.VALVE_KEY}' section."
            )

        steam = valve.get(self.STEAM_KEY)

        if not isinstance(steam, dict):
            raise SteamConfigStructureError(
                f"Missing or invalid '{self.STEAM_KEY}' section."
            )

        return steam
