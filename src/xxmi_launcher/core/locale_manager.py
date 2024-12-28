import tomllib
import random

from textwrap import dedent
from pathlib import Path
from typing import Optional, Dict, Callable

import core.path_manager as Paths


class Default(dict):
    def __missing__(self, key):
        return '{'+key+'}'


class LocaleString:
    def __init__(self, string):
        self.string = str(string)

    def format(self, **kwargs) -> 'LocaleString':
        self.string = self.string.format_map(Default(kwargs))
        return self

    def __str__(self):
        return self.string


class LocaleEngine:
    def __init__(self, locales_path: Path):
        self.locales_path = locales_path
        self.strings : Optional[Dict[str, str]] = None
        self.enable_locale = False

    def load_locale(self, locale: str, tag: str = 'loc'):
        self.strings = {}

        locale_path = self.locales_path / locale

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
        self.locale = LocaleEngine(Paths.App.Resources / 'Packages' / 'Locale' / 'Strings')
        # self.guide_chan = GuideChan(Paths.App.Resources / 'Packages' / 'Locale' / 'GuideChan')
        # self.enable_guide_chan = False

        # self.load_locale('English')

    def load_locale(self, locale: str):
        self.locale.load_locale(locale)
        # self.guide_chan.load_locale(locale)

    def get_string(self, key: str, string: str) -> 'LocaleString':
        string = self.locale.get_string(key, string)
        # if self.enable_guide_chan:
        #     string = self.guide_chan.get_string(key, string)
        return LocaleString(string)


Locale = LocaleManager()

L = Locale.get_string
