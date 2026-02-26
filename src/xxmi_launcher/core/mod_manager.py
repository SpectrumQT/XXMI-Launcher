
import logging
import json
import fnmatch
import re
import os

from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.locale_manager import L

log = logging.getLogger(__name__)


@dataclass
class Section:
    name: str
    command_lists: list[str] = field(default_factory=list)
    triggered_slots: list[tuple[int, str]] = field(default_factory=list)


class IssueType(Enum):
    RogueIni = 'RogueIni'
    UnwantedFile = 'UnwantedFile'
    UnwantedTrigger = 'UnwantedTrigger'
    GlobalTrigger = 'GlobalTrigger'


@dataclass(frozen=True)
class Issue:
    line_id: int
    type: IssueType
    reason: str


@dataclass
class ValidationResult:
    file_issue: Issue | None = None
    line_issues: dict[int, Issue] = field(default_factory=dict)


@dataclass
class ParsedIni:
    ini_lines: list[str] = field(default_factory=list)
    sections: dict[str, Section] = field(default_factory=dict)


class IniValidatorCache:
    def __init__(self):
        self.file_path: Path | None = None
        self.modified: bool = False
        self.data: dict[str, float] = {}

    def reset(self):
        self.data = {}

    def get_mod_time(self, path: Path):
        return self.data.get(str(path.resolve()), None)

    def add_path(self, path: Path):
        resolved_path = str(path.resolve())
        self.data[resolved_path] = path.stat().st_mtime
        self.modified = True

    def remove_path(self, path: Path):
        resolved_path = str(path.resolve())
        if resolved_path not in self.data.keys():
            return
        del self.data[resolved_path]
        self.modified = True

    def load(self, mods_path: Path, cache_path: Path | None = None):
        self.file_path = cache_path or mods_path

        if self.file_path.suffix != '.json':
            self.file_path /= 'ini_validator_cache.json'

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
            Paths.App.write_file(self.file_path, json.dumps(self.data, indent=2))


@dataclass
class IniValidator:
    folder_path: Path
    # GLOB patterns from d3dx.ini
    exclude_patterns: list[str] = field(default_factory=list)
    # Known filenames we always want disabled
    unwanted_files: dict[str, set[str]] = field(default_factory=set)
    # Resource slots we don't want ever see CheckTextureOverride for
    unwanted_triggers: set[str] = field(default_factory=set)
    # Common sections used for d3dx.ini detection
    d3dx_ini_keywords: set[str] = field(default_factory=set)
    # Common option values used for d3dx.ini detection
    d3dx_ini_option_values: dict[str, dict[str, str]] = field(default_factory=dict)
    # Controls whether validator stores paths to processed ini files mod time to skip them on subsequent runs
    use_cache: bool = False
    # Controls whether validator uses existing cache from file or new one
    new_cache: bool = False,
    # Cache path (default it is folder_path/ini_validator_cache.json)
    cache_path: Path | None = None

    cache: IniValidatorCache | None = field(init=False, default=None)

    def __post_init__(self):
        if self.use_cache:
            self.cache = IniValidatorCache()

    def validate_folder(self) -> dict[Path, tuple[ValidationResult, ParsedIni | None]]:
        # Load list of already processed files to avoid scanning them (if cache is enabled)
        self.load_cache()

        validation_results = {}

        unwanted_files = self.unwanted_files.get('*', [])

        ini_files = [Path(root) / file
                     for root, dirs, files in os.walk(self.folder_path, followlinks=True)
                     for file in files if file.endswith('.ini')]

        for path in ini_files:
            # Exclude paths that are configured to be ignored by DLL
            if self.exclude_patterns:
                if self.should_exclude(path.relative_to(self.folder_path), self.exclude_patterns):
                    continue

            # Skip unchanged files found in the cache
            if self.is_path_in_cache(path):
                # log.debug(f'Skipped already processed file sanitizing: {path}')
                continue

            # Mark file as unwanted by filename
            path_name = path.name.lower()
            unwanted_folder_files = self.unwanted_files.get(path.parent.name.lower(), None)
            if path_name in unwanted_files or unwanted_folder_files and path_name in unwanted_folder_files:
                validation_result = ValidationResult()
                validation_result.file_issue = Issue(0, IssueType.UnwantedFile, f'unwanted {path.name}')
                validation_results[path] = (validation_result, None)
                # Update cache with current modification time
                self.add_path_to_cache(path)
                continue

            # Read ini and analyze its behavior
            try:
                ini_lines = Paths.App.read_text(path).splitlines()
                validation_result, parsed_ini = self.validate_ini(ini_lines)
                if validation_result.file_issue or validation_result.line_issues:
                    validation_results[path] = (validation_result, parsed_ini)
            except Exception:
                log.exception(f'Failed to validate {path}')
            finally:
                # Update cache with current modification time
                self.add_path_to_cache(path)

        return validation_results

    def validate_ini(self, ini_lines: list[str]) -> tuple[ValidationResult, ParsedIni | None]:

        # Run basic validation pass (which doesn't involve section references handling)
        validation_result, parsed_ini = self.validate_ini_text(ini_lines)

        # Ini disable pending, no need to dig deeper
        if validation_result.file_issue:
            return validation_result, None

        # Detect global Shader RegEx based triggers
        for section_name, section in parsed_ini.sections.items():
            if section_name.startswith('shaderregex'):
                # Allow global triggers for Shader RegEx with patterns
                pattern = parsed_ini.sections.get(f'{section_name}.pattern', None)
                if pattern:
                    continue
                # Comment global triggers defined directly in Shader RegEx section
                for (line_id, triggered_slot) in section.triggered_slots:
                    validation_result.line_issues[line_id] = Issue(line_id, IssueType.GlobalTrigger, f'forbidden global trigger for {triggered_slot} in [{section_name}]')
                # Comment global triggers defined in CommandLists called by Shader RegEx section
                for command_list_name in section.command_lists:
                    command_list = parsed_ini.sections.get(command_list_name, None)
                    if command_list is None:
                        continue
                    for (line_id, triggered_slot) in command_list.triggered_slots:
                        validation_result.line_issues[line_id] = Issue(line_id, IssueType.GlobalTrigger, f'forbidden global trigger for {triggered_slot} in [{section_name}]/[{command_list_name}]')

        # Destroy ParsedIni object if no line issues detected
        if not validation_result.line_issues:
            return validation_result, None

        return validation_result, parsed_ini

    def validate_ini_text(self, ini_lines: list[str]) -> tuple[ValidationResult, ParsedIni | None]:

        result: ValidationResult = ValidationResult()
        parsed_ini: ParsedIni = ParsedIni(ini_lines=ini_lines)

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
                for keyword in self.d3dx_ini_keywords:
                    if line_lower.startswith(keyword):
                        result.file_issue = Issue(line_id, IssueType.RogueIni, f'unwanted d3dx.ini duplicate - detected by `{keyword}`')
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
            section_options = self.d3dx_ini_option_values.get(current_section.name, None)
            if section_options and option_value == section_options.get(option_name, None):
                result.file_issue = Issue(line_id, IssueType.RogueIni, f'unwanted d3dx.ini duplicate - detected by `{option_name}`')
                return result, None
            # Handle CheckTextureOverride
            if option_name == 'checktextureoverride' and option_value:
                # Index slot triggered by CheckTextureOverride
                current_section.triggered_slots.append((line_id, option_value))
                # Comment ini line: CheckTextureOverride triggers slot that's already triggered by Model Importer
                if option_value in self.unwanted_triggers:
                    result.line_issues[line_id] = Issue(line_id, IssueType.UnwantedTrigger, option_value)
                continue
            # Index runnable CommandList
            if option_name == 'run' and option_value:
                current_section.command_lists.append(option_value)
                continue

        return result, parsed_ini

    @staticmethod
    def should_exclude(path: Path, patterns: list[str]) -> bool:
        return any(fnmatch.fnmatch(part.lower(), pat.lower()) for part in path.parts for pat in patterns)

    def index_namespaces(self, folder_path: Path):
        log.debug(f'Indexing namespaces for {folder_path}...')
        namespace_pattern = re.compile(r'namespace\s*=\s*(.*)')
        namespaces: dict[str, list[Path]] = {}

        for path in folder_path.rglob('*.ini'):
            # Exclude paths that are configured to be ignored by DLL
            if self.exclude_patterns:
                if self.should_exclude(path.relative_to(folder_path), self.exclude_patterns):
                    continue

            try:
                ini_lines = Paths.App.read_text(path).splitlines()
                for line_id, line in enumerate(ini_lines):
                    stripped_line = line.strip().lower()
                    if not stripped_line:
                        continue
                    if stripped_line[0] == ';':
                        continue
                    result = namespace_pattern.findall(stripped_line)
                    if len(result) == 1:
                        namespace = result[0]
                        known_namespace = namespaces.get(namespace, None)
                        if known_namespace:
                            known_namespace.append(path)
                        else:
                            namespaces[namespace] = [path]
                        break
            except Exception as e:
                pass

        return namespaces

    def load_cache(self):
        if self.use_cache and not self.new_cache:
            self.cache.load(self.folder_path, self.cache_path)

    def reset_cache(self):
        if self.use_cache:
            self.cache.reset()

    def is_path_in_cache(self, path: Path):
        if not self.use_cache:
            return False
        else:
            file_mod_time = path.stat().st_mtime
            cache_mod_time = self.cache.get_mod_time(path)
            return cache_mod_time == file_mod_time

    def add_path_to_cache(self, path: Path):
        if self.use_cache:
            self.cache.add_path(path)

    def remove_path_from_cache(self, path: Path):
        if self.use_cache:
            self.cache.remove_path(path)

    def save_cache(self):
        if self.use_cache:
            self.cache.save()


@dataclass
class Mod:
    name: str
    path: Path
    ini_paths: list[Path]

    def disable(self, reason: str, dry_run = True):
        dry_prefix = '[DRY]: ' if dry_run else ''
        new_path = self.path.parent / f'DISABLED_{self.path.name}'
        log.info(f'{dry_prefix}Disabled mod {self.path.name} (reason: {reason}), new path: {new_path} ')
        if not dry_run:
            if not self.path.is_symlink():
                Paths.App.rename_path(self.path, Paths.App.get_free_path(new_path))
            else:
                for ini_path in self.ini_paths:
                    new_path = ini_path.parent / f'DISABLED_{ini_path.name}'
                    Paths.App.rename_path(ini_path, Paths.App.get_free_path(new_path))


    def __hash__(self):
        return hash(self.path)


@dataclass
class OptimizationResults:
    disabled_mods_count: int = 0
    disabled_files_count: int = 0
    edited_files_count: int = 0
    edited_lines_count: int = 0


class ModManager:
    ini_validator: IniValidator | None

    def optimize_shaderfixes_folder(
            self,
            shaderfixes_path: Path,
            exclude_patterns: list[str] | None = None,
            dry_run: bool = True,
    ) -> OptimizationResults:
        dry_prefix = '[DRY]: ' if dry_run else ''

        Paths.verify_path(shaderfixes_path)

        self.ini_validator = IniValidator(folder_path=shaderfixes_path, exclude_patterns=exclude_patterns)
        self.ini_validator.unwanted_files = {'*': {'3dvision2sbs.ini', 'help.ini', 'mouse.ini', 'upscale.ini'}}

        validation_results = self.ini_validator.validate_folder()

        disabled_files_count = 0
        for ini_path, (validation_result, parsed_ini) in validation_results.items():
            # Handle global ini issue
            if validation_result.file_issue:
                if validation_result.file_issue.type == IssueType.UnwantedFile:
                    # Disable any ini with unhandled issue
                    if not dry_run:
                        self.disable_ini(ini_path)
                    disabled_files_count += 1
                    log.info(f'{dry_prefix}Disabled {ini_path.relative_to(shaderfixes_path.parent)} (reason: unwanted file)')
                continue

        return OptimizationResults(disabled_files_count=disabled_files_count)

    def optimize_mods_folder(
            self,
            mods_path: Path,
            cache_path: Path | None = None,
            dry_run: bool = True,
            use_cache: bool = True,
            reset_cache: bool = False,
            exclude_patterns: list[str] | None = None,
        ) -> OptimizationResults:
        """Shutdown the worst ini offenders in Mods folder.

        Quite often, due to lack of knowledge (or infrastructure), modders ship unwanted ini files with their mods.
        Those files have extremely negative impact on performance and stability, and here we:
        1. Disable all rogue d3dx.ini files (should never be present in Mods folder).
        2. Disable all VSCheck.ini files (they trigger ib, already done by EFMI).
        3. Comment out all CheckTextureOverride for ib or vb0 in any section (already done by WWMI/EFMI).
        4. Comment out all ShaderRegex sections running global CheckTextureOverride (FPS killers).
        """
        dry_prefix = '[DRY]: ' if dry_run else ''

        Paths.verify_path(mods_path)

        if Config.Launcher.active_importer in ['GIMI']:
            libs_path = Config.Active.Importer.importer_path / 'Core' / 'GIMI' / 'Libraries'
            self.disable_duplicate_libraries(libs_path, mods_path, exclude_patterns, dry_run)

        self.ini_validator = IniValidator(
            folder_path=mods_path,
            exclude_patterns=exclude_patterns,
            use_cache=True,
            new_cache=reset_cache,
            cache_path=cache_path
        )

        self.ini_validator.d3dx_ini_keywords = {'[loader', '[system', '[stereo', '[commandlistunbindallrendertargets'}
        self.ini_validator.d3dx_ini_option_values = {'include': {'include_recursive': 'mods', 'exclude_recursive': 'disabled*'}}

        if Config.Launcher.active_importer in ['WWMI', 'EFMI']:
            self.ini_validator.unwanted_triggers = {'ib', 'vb0'}

        self.ini_validator.unwanted_files = {'shaderfixes': {'3dvision2sbs.ini', 'help.ini', 'mouse.ini', 'upscale.ini'}}

        if Config.Launcher.active_importer == 'EFMI':
            self.ini_validator.unwanted_files['*'] = {'vscheck.ini'}

        validation_results = self.ini_validator.validate_folder()

        rogue_ini_issues = {}
        global_trigger_results = {}

        pending_ini_disables = {}

        edited_ini_count = 0
        edited_lines_count = 0
        for ini_path, (validation_result, parsed_ini) in validation_results.items():

            # Handle global ini issue
            if validation_result.file_issue:
                if validation_result.file_issue.type == IssueType.RogueIni:
                    # Add rogue d3dx.ini to the dict for user notification
                    rogue_ini_issues[ini_path] = validation_result.file_issue
                else:
                    # Disable any ini with unhandled issue
                    pending_ini_disables[ini_path] = validation_result.file_issue
                continue

            # Handle issues in ini lines (logic)
            if validation_result.line_issues:
                auto_fix_lines_issues = []
                unhandled_issues = []

                for issue in validation_result.line_issues.values():
                    if issue.type == IssueType.UnwantedTrigger:
                        # Add line with unwanted trigger to auto-resolve list
                        auto_fix_lines_issues.append(issue)
                    else:
                        # Add line to the list of unhandled issues
                        unhandled_issues.append(issue)

                # Added ini to the dict for user notification
                if any(issue.type == IssueType.GlobalTrigger for issue in unhandled_issues):
                    global_trigger_results[ini_path] = validation_result

                # Automatically resolve ini line issues from the list
                if auto_fix_lines_issues:
                    try:
                        self.sanitize_ini(mods_path, ini_path, auto_fix_lines_issues, parsed_ini, dry_run)
                        edited_ini_count += 1
                        edited_lines_count += len(auto_fix_lines_issues)
                    except Exception:
                        log.exception(f'Failed to sanitize {ini_path}')

        # Handle rogue d3dx.ini files based on user input
        if rogue_ini_issues:
            pending_d3dx_ini_disable = self.show_rogue_ini_notification(rogue_ini_issues, mods_path)
            if pending_d3dx_ini_disable:
                # User selected "Disable Ini Files"
                pending_ini_disables.update(rogue_ini_issues)
            else:
                # User selected "Abort" or closed the message via [X] button
                for ini_path in rogue_ini_issues.keys():
                    self.ini_validator.remove_path_from_cache(ini_path)
                raise ValueError(L('error_cannot_start_with_d3dx_ini_in_mods', 'Cannot start with d3dx.ini in Mods folder!'))

        # Process pending ini files disables
        for ini_path, file_issue in pending_ini_disables.items():
            if not dry_run:
                self.disable_ini(ini_path)
            log.info(f'{dry_prefix}Disabled {ini_path.relative_to(mods_path.parent)} (reason: {file_issue.reason})')
            continue

        # Handle ini files with global triggers based on user input
        disabled_mods_count = 0
        if global_trigger_results:
            user_response, pending_mod_disables = self.show_global_trigger_notification(global_trigger_results, mods_path)
            # User closed the message via close button [X] (no clear decision was made)
            if user_response is None:
                # Remove ini files with global triggers from the cache (so this message will be shown again next time)
                for ini_path in global_trigger_results.keys():
                    self.ini_validator.remove_path_from_cache(ini_path)
            # User selected "Disable Selected"
            elif user_response is True:
                # Disable mods from the list
                for mod in pending_mod_disables:
                    mod.disable(reason='user choice', dry_run=dry_run)
                disabled_mods_count = len(pending_mod_disables)
            # User selected "Ignore"
            else:
                # No further action required, paths are cached and won't be processed again unless files change
                pass

        if use_cache:
            self.ini_validator.save_cache()

        return OptimizationResults(
            disabled_files_count=len(pending_ini_disables),
            disabled_mods_count=disabled_mods_count,
            edited_files_count=edited_ini_count,
            edited_lines_count=edited_lines_count,
        )

    def show_rogue_ini_notification(self, rogue_ini_issues: dict[Path, Issue], mods_path: Path) -> bool:
        ini_paths = {ini_path: ini_path.relative_to(mods_path.parent) for ini_path in rogue_ini_issues.keys()}
        mod_list = self.build_mod_list(list(ini_paths.values()), mods_path)

        def get_mod_by_ini_path(mods: dict[str, Mod], path: Path) -> Mod | None:
            path = mods_path.parent / path
            for mod in mods.values():
                if path in mod.ini_paths:
                    return mod
            return None

        mod_list_entries = {}
        for ini_path in ini_paths.values():
            mod = get_mod_by_ini_path(mod_list, ini_path)
            entry = f'- {mod.path.name}: <span class="gray">({ini_path})</span>'
            mod_list_entries[mod.name] = entry
        mod_list_entries = dict(sorted(mod_list_entries.items()))

        user_response = Events.Call(Events.Application.ShowWarning(
            modal=True,
            title=L('message_title_rogue_ini_notification', 'Stability Warning'),
            message=L('message_text_rogue_ini_in_mods_detected', """
                Detected mods with ini files containing **d3dx.ini**-exclusive options:

                {mod_list}

                Listed files [usually cause]({link_wiki_d3dx_ini_shipping}) silent errors, glitches and crashes.
            """).format(
                mod_list='\n'.join(mod_list_entries.values()),
                link_wiki_d3dx_ini_shipping='https://github.com/SpectrumQT/XXMI-Libs-Package/wiki/Bad-Modding-Practices#shipping-a-mod-with-d3dxini-included',
            ),
            confirm_text=L('message_button_disable_ini_files', 'Disable Ini Files'),
            cancel_text=L('message_button_abort', 'Abort'),
        ))

        return user_response

    def show_global_trigger_notification(
            self,
            global_trigger_results: dict[Path, ValidationResult],
            mods_path: Path
    ) -> tuple[bool | None, list[Mod] | None]:

        @dataclass
        class PerformanceImpact:
            label: str
            max_triggers: int
            color: str

        def get_impact_text(triggers_count: int):
            impact_table = [
                PerformanceImpact('Light', 2, 'green'),
                PerformanceImpact('Medium', 5, 'yellow'),
                PerformanceImpact('Heavy', 15, 'orange'),
                PerformanceImpact('Severe', 20, 'red'),
                PerformanceImpact('FATAL', 9000, 'dark_red'),
            ]
            triggers_impact = impact_table[-1]
            for impact in impact_table:
                if triggers_count <= impact.max_triggers:
                    triggers_impact = impact
                    break
            return f'<span class="{triggers_impact.color}">{triggers_impact.label}</span>'

        ini_paths = {ini_path: ini_path.relative_to(mods_path.parent) for ini_path in global_trigger_results.keys()}
        mod_list = self.build_mod_list(list(ini_paths.values()), mods_path)

        trigger_counts = {}
        for mod_name, mod in mod_list.items():
            triggers_count = 0
            for ini_path in mod.ini_paths:
                validation_result: ValidationResult = global_trigger_results[ini_path]
                for line_issue in validation_result.line_issues.values():
                    if line_issue.type == IssueType.GlobalTrigger:
                        triggers_count += 1
            trigger_counts[mod] = triggers_count

        trigger_counts = dict(sorted(trigger_counts.items(), key=lambda x: x[1], reverse=True))

        checkbox_options = []
        for mod, triggers_count in trigger_counts.items():
            txt = f'{mod.name}: {get_impact_text(triggers_count)} <span class="gray">({mod.path.relative_to(mods_path.parent)})</span>'
            checkbox_options.append((True, txt))

        user_response, selected_options = Events.Call(Events.Application.ShowWarning(
            modal=True,
            title=L('message_title_performance_notification', 'Performance Notification'),
            message=L('message_text_global_triggers_in_mods_detected', """
                Detected mods with notable global performance impact:
                
                {checkbox_widget}
        
                Listed mods are using [unlimited resource slot triggers]({link_wiki_global_triggers_usage}).
            """).format(
                link_wiki_global_triggers_usage='https://github.com/SpectrumQT/XXMI-Libs-Package/wiki/Bad-Modding-Practices#improper-usage-of-global-checktextureoverride',
            ),
            checkbox_options=checkbox_options,
            confirm_text=L('message_button_disable_selected', 'Disable Selected'),
            cancel_text=L('message_button_ignore', 'Ignore'),
        ))

        disable_mods_list = []

        if user_response is True:
            disable_mods_list = [mod for mod, should_disable in zip(trigger_counts.keys(), selected_options) if should_disable]

        return user_response, disable_mods_list

    def sanitize_ini(
        self,
        mods_path: Path,
        ini_path: Path,
        line_issues: list[Issue],
        parsed_ini: ParsedIni,
        dry_run: bool = False
    ):
        dry_prefix = '[DRY]: ' if dry_run else ''
        log.info(f'{dry_prefix}Replacing {len(line_issues)} lines in {ini_path.relative_to(mods_path.parent)}...')
        # Comment ini lines with issues
        for issue in line_issues:
            line = parsed_ini.ini_lines[issue.line_id]
            if line.strip().startswith(';'):
                continue
            indent = line[:len(line) - len(line.lstrip())]
            if issue.reason == 'ib' and Config.Launcher.active_importer == 'WWMI':
                fixed_line = r"$\WWMIv1\enable_ib_callbacks = 1"
            else:
                fixed_line = ';' + line.strip()
            log.info(f'    - Line #{issue.line_id+1} `{line.strip()}` with `{fixed_line}` (reason: {issue.reason})')
            parsed_ini.ini_lines[issue.line_id] = indent + fixed_line
        # Write ini with commented ini lines with issues
        if not dry_run:
            self.make_backup(ini_path)
            Paths.App.write_file(ini_path, '\n'.join(parsed_ini.ini_lines))
        # Update validator cache
        self.ini_validator.add_path_to_cache(ini_path)

    def disable_duplicate_libraries(
        self,
        libs_path: Path,
        mods_path: Path,
        exclude_patterns: list[str] | None = None,
        dry_run: bool = True,
    ):
        self.ini_validator = IniValidator(
            folder_path=mods_path,
            exclude_patterns=exclude_patterns,
        )
        mods_namespaces = self.ini_validator.index_namespaces(mods_path)
        packaged_namespaces = self.ini_validator.index_namespaces(libs_path)

        duplicate_ini_paths = []
        for mods_namespace, ini_paths in mods_namespaces.items():
            if mods_namespace in packaged_namespaces.keys():
                for ini_path in ini_paths:
                    duplicate_ini_paths.append(ini_path)

        if len(duplicate_ini_paths) == 0:
            return

        user_requested_disable = self.show_duplicate_libraries_notification(duplicate_ini_paths, mods_path)

        if not user_requested_disable:
            return

        for ini_path in duplicate_ini_paths:
            if not dry_run:
                self.disable_ini(ini_path)

    def show_duplicate_libraries_notification(
        self,
        duplicate_ini_paths: list[Path],
        mods_path: Path,
    ) -> bool | None:

        user_response = Events.Call(Events.Application.ShowError(
            modal=True,
            message=L('message_text_duplicate_libraries_detected', """
                Your Mods folder contains some libraries that are already included into {importer}!

                Would you like to disable following duplicates automatically (recommended)?

                {duplicates}
            """).format(
                importer=Config.Launcher.active_importer,
                duplicates='\n'.join([f'- {x.relative_to(mods_path.parent)}' for x in duplicate_ini_paths]
            )),
            confirm_text=L('message_button_disable', 'Disable'),
            cancel_text=L('message_button_ignore', 'Ignore'),
        ))

        return user_response

    @staticmethod
    def build_mod_list(ini_paths: list[Path], mods_path: Path) -> dict[str, Mod]:
        mods: dict[str, Mod] = {}
        grouped = defaultdict(list)

        # Ini files directly under Mods → standalone mods
        for p in ini_paths:
            if p.parent.name == "Mods":
                mods[p.stem] = Mod(
                    name=p.stem,
                    path=mods_path.parent / p,
                    ini_paths=[p]
                )
            else:
                # First folder after 'Mods' for grouping
                grouped[p.parts[1]].append(p)

        # Resolve grouped mods
        result = {}
        for root_name, paths in grouped.items():
            key = root_name
            if key in mods:
                i = 2
                while f"{key}_{i}" in mods or f"{key}_{i}" in result:
                    i += 1
                key = f"{key}_{i}"

            # Mod.path is parent of the shortest ini path
            shortest_ini = min(paths, key=lambda p: len(p.parts))
            mod_path = shortest_ini.parent

            result[key] = Mod(
                name=key,
                path=mods_path.parent / mod_path,
                ini_paths=paths
            )

        # Merge standalone mods
        result.update(mods)

        # Make ini paths absolute
        for mod in result.values():
            mod.ini_paths = [mods_path.parent / ini_path for ini_path in mod.ini_paths]

        return result

    @staticmethod
    def disable_ini(ini_path: Path) -> Path:
        disabled_ini_path = ini_path.parent / f'DISABLED_{ini_path.name}'
        disabled_ini_path = Paths.App.get_free_path(disabled_ini_path)
        Paths.App.rename_path(ini_path, disabled_ini_path)
        return disabled_ini_path

    @staticmethod
    def make_backup(file_path: Path, extension: str = '.xxmi_bak') -> Path:
        backup_path = Paths.App.get_free_path(file_path.with_suffix(file_path.suffix + extension))
        Paths.App.copy_file(file_path, backup_path)
        return backup_path
