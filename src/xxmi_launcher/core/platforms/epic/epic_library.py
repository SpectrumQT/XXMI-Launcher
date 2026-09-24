import json
import os

from pathlib import Path
from dataclasses import dataclass

from core.platforms.game import Game


@dataclass(frozen=True)
class EpicApp:
    namespace_id: str
    item_id: str
    artifact_id: str
    app_version: str
    install_location: Path


class EpicLibrary:
    @property
    def installed_dat(self) -> Path:
        return Path(os.environ["PROGRAMDATA"]) / "Epic" / "UnrealEngineLauncher" / "LauncherInstalled.dat"

    def find_game(self, game: Game) -> EpicApp | None:
        path = self.installed_dat

        if not path.is_file():
            return None

        with path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)

        installations = data.get("InstallationList", [])

        if not isinstance(installations, list):
            return None

        for entry in installations:
            if not isinstance(entry, dict):
                continue

            location = entry.get("InstallLocation")

            if not isinstance(location, str):
                continue

            install_location = Path(location)

            if not self._matches_game(install_location, game):
                continue

            namespace_id = entry.get("NamespaceId")
            item_id = entry.get("ItemId")
            artifact_id = entry.get("ArtifactId")
            app_version = entry.get("AppVersion")

            if not all(
                isinstance(value, str)
                for value in (
                    namespace_id,
                    item_id,
                    artifact_id,
                    app_version,
                )
            ):
                continue

            return EpicApp(
                namespace_id=namespace_id,
                item_id=item_id,
                artifact_id=artifact_id,
                app_version=app_version,
                install_location=install_location,
            )

        return None

    @staticmethod
    def _matches_game(
        install_location: Path,
        game: Game,
    ) -> bool:
        name = EpicLibrary._normalize(install_location.name)

        return any(
            EpicLibrary._normalize(keyword) in name
            for keyword in game.keywords
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return "".join(
            character.casefold()
            for character in value
            if character.isalnum()
        )