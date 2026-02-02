import tomllib
import random
import locale

from pathlib import Path
from textwrap import dedent
from typing import Optional, Dict, Callable
from enum import Enum


class LocaleName(Enum):
    EN = 'English'
    CN = '中文'
    RU = 'Русский'


def get_os_locale() -> LocaleName:
    language, codepage = locale.getlocale()

    if language:
        keywords = {
            LocaleName.CN: ['zh_CN', 'Chinese', 'China'],
            LocaleName.RU: ['ru_RU', 'Russian', 'Russia'],
        }
        for locale_name, locale_keywords in keywords.items():
            for locale_keyword in locale_keywords:
                if locale_keyword in language:
                    return locale_name

    if codepage:
        codepages = {
            LocaleName.CN: '936',
            LocaleName.RU: '1252',
        }
        for locale_name, locale_codepage in codepages.items():
            if locale_codepage in codepage:
                return locale_name

    return LocaleName.EN


class Default(dict):
    def __missing__(self, key):
        return '{'+key+'}'


class LocaleString(str):
    def __new__(cls, string, key: str):
        obj = super().__new__(cls, str(string))
        obj.key = key
        return obj

    def format(self, **kwargs) -> 'LocaleString':
        formatted = self.format_map(Default(kwargs))
        return LocaleString(formatted, key=self.key)

    def __repr__(self):
        return f"LocaleString({super().__repr__()}, key={self.key!r})"


class LocaleEngine:
    def __init__(self, locales_path: Path):
        self.locales_path = locales_path
        self.strings : Optional[Dict[str, str]] = None
        self.enable_locale = False

    def load_locale(self, locale: LocaleName, tag: str = 'loc'):
        if locale == LocaleName.EN:
            self.enable_locale = False
            return

        self.strings = {}

        locale_path = self.locales_path / locale.name

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
        elif isinstance(locale_string, list):
            locale_string = random.choice(locale_string)
        return locale_string

    def load_file_strings(self, path: Path, tag: str = 'loc'):
        with open(path, 'rb') as f:
            data = tomllib.load(f)

            for key, locale in data.items():

                loc_string = None
                src_string = None
                alt_strings = None

                for loc_tag, loc_line in locale.items():
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
                        raise Exception(f'Locale key `{key}` has unknown `{loc_tag}` locale string tag!')

                if loc_string is None:
                    raise Exception(f'Locale key `{key}` is missing `loc` locale string!')

                if src_string is None:
                    raise Exception(f'Locale key `{key}` is missing `src` locale string!')

                if alt_strings is not None:
                    loc_string = [loc_string] + alt_strings

                if tag == 'loc':
                    self.strings[key] = loc_string
                else:
                    self.strings[key] = src_string

    def validate_locale(self, source_locale: 'LocaleEngine'):
        # Load source strings from current locale
        src_lines_locale = LocaleEngine(self.locales_path)
        src_lines_locale.load_locale('src')
        # Check if all original source keys exist in current locale
        for key in source_locale.strings.keys():
            string = self.strings.get(key, None)
            if string is None:
                raise Exception()
        # Check if all english strings in current locale are equal to original english locale
        for key, string in self.strings.items():
            if string != src_lines_locale.strings[key]:
                raise Exception()


class GuideChan:
    def __init__(self, locales_path: Path):
        self.locales_path = locales_path
        self.locale = LocaleEngine(locales_path)
        self.load_locale('English')

    def load_locale(self, locale: str):
        self.locale.load_locale(locale, 'loc')

    def get_string(self, key: str, string: str) -> str:
        txt = self.locale.get_string(key, '')
        if not txt:
            return string
        if string.find('{guide_chan}') != -1:
            return string.replace('{guide_chan}', txt)
        else:
            return txt + '\n' + string

    # def validate_locale(self):
    #     self.locale.validate_locale(Paths.App.Resources / 'Packages' / 'Locale' / 'GuideChan')


class LocaleManager:
    def __init__(self):
        self.package_path = None
        self.locale = None
        self.active_locale = LocaleName.EN
        # self.guide_chan = GuideChan(Paths.App.Resources / 'Packages' / 'Locale' / 'GuideChan')
        # self.enable_guide_chan = False

    def set_root_path(self, root_path: Path):
        self.package_path = root_path / 'Resources' / 'Packages' / 'Locale'
        self.locale = LocaleEngine(self.package_path / 'Strings')

    def read_active_locale(self) -> Optional[LocaleName]:
        try:
            with open(self.package_path / 'active_locale.cfg', 'r') as f:
                locale = f.read()
                for lang in LocaleName:
                    if lang.name == locale:
                        return lang
        except:
            pass
        return None

    def set_active_locale(self, locale: LocaleName, save_to_file = True):
        if locale == self.active_locale:
            return
        if save_to_file:
            with open(self.package_path / 'active_locale.cfg', 'w') as f:
                f.write(locale.name)
        self.load_locale(locale)
        self.active_locale = locale

    def load_locale(self, locale: LocaleName):
        self.locale.load_locale(locale)
        # self.guide_chan.load_locale(locale)

    def get_string(self, key: str, string: str) -> 'LocaleString':
        string = self.locale.get_string(key, string)
        # if self.enable_guide_chan:
        #     string = self.guide_chan.get_string(key, string)
        return LocaleString(string, key)


Locale = LocaleManager()

L = Locale.get_string


def initialize(root_path: Path):
    Locale.set_root_path(root_path)
    active_locale = Locale.read_active_locale()
    if active_locale is None:
        active_locale = get_os_locale()
    Locale.set_active_locale(active_locale, save_to_file=False)
