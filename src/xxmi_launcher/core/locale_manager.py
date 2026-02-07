import logging
import tomllib
import random
import locale
import re

from pathlib import Path
from textwrap import dedent
from typing import Optional, Union, List, Dict, BinaryIO
from dataclasses import dataclass

log = logging.getLogger(__name__)


class Default(dict):
    def __missing__(self, key):
        return '{' + key + '}'


FORMATTERS = {}

def formatter(name):
    def deco(fn):
        FORMATTERS[name] = fn
        return fn
    return deco


@formatter('bold')
def fmt_bold(value):
    if isinstance(value, list):
        return [f'**{str(x)}**' for x in value]
    if not isinstance(value, str):
        value = str(value)
    return f'**{value}**'


def list_formatter(value, conjunction):
    if not value:
        return ''
    if not isinstance(value, list):
        return value

    separator = L('locale_list_separator', ', ')
    spacing = L('locale_list_conjunction_spacing', r'\s').replace(r'\s', ' ')
    if len(value) == 1:
        return str(value[0])

    return f'{separator}'.join(map(str, value[:-1])) + spacing + conjunction + spacing + str(value[-1])


@formatter('or_list')
def fmt_or_list(value):
    return list_formatter(value, L('locale_list_conjunction_or', 'or'))


@formatter('and_list')
def fmt_and_list(value):
    return list_formatter(value, L('locale_list_conjunction_and', 'and'))


class LocaleString(str):
    _pattern = re.compile(r"\{(\w+(?::\w+)*)\}")

    def __new__(cls, string, key: str):
        obj = super().__new__(cls, str(string))
        obj.key = key
        return obj

    def format(self, **kwargs) -> 'LocaleString':
        # Extract formatters
        instructions = {}
        template = self._pattern.sub(lambda m: self._replace(m, instructions), self)
        # Apply formatters to kwargs
        formatted_kwargs = kwargs.copy()
        for var, fmts in instructions.items():
            if var in kwargs:
                value = kwargs[var]
                for fmt in fmts:
                    func = FORMATTERS.get(fmt)
                    if func:
                        value = func(value)
                formatted_kwargs[var] = value
        # Replace placeholders in string with formatted vars
        formatted = template.format_map(Default(formatted_kwargs))
        # Return mutated string with same locale key
        return LocaleString(formatted, key=self.key)

    @staticmethod
    def _replace(match, instructions):
        token = match.group(1)
        parts = token.split(':')
        var = parts[0]
        formatters = parts[1:]
        instructions[var] = formatters
        return '{' + var + '}'

    def __repr__(self):
        return f"LocaleString({super().__repr__()}, key={self.key!r})"


class LocaleEngine:
    def __init__(self, locales_path: Path):
        self.locales_path: Path = locales_path
        self.strings: Optional[Dict[str, Union[str, List[str]]]] = None
        self.src_strings: Optional[Dict[str, str]] = None
        self.enable_locale = False

    def load_locale(self, locale_name: str, tag: str = 'loc'):
        if locale_name == 'EN':
            self.enable_locale = False
            return

        self.strings = {}
        self.src_strings = {}

        locale_path = self.locales_path / locale_name

        try:
            for path in sorted(locale_path.iterdir()):
                if not path.is_file() or not path.suffix == '.toml':
                    continue
                self.load_file_strings(path, tag)
        except Exception as e:
            self.enable_locale = False
            raise Exception(f'Failed to load locale: {e}')

        self.enable_locale = True

    def get_string(self, key: str, string: str) -> str:
        string = dedent(string)
        if string.startswith('\n'):
            string = string[1:]
        if string.endswith('\n'):
            string = string[:-1]
        if self.enable_locale:
            string = self.translate(key, string)
        return string

    def translate(self, key: str, string: str) -> str:
        locale_string = self.strings.get(key, None)
        if locale_string is None:
            locale_string = string
        elif string.strip() != self.src_strings.get(key, ''):
            locale_string = string
        elif isinstance(locale_string, list):
            locale_string = random.choice(locale_string)
        return locale_string

    def load_file_strings(self, path: Path, tag: str = 'loc'):
        with open(path, 'rb') as f:
            data = tomllib.load(f)
            for key, locale_strings in data.items():
                loc_string = None
                src_string = None
                alt_strings = None

                try:
                    for loc_tag, loc_line in locale_strings.items():
                        if loc_tag == 'src':
                            src_string = loc_line
                        elif loc_tag == 'loc':
                            loc_string = loc_line
                        elif loc_tag.startswith('alt'):
                            if alt_strings is None:
                                alt_strings = [loc_line]
                            else:
                                alt_strings.append(loc_line)
                        else:
                            raise ValueError(f'Locale key `{key}` has unknown `{loc_tag}` locale string tag!')

                    if loc_string is None:
                        raise ValueError(f'Locale key `{key}` is missing `loc` locale string!')

                    if src_string is None:
                        raise ValueError(f'Locale key `{key}` is missing `src` locale string!')

                except Exception as e:
                    log.error(f'Malformed locale string: {e} in file {path}')
                    continue

                if alt_strings is not None:
                    loc_string = [loc_string] + alt_strings

                if tag == 'loc':
                    self.strings[key] = loc_string
                    self.src_strings[key] = src_string.strip()
                else:
                    self.strings[key] = src_string


@dataclass
class LocaleData:
    name: str
    display_name: str
    keywords: List[str]
    codepage: str


@dataclass
class LocaleIndex:
    locales: Dict[str, LocaleData]

    def get_locale(self, locale_name: str) -> LocaleData:
        return self.locales.get(locale_name, self.get_default_locale())

    @staticmethod
    def get_default_locale() -> LocaleData:
        return LocaleData(
            name="EN",
            display_name="English",
            keywords=["en_US", "English", "USA"],
            codepage="1252",
        )

    def get_names(self) -> List[str]:
        return list(self.locales.keys())

    def get_locales(self) -> List[LocaleData]:
        return list(self.locales.values())

    @classmethod
    def from_toml_file(cls, f: BinaryIO) -> "LocaleIndex":
        data = tomllib.load(f)
        locales = {}
        for name, info in data.items():
            locales[name] = LocaleData(
                name=name,
                display_name=info["display_name"],
                keywords=info["keywords"],
                codepage=info["codepage"]
            )
        if 'EN' not in locales.keys():
            locales['EN'] = cls.get_default_locale()
        return cls(locales=locales)

    @classmethod
    def from_default(cls) -> "LocaleIndex":
        default_locale = cls.get_default_locale()
        return cls(locales={default_locale.name: default_locale})


class LocaleManager:
    def __init__(self):
        self.package_path: Optional[Path] = None
        self.locale_engine: Optional[LocaleEngine] = None
        self.locale_index: Optional[LocaleIndex] = None
        self.active_locale: Optional[LocaleData] = None

    def get_string(self, key: str, string: str) -> 'LocaleString':
        string = self.locale_engine.get_string(key, string)
        # if self.enable_guide_chan:
        #     string = self.guide_chan.get_string(key, string)
        return LocaleString(string, key)

    def get_indexed_names(self) -> List[str]:
        return self.locale_index.get_names()

    def get_indexed_locales(self) -> List[LocaleData]:
        return self.locale_index.get_locales()

    def initialize(self, root_path: Path):
        self.set_root_path(root_path)
        self.load_locale_index()
        self.active_locale = self.locale_index.get_locale('EN')
        detected_locale = self.auto_detect_locale()
        self.set_active_locale(detected_locale, save_to_file=False)

    def auto_detect_locale(self) -> LocaleData:
        # Read last used locale from file
        active_locale = self.read_active_locale()
        if active_locale is not None:
            return active_locale
        # Read current OS locale
        active_locale = self.get_os_locale()
        if active_locale is not None:
            return active_locale
        # Fallback to default EN locale
        return self.locale_index.get_default_locale()

    def set_root_path(self, root_path: Path):
        self.package_path = root_path / 'Locale'
        self.locale_engine = LocaleEngine(self.package_path / 'Strings')

    def load_locale_index(self):
        config_path = self.package_path / 'locale_index.toml'
        try:
            with open(config_path, 'rb') as f:
                self.locale_index = LocaleIndex.from_toml_file(f)
        except Exception as e:
            log.error(f'Failed to load locale index from {config_path}: {str(e)}')
            self.locale_index = LocaleIndex.from_default()

    def read_active_locale(self) -> Optional[LocaleData]:
        config_path = self.package_path / 'active_locale.cfg'
        try:
            with open(config_path, 'r') as f:
                locale_name = f.read().strip()
                return self.locale_index.get_locale(locale_name)
        except Exception as e:
            log.error(f'Failed to read active locale from {config_path}: {str(e)}')
        return None

    def get_os_locale(self) -> Optional[LocaleData]:
        # Read raw locale data
        language, codepage = locale.getlocale()
        # Lookup locale by keywords
        if language:
            for locale_data in self.locale_index.locales.values():
                for keyword in locale_data.keywords:
                    if keyword in language:
                        return locale_data
        # Lookup locale by codepage
        if codepage:
            for locale_data in self.locale_index.locales.values():
                if locale_data.codepage in codepage:
                    return locale_data
        return None

    def load_locale(self, locale_name: str):
        self.locale_engine.load_locale(locale_name)
        # self.guide_chan.load_locale(locale)

    def set_active_locale(self, locale_data: Union[str, LocaleData], save_to_file=True):
        # Get locale by name
        if isinstance(locale_data, str):
            locale_data = self.locale_index.get_locale(locale_data)
        # Make sure locale exists in the index
        locale_name = locale_data.name
        # Skip loading same locale
        if locale_name == self.active_locale.name:
            return
        # Load locale
        self.load_locale(locale_name)
        # Remember loaded locale
        self.active_locale = locale_data
        if save_to_file:
            with open(self.package_path / 'active_locale.cfg', 'w') as f:
                f.write(locale_name)


Locale = LocaleManager()
L = Locale.get_string


def initialize(root_path: Path):
    Locale.initialize(root_path)
