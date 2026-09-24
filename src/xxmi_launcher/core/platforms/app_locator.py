import os
import re
import winreg

from collections.abc import Iterable
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class RegistryPath:
    root: int
    key: str


@dataclass(frozen=True)
class RegistryValuePath:
    root: int
    key: str
    value: str


@dataclass(frozen=True)
class AppInfo:
    exe_names: Iterable[str]
    display_names: Iterable[str] = ()
    known_paths: Iterable[Path | str] = ()
    known_registry_paths: Iterable[RegistryValuePath] = ()
    expected_relative_paths: Iterable[Path | str] = ()


class AppLocator:
    """
    Locate a Windows executable using several independent sources:

    1. Known absolute paths.
    2. Known registry values.
    3. Windows uninstall registry entries.
    4. Windows application-usage registry entries.

    Registry information is treated only as a source of candidates.
    A candidate is returned only when it points to an existing .exe file.

    This class is intentionally generic.
    It does not know anything about Steam, Epic, Discord, etc.;
    callers provide executable names and, optionally, application display
    names and known registry locations.
    """

    UNINSTALL_PATHS: tuple[RegistryPath, ...] = (
        RegistryPath(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        RegistryPath(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        RegistryPath(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    )

    USAGE_PATHS: tuple[RegistryPath, ...] = (
        RegistryPath(winreg.HKEY_CLASSES_ROOT, r"Local Settings\Software\Microsoft\Windows\Shell\MuiCache"),
        RegistryPath(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\FeatureUsage\AppSwitched"),
        RegistryPath(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\FeatureUsage\ShowJumpView"),
    )

    _QUOTED_EXE_RE = re.compile(r'"([^"]+\.exe)"', re.IGNORECASE)

    _UNQUOTED_EXE_RE = re.compile(r"(?P<path>[A-Za-z]:\\.*?\.exe)", re.IGNORECASE)

    def __init__(
        self,
        app_info: AppInfo,
        *,
        search_install_locations: bool = True,
    ) -> None:
        """
        Args:
            app_info.exe_names:
                Executable file names to look for, e.g. {"EpicGamesLauncher.exe"}.

            app_info.display_names:
                Windows uninstall-registration display names, e.g. {"Epic Games Launcher"}.
                When supplied, configured exe_names are explicitly searched in folders where uninstaller exe is located
                for all keys with matching DisplayName. Otherwise, uninstaller exe name is simply searched in exe_names.

            app_info.known_paths:
                Known absolute executable paths.

            app_info.known_registry_paths:
                Known registry values containing executable paths.

            app_info.expected_relative_paths:
                Optional path suffixes used to disambiguate generic executable names.
                Paths are matched against the candidate's parent path, independently of drive/root.

                For example:
                    Path("HoYoPlay")
                matches:
                    C:\\Games\\HoYoPlay\\launcher.exe
                    D:\\Apps\\HoYoPlay\\launcher.exe

                And:
                    Path("Vendor/Launcher")
                matches:
                    C:\\Program Files (x86)\\Vendor\\Launcher\\Launcher.exe

            search_install_locations:
                If True, search registered InstallLocation directories for the requested executable names.
        """
        self._exe_names = frozenset(name.casefold() for name in app_info.exe_names if name)
        if not self._exe_names:
            raise ValueError("exe_names must contain at least one executable name")
        self._display_names = frozenset(name.casefold() for name in app_info.display_names if name)
        self._known_paths = tuple(Path(path) for path in app_info.known_paths)
        self._known_registry_paths = tuple(app_info.known_registry_paths)
        self._expected_relative_paths = tuple(
            self._normalize_relative_path(path) for path in app_info.expected_relative_paths if str(path)
        )
        self._search_install_locations = search_install_locations

    def find(self) -> Path | None:
        """
        Find the first valid executable.

        Search order:

        1. Known paths.
        2. Known registry paths.
        3. Uninstall registry.
        4. Usage registry.

        Returns:
            The executable path, or None if no valid executable was found.
        """
        for finder in (
            self._find_known_paths,
            self._find_known_registry_paths,
            self._find_uninstall_registry,
            self._find_usage_registry,
        ):
            executable = finder()

            if executable is not None:
                return executable

        return None

    def find_all(self) -> list[Path]:
        """
        Find all valid executable candidates.

        Unlike find(), this does not stop after the first match and removes duplicate paths.
        """
        results: list[Path] = []
        seen: set[str] = set()

        for finder in (
            self._iter_known_paths,
            self._iter_known_registry_paths,
            self._iter_uninstall_registry,
            self._iter_usage_registry,
        ):
            for candidate in finder():
                executable = self._validate(candidate)

                if executable is None:
                    continue

                key = self._normalization_key(executable)

                if key in seen:
                    continue

                seen.add(key)
                results.append(executable)

        return results

    # endregion

    # region Known paths

    def _find_known_paths(self) -> Path | None:
        for path in self._iter_known_paths():
            executable = self._validate(path)

            if executable is not None:
                return executable

        return None

    def _iter_known_paths(self) -> Iterable[Path]:
        for path in self._known_paths:
            yield from self._iter_path_candidates(path)

    # endregion

    # region Known registry

    def _find_known_registry_paths(self) -> Path | None:
        for candidate in self._iter_known_registry_paths():
            executable = self._validate(candidate)

            if executable is not None:
                return executable

        return None

    def _iter_known_registry_paths(self) -> Iterable[Path]:
        for registry_path in self._known_registry_paths:
            try:
                with winreg.OpenKey(registry_path.root, registry_path.key, 0, winreg.KEY_READ) as key:
                    value, _ = winreg.QueryValueEx(key, registry_path.value)
            except OSError:
                continue

            if not isinstance(value, str):
                continue

            value = value.strip()

            if not value:
                continue

            yield from self._iter_path_candidates(value)

    # endregion

    # region Uninstall registry

    def _find_uninstall_registry(self) -> Path | None:
        for candidate in self._iter_uninstall_registry():
            executable = self._validate(candidate)

            if executable is not None:
                return executable

        return None

    def _iter_uninstall_registry(self) -> Iterable[Path]:
        for registry_path in self.UNINSTALL_PATHS:
            yield from self._iter_uninstall_key(registry_path.root, registry_path.key)

    def _iter_uninstall_key(
        self,
        root: int,
        key_path: str,
    ) -> Iterable[Path]:
        try:
            with winreg.OpenKey(root, key_path, 0, winreg.KEY_READ) as uninstall_key:
                subkey_count = winreg.QueryInfoKey(uninstall_key)[0]

                for index in range(subkey_count):
                    try:
                        subkey_name = winreg.EnumKey(uninstall_key, index)
                    except OSError:
                        continue

                    try:
                        with winreg.OpenKey(uninstall_key, subkey_name, 0, winreg.KEY_READ) as app_key:
                            yield from self._iter_uninstall_entry(app_key)

                    except OSError:
                        continue

        except OSError:
            return

    def _iter_uninstall_entry(
        self,
        key: winreg.HKEYType,
    ) -> Iterable[Path]:

        display_name_matches = False
        if self._display_names:
            display_name = self._read_string(key, "DisplayName")
            if display_name is not None:
                display_name_matches = display_name.casefold() in self._display_names

        # DisplayIcon is usually the best direct executable candidate.
        display_icon = self._read_string(key, "DisplayIcon")

        if display_icon is not None:
            yield from self._extract_executable_paths(display_icon, display_name_matches)

        # UninstallString can also contain the executable path.
        uninstall_string = self._read_string(key, "UninstallString")

        if uninstall_string is not None:
            yield from self._extract_executable_paths(uninstall_string, display_name_matches)

        if not self._search_install_locations:
            return

        install_location = self._read_string(key, "InstallLocation")

        if install_location is None:
            return

        location = self._expand_path(install_location)

        if not location.is_dir():
            return

        if display_name_matches:
            yield from self._iter_candidate_directory(location)
        else:
            yield location

    def _iter_candidate_directory(
        self,
        directory: Path,
    ) -> Iterable[Path]:
        """
        Generate directory paths for each configured exe name. No real traversal is performed.
        """
        for exe_name in self._exe_names:
            yield directory / exe_name

    # endregion

    # region Usage registry

    def _find_usage_registry(self) -> Path | None:
        for candidate in self._iter_usage_registry():
            executable = self._validate(candidate)

            if executable is not None:
                return executable

        return None

    def _iter_usage_registry(self) -> Iterable[Path]:
        for registry_path in self.USAGE_PATHS:
            yield from self._iter_usage_key(registry_path.root, registry_path.key)

    def _iter_usage_key(
        self,
        root: int,
        key_path: str,
    ) -> Iterable[Path]:
        try:
            with winreg.OpenKey(root, key_path, 0, winreg.KEY_READ) as key:
                value_count = winreg.QueryInfoKey(key)[1]

                for index in range(value_count):
                    try:
                        name, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        continue

                    # MuiCache commonly stores the executable path as the value name.
                    # FeatureUsage keys can also expose paths in names/data depending on Windows version.
                    for candidate in self._extract_executable_paths(name):
                        if self._is_requested_executable(candidate):
                            yield candidate

                    if isinstance(value, str):
                        for candidate in self._extract_executable_paths(value):
                            if self._is_requested_executable(candidate):
                                yield candidate

        except OSError:
            return

    # endregion

    # region Candidate extraction

    def _matches_expected_relative_path(self, path: Path) -> bool:
        """
        Return True when the candidate's parent path ends with one of the configured relative path suffixes.

        If no expected relative paths were configured, every parent path matches.
        """
        if not self._expected_relative_paths:
            return True

        parent_parts = tuple(part.casefold() for part in path.parent.parts)

        return any(
            len(parent_parts) >= len(expected)
            and parent_parts[-len(expected):] == expected
            for expected in self._expected_relative_paths
        )

    def _iter_path_candidates(self, path: Path | str) -> Iterable[Path]:
        path = self._expand_path(path)

        if path.suffix.casefold() == ".exe":
            yield path
            return

        for exe_name in self._exe_names:
            yield path / exe_name

    def _is_requested_executable(self, path: Path) -> bool:
        if not self._exe_names:
            return False

        return path.name.casefold() in self._exe_names

    def _extract_executable_paths(
        self,
        value: str,
        from_parent: bool = False,
    ) -> Iterable[Path]:
        value = value.strip()

        if not value:
            return

        # Environment variables such as %ProgramFiles% may occur in registry values.
        expanded = os.path.expandvars(value)

        # Quoted executable:
        #   "C:\Program Files\App\App.exe" /uninstall
        for match in self._QUOTED_EXE_RE.finditer(expanded):
            path = self._clean_candidate(match.group(1))

            if path is not None:
                if from_parent:
                    yield from self._iter_candidate_directory(path.parent)
                else:
                    yield path

        # Unquoted executable:
        #   C:\Program Files\App\App.exe /uninstall
        for match in self._UNQUOTED_EXE_RE.finditer(expanded):
            path = self._clean_candidate(match.group("path"))

            if path is not None:
                if from_parent:
                    yield from self._iter_candidate_directory(path.parent)
                else:
                    yield path

        # The entire value may itself be an executable path.
        path = self._clean_candidate(expanded)

        if path is not None:
            if from_parent:
                yield from self._iter_candidate_directory(path.parent)
            else:
                yield path

    @staticmethod
    def _clean_candidate(value: str) -> Path | None:
        value = value.strip()

        if not value:
            return None

        # Remove surrounding quotes.
        if value.startswith('"'):
            end_quote = value.find('"', 1)

            if end_quote == -1:
                return None

            value = value[1:end_quote]
        else:
            # For unquoted values, only the executable path itself should be considered.
            # Anything after the .exe is a command-line argument.
            match = re.match(r"(?i)^(.*?\.exe)(?:\s|$)", value)

            if match is None:
                return None

            value = match.group(1)

        # DisplayIcon commonly stores an icon index:
        #   C:\Program Files\App\App.exe,0
        # Remove that suffix.
        value = re.sub(r",\d+$", "", value)

        value = value.strip()

        if not value or not value.casefold().endswith(".exe"):
            return None

        return Path(value)

    # endregion

    # region Validation

    def _validate(self, path: Path) -> Path | None:
        try:
            path = self._expand_path(path)
            path = path.resolve()
        except (OSError, RuntimeError):
            return None

        if path.name.casefold() not in self._exe_names:
            return None

        if not path.is_file():
            return None

        if not self._matches_expected_relative_path(path):
            return None

        return path

    @staticmethod
    def _expand_path(path: Path | str) -> Path:
        value = os.path.expandvars(os.path.expanduser(str(path)))
        return Path(value)

    @staticmethod
    def _normalization_key(path: Path) -> str:
        return os.path.normcase(
            os.path.normpath(str(path)),
        )

    # endregion

    # region Helpers

    @staticmethod
    def _read_string(
        key: winreg.HKEYType,
        name: str,
    ) -> str | None:
        try:
            value, _ = winreg.QueryValueEx(key, name)
        except (FileNotFoundError, OSError):
            return None

        if not isinstance(value, str):
            return None

        value = value.strip()

        return value or None

    @staticmethod
    def _normalize_relative_path(path: Path | str) -> tuple[str, ...]:
        """
        Normalize a relative path for case-insensitive Windows comparison.

        The returned tuple contains only path components and does not include any drive/root information.
        """
        path = Path(path)

        if path.is_absolute():
            raise ValueError(f"expected_relative_paths must contain relative paths: {path!s}")

        return tuple(part.casefold() for part in path.parts if part not in ("", "."))

    # endregion
