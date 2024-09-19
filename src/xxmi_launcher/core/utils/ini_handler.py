import re
import logging

from dataclasses import dataclass, field
from typing import Dict, Union

log = logging.getLogger(__name__)

@dataclass
class IniHandlerSettings:
    ignore_comments: bool = True
    option_value_spacing: bool = True


class IniHandlerSection:
    def __init__(self, name, comments):
        self.name = name
        self.comments = comments
        self.options = []
        self.modified = False

    def get_option(self, name, cast_type=str):
        for (option_name, option_value, modified, comments) in self.options:
            if option_name.lower() == name.lower():
                if cast_type == str:
                    return str(option_value)
                elif cast_type == int:
                    return int(option_value)
                elif cast_type == float:
                    return float(option_value)
        return None

    def set_option(self, name, value, flag_modified=True, overwrite=True, comments=None):
        if overwrite:
            for i, (option_name, option_value, modified, default_comments) in enumerate(self.options):
                if option_name.lower() == name.lower():
                    if str(value) == option_value:
                        return
                    if comments is not None:
                        default_comments = comments
                    if flag_modified and not modified:
                        modified = True
                    self.options[i] = (name, str(value), modified, default_comments)
                    if modified:
                        self.modified = True
                    return
            self.options.append((name, str(value), flag_modified, comments))
            if flag_modified:
                self.modified = True
        else:
            self.options.append((name, str(value), flag_modified, comments))
            if flag_modified:
                self.modified = True

    def to_string(self, cfg: IniHandlerSettings):
        result = ''
        if self.comments is None:
            result += '\n'
        else:
            for comment in self.comments:
                result += comment
        result += f'[{self.name}]' + '\n'
        for (option_name, option_value, modified, comments) in self.options:
            if comments is not None:
                for comment in comments:
                    result += comment
            if cfg.option_value_spacing:
                result += f'{option_name} = {option_value}' + '\n'
            else:
                result += f'{option_name}={option_value}' + '\n'
        return result

    def __repr__(self):
        return self.name


class IniHandler:
    def __init__(self, cfg: IniHandlerSettings, f):
        self.cfg = cfg
        self.sections = None
        self.footer_comments = []
        self.from_file(f)

    def from_file(self, f):
        log.debug(f'Parsing ini...')
        section_pattern = re.compile(r'^\[(.+)\]')
        option_pattern = re.compile(r'^([\w\.\s$]*)\s*=(?!=)\s*(.+)')

        self.sections = {}
        current_section = None
        current_comments = []

        for line_id, line in enumerate(f.readlines()):
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
                    current_section.set_option(result[0].rstrip(), result[1].strip(), flag_modified=False, overwrite=False, comments=current_comments)
                    current_comments = []
                continue

            if not self.cfg.ignore_comments:
                current_comments.append(line)

        if len(current_comments) > 0:
            self.footer_comments = current_comments

    def add_section(self, name, comments=None):
        section = IniHandlerSection(name, comments)
        self.sections[name.lower()] = section
        return section

    def get_section(self, section):
        return self.sections.get(section.lower(), None)

    def is_modified(self):
        for section in self.sections.values():
            if section.modified:
                return True
        return False

    def to_string(self):
        result = ''
        for section in self.sections.values():
            result += section.to_string(self.cfg)
        for comment in self.footer_comments:
            result += comment
        return result

    def set_option(self, section_name, option_name, option_value, modified=True, overwrite=True, comments=None):
        section = self.get_section(section_name)
        if section is None:
            section = self.add_section(section_name)
        section.set_option(option_name, option_value, flag_modified=modified, overwrite=overwrite, comments=comments)
