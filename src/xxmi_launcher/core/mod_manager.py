
import logging
import shutil
import json
import fnmatch

from pathlib import Path
from dataclasses import dataclass, field

import core.path_manager as Paths
import core.event_manager as Events

log = logging.getLogger(__name__)


@dataclass
class Section:
    name: str
    command_lists: list[str] = field(default_factory=list)
    triggered_slots: list[tuple[int, str]] = field(default_factory=list)


@dataclass(frozen=True)
class Issue:
    line_id: int
    reason: str


@dataclass
class ValidationResult:
    file_issue: Issue | None = None
    line_issues: dict[int, Issue] = field(default_factory=dict)


@dataclass
class ParsedIni:
    sections: dict[str, Section] = field(default_factory=dict)


class IniSanitizerCache:
    def __init__(self):
        self.file_path: Path | None = None
        self.modified: bool = False
        self.data: dict[str, float] = {}

    def get_mod_time(self, path: Path):
        return self.data.get(str(path.resolve()), None)

    def add_path(self, path: Path):
        self.data[str(path.resolve())] = path.stat().st_mtime
        self.modified = True

    def load(self, mods_path: Path, cache_path: Path | None = None):
        self.file_path = cache_path or mods_path

        if self.file_path.suffix != '.json':
            self.file_path /= 'ini_sanitizer_cache.json'

        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.data = {k: float(v) for k, v in json.load(f).items()}
            except Exception:
                self.data = {}
                log.exception(f'Failed to load ini sanitizer cache {self.file_path}')

        self.modified = False

    def save(self):
        if self.modified and self.file_path:
            Paths.verify_path(self.file_path.parent)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)


class IniSanitizer:
    # Known filenames we always want disabled
    unwanted_files: set[str] = {'vscheck.ini'}
    # Resource slots we don't want ever see CheckTextureOverride for
    unwanted_triggers: set[str] = {'ib', 'vb0'}
    # Common sections used for d3dx.ini detection
    d3dx_ini_keywords: set[str] = {'[loader', '[stereo', '[commandlistunbindallrendertargets'}
    # Common option values used for d3dx.ini detection
    d3dx_ini_option_values: dict[str, str] = {'include_recursive': 'mods', 'exclude_recursive': 'disabled*'}

    def __init__(self):
        self.cache: IniSanitizerCache = IniSanitizerCache()

    def sanitize_mods_folder(
            self,
            mods_path: Path,
            cache_path: Path | None = None,
            dry_run: bool = True,
            use_cache: bool = True,
            exclude_patterns: list[str] | None = None
        ):
        """Shutdown the worst ini offenders in Mods folder.

        Quite often, due to lack of knowledge (or infrastructure), modders ship unwanted ini files with their mods.
        Those files have extremely negative impact on performance and stability, and here we:
        1. Disable all rogue d3dx.ini files (should never be present in Mods folder).
        2. Disable all VSCheck.ini files (they trigger ib, already done by EFMI).
        3. Comment out all CheckTextureOverride for ib or vb0 in any section (already done by EFMI).
        4. Comment out all ShaderRegex sections running global CheckTextureOverride (FPS killers).
        """
        dry_prefix = '[DRY]: ' if dry_run else ''

        Paths.verify_path(mods_path)

        # Load list of already processed files to avoid scanning them
        if use_cache:
            self.cache.load(mods_path, cache_path)

        # Process all ini files in given path
        for path in Path(mods_path).rglob("*.ini"):

            # Exclude paths that are configured to be ignored by DLL
            if exclude_patterns:
                if self.should_exclude(path.relative_to(mods_path), exclude_patterns):
                    continue

            # Skip unchanged files using the cache
            if use_cache:
                file_mod_time = path.stat().st_mtime
                cache_mod_time = self.cache.get_mod_time(path)
                if cache_mod_time == file_mod_time:
                    # log.debug(f'Skipped already processed file sanitizing: {path}')
                    continue

            validation_result = ValidationResult()
            ini_lines = []

            # Add VSCheck.ini to disable list
            if path.name.lower() in self.unwanted_files:
                validation_result.file_issue = Issue(0, f'unneeded {path.name}')

            # Read ini and analyze its behavior
            if not validation_result.file_issue:
                try:
                    ini_lines = path.read_text(encoding='utf-8').splitlines()
                    validation_result = self.validate_ini(ini_lines)
                    # Report commented lines
                    if validation_result.line_issues.values():
                        log.info(f'{dry_prefix}Commenting out {len(validation_result.line_issues)} lines in {path.relative_to(mods_path.parent)}...')
                        self.sanitize_ini(ini_lines, validation_result)
                except Exception:
                    log.exception(f'Failed to sanitize {path}')

            # Disable ini file with issue
            if validation_result.file_issue:
                Events.Fire(Events.Application.VerifyFileAccess(path=path, write=True))
                backup_path = self.make_backup(path, rename=True, dry_run=dry_run)
                log.info(f'{dry_prefix}Disabled {path.relative_to(mods_path.parent)} (reason: {validation_result.file_issue.reason}), new name: {backup_path.name} ')
                continue

            # Write ini with commented ini lines with issues
            if validation_result.line_issues and not dry_run:
                Events.Fire(Events.Application.VerifyFileAccess(path=path, write=True))
                self.make_backup(path)
                path.write_text('\n'.join(ini_lines), encoding='utf-8')

            # Update cache with current modification time
            if use_cache:
                self.cache.add_path(path)

        if use_cache:
            self.cache.save()

    @classmethod
    def sanitize_ini(cls, ini_lines: list[str], validation_result: ValidationResult):
        # Comment ini lines with issues
        for issue in validation_result.line_issues.values():
            line = ini_lines[issue.line_id]
            if line.strip().startswith(';'):
                continue
            log.info(f'    - Line #{issue.line_id+1} `{line.strip()}` (reason: {issue.reason})')
            ini_lines[issue.line_id] = ';' + line

    @classmethod
    def validate_ini(cls, ini_lines: list[str]) -> ValidationResult:

        # Run basic validation pass (which doesn't involve section references handling)
        validation_result, parsed_ini = cls.validate_ini_text(ini_lines)

        # Ini disable pending, no need to dig deeper
        if validation_result.file_issue:
            return validation_result

        # Detect global Shader RegEx based triggers
        for section_name, section in parsed_ini.sections.items():
            if section_name.startswith('shaderregex'):
                # Allow global triggers for Shader RegEx with patterns
                pattern = parsed_ini.sections.get(f'{section_name}.pattern', None)
                if pattern:
                    continue
                # Comment global triggers defined directly in Shader RegEx section
                for (line_id, triggered_slot) in section.triggered_slots:
                    validation_result.line_issues[line_id] = Issue(line_id, f'forbidden global trigger for {triggered_slot} in [{section_name}]')
                # Comment global triggers defined in CommandLists called by Shader RegEx section
                for command_list_name in section.command_lists:
                    command_list = parsed_ini.sections.get(command_list_name, None)
                    if command_list is None:
                        continue
                    for (line_id, triggered_slot) in command_list.triggered_slots:
                        validation_result.line_issues[line_id] = Issue(line_id, f'forbidden global trigger for {triggered_slot} in [{section_name}]/[{command_list_name}]')

        return validation_result

    @classmethod
    def validate_ini_text(cls, ini_lines: list[str]) -> tuple[ValidationResult, ParsedIni | None]:

        result: ValidationResult = ValidationResult()
        parsed_ini: ParsedIni = ParsedIni()

        current_section = None

        for line_id, raw_line in enumerate(ini_lines):
            line = raw_line.strip()
            # Skip empty lines or comments
            if not line or line.startswith(';'):
                continue
            # Handle section line
            if line.startswith('['):
                line_lower = line.lower()
                # Disable ini: rogue d3dx.ini found by keyword
                for keyword in cls.d3dx_ini_keywords:
                    if line_lower.startswith(keyword):
                        result.file_issue = Issue(line_id, f'unwanted d3dx.ini duplicate - detected by `{keyword}`')
                        return result, None
                # Index section
                if line_lower.endswith(']'):
                    section_name = line_lower[1:-1].strip()
                else:
                    section_name = line_lower[1:].strip()
                current_section = parsed_ini.sections.setdefault(section_name, Section(section_name))
                continue
            # Skip options before first section
            if current_section is None:
                continue
            # Extract ini option name and value
            try:
                option_name, option_value = line.split('=', 1)
            except ValueError:
                continue
            option_name = option_name.strip().lower()
            option_value = option_value.strip().lower()
            # Disable ini: rogue d3dx.ini found by option values
            if option_value == cls.d3dx_ini_option_values.get(option_name, None):
                result.file_issue = Issue(line_id, f'unwanted d3dx.ini duplicate - detected by `{option_name}`')
                return result, None
            # Handle CheckTextureOverride
            if option_name == 'checktextureoverride' and option_value:
                # Index slot triggered by CheckTextureOverride
                current_section.triggered_slots.append((line_id, option_value))
                # Comment ini line: CheckTextureOverride triggers slot that's already triggered by Model Importer
                if option_value in cls.unwanted_triggers:
                    result.line_issues[line_id] = Issue(line_id, f'unneeded global trigger for {option_value}')
                continue
            # Index runnable CommandList
            if option_name == 'run' and option_value:
                current_section.command_lists.append(option_value)
                continue

        return result, parsed_ini

    @staticmethod
    def should_exclude(path: Path, patterns: list[str]) -> bool:
        return any(fnmatch.fnmatch(part.lower(), pat.lower()) for part in path.parts for pat in patterns)

    @staticmethod
    def make_backup(file_path: Path, rename: bool = False, dry_run: bool = False, extension: str = '.xxmi_bak') -> Path:
        base_backup = file_path.with_suffix(file_path.suffix + extension)
        backup_path = base_backup
        counter = 1
        while backup_path.exists():
            backup_path = base_backup.with_name(base_backup.stem + f"_{counter}" + base_backup.suffix)
            counter += 1
        if not dry_run:
            if rename:
                file_path.rename(backup_path)
            else:
                shutil.copy(file_path, backup_path)
        return backup_path
