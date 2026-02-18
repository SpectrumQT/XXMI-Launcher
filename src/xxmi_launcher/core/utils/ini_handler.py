import re
import logging

from dataclasses import dataclass, field
from typing import Dict, Union
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class IniHandlerSettings:
    ignore_comments: bool = True
    option_value_spacing: bool = True
    inline_comments: bool = False
    add_section_spacing: bool = False
    right_split: bool = False


class IniHandlerSection:
    def __init__(self, name, comments):
        self.name = name
        self.comments = comments
        self.options = []
        self.modified = False

    def get_option(self, name, cast_type=str):
        for (option_name, option_value, modified, comments, inline_comment) in self.options:
            if option_name.lower() == name.lower():
                if cast_type == str:
                    return str(option_value)
                elif cast_type == int:
                    return int(option_value)
                elif cast_type == float:
                    return float(option_value)
        return None

    def get_option_values(self, name):
        result = {}
        for option_id, (option_name, option_value, modified, comments, inline_comment) in enumerate(self.options):
            if option_name.lower() == name.lower():
                result[option_id] = option_value
        return result

    def set_option(self, name, value, flag_modified=True, overwrite=True, comments=None, inline_comment=None):
        if overwrite:
            for i, (option_name, option_value, modified, default_comments, default_inline_comment) in enumerate(self.options):
                if option_name.lower() == name.lower():
                    if str(value) == option_value:
                        return
                    if comments is not None:
                        default_comments = comments
                    if inline_comment:
                        default_inline_comment = inline_comment
                    if flag_modified and not modified:
                        modified = True
                    self.options[i] = (name, str(value), modified, default_comments, default_inline_comment)
                    if modified:
                        self.modified = True
                    return
            self.options.append((name, str(value), flag_modified, comments, inline_comment))
            if flag_modified:
                self.modified = True
        else:
            self.options.append((name, str(value), flag_modified, comments, inline_comment))
            if flag_modified:
                self.modified = True

    def remove_option(self, name, value=None, not_equal=False):
        if value is None:
            # Filter out all options with given name
            filter_func = lambda option: option[0] != name
        else:
            if not_equal:
                # Filter out all options with given name but different value
                # Useful to make sure that section doesn't contain duplicate options with different values
                filter_func = lambda option: option[0] != name or (option[0] == name and option[1] == str(value))
            else:
                # Filter out all options with given name and same value
                # Useful when ini contains multiple option with same name (deviates from classic format)
                filter_func = lambda option: option[0] != name or (option[0] == name and option[1] != str(value))

        options = list(filter(filter_func, self.options))

        if len(options) != len(self.options):
            self.options = options
            self.modified = True

    def to_string(self, cfg: IniHandlerSettings):
        result = ''
        if self.comments is None:
            result += '\n'
        else:
            for comment in self.comments:
                result += comment
        result += f'[{self.name}]' + '\n'
        for (option_name, option_value, modified, comments, inline_comment) in self.options:
            if comments is not None:
                for comment in comments:
                    result += comment
            if inline_comment:
                option_value += f' ; {inline_comment}'
            if cfg.option_value_spacing:
                result += f'{option_name} = {option_value}' + '\n'
            else:
                result += f'{option_name}={option_value}' + '\n'
        return result

    def __repr__(self):
        return self.name


class IniHandler:
    def __init__(self, cfg: IniHandlerSettings, data):
        self.cfg = cfg
        self.sections = None
        self.footer_comments = []
        if isinstance(data, str):
            data = data.splitlines()
        if isinstance(data, list):
            self.from_text(data)
        else:
            self.from_file(data)
        self.modified = False

    def from_file(self, f):
        self.from_text(f.readlines())

    def from_text(self, lines: list[str]):
        log.debug(f'Parsing ini...')
        section_pattern = re.compile(r'^\[(.+)\]')
        if not self.cfg.right_split:
            option_pattern = re.compile(r'^([\w\.\s$]*)\s*=(?!=)\s*(.+)')
        else:
            option_pattern = re.compile(r'^([\w\.\s$=]*)\s*=(?!=)\s*(.+)')

        self.sections = {}
        current_section = None
        current_comments = []

        for line_id, line in enumerate(lines):
            stripped_line = line.rstrip()

            result = section_pattern.findall(stripped_line)
            if len(result) == 1:
                current_section = self.get_section(result[0])
                if current_section is None:
                    current_section = self.add_section(result[0], comments=current_comments)
                    current_comments = []
                continue

            result = option_pattern.findall(stripped_line)
            if len(result) == 1 and current_section is not None:
                result = result[0]
                if len(result) == 2:
                    option = result[0].rstrip()
                    value = result[1].strip()
                    inline_comment = None
                    if self.cfg.inline_comments:
                        split_pos = value.find(';')
                        if split_pos != -1:
                            inline_comment = value[split_pos+1:].strip()
                            value = value[:split_pos].rstrip()
                    current_section.set_option(option, value, flag_modified=False, overwrite=False,
                                               comments=current_comments, inline_comment=inline_comment)

                    current_comments = []
                continue

            if not self.cfg.ignore_comments:
                current_comments.append(stripped_line + '\n')

        if len(current_comments) > 0:
            self.footer_comments = current_comments

    def add_section(self, name, comments=None):
        section = IniHandlerSection(name, comments)
        self.sections[name.lower()] = section
        return section

    def get_section(self, section):
        return self.sections.get(section.lower(), None)

    def remove_section(self, section):
        del self.sections[section.lower()]
        self.modified = True

    def is_modified(self):
        for section in self.sections.values():
            if section.modified:
                return True
        return self.modified

    def to_string(self):
        result = ''
        for section in self.sections.values():
            result += section.to_string(self.cfg)
            if self.cfg.add_section_spacing:
                result += '\n'
        for comment in self.footer_comments:
            result += comment
        return result

    def set_option(self, section_name, option_name, option_value, modified=True, overwrite=True, comments=None):
        section = self.get_section(section_name)
        if section is None:
            section = self.add_section(section_name)
        section.set_option(option_name, option_value, flag_modified=modified, overwrite=overwrite, comments=comments)

    def remove_option(self, option_name, section_name=None, option_value=None, not_equal=False):
        if section_name:
            section = self.get_section(section_name)
            sections = [section] if section else []
        else:
            sections = self.sections.values()

        for section in sections:
            section.remove_option(option_name, option_value, not_equal)

    def get_option_values(self, option_name, section_name=None):
        if section_name:
            section = self.get_section(section_name)
            if section:
                sections = [section]
            else:
                sections = []
        else:
            sections = self.sections.values()

        result = {}
        for section in sections:
            values = section.get_option_values(option_name)
            if len(values) > 0:
                result[section.name] = values

        return result