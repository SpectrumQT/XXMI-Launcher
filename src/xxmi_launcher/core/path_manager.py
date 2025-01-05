import os
import stat

from pathlib import Path
from dataclasses import dataclass, fields


class PathNotAbsoluteError(Exception):
    pass


class NoReadAccessError(Exception):
    pass


class NoWriteAccessError(Exception):
    pass


class NoExeAccessError(Exception):
    pass


class FileNotFileError(Exception):
    pass


class FileReadOnlyError(Exception):
    pass


class FileNotFound(Exception):
    pass


def is_read_only(file_path):
    attrs = os.stat(file_path).st_file_attributes
    return attrs & stat.FILE_ATTRIBUTE_READONLY != 0


def remove_read_only(file_path: Path):
    try:
        os.chmod(file_path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
    except Exception as e:
        raise NoWriteAccessError(f'Failed to remove Read Only flag from file {file_path}: {str(e)}!')


def assert_file_read(file_path: Path, absolute=True):
    if not file_path.exists():
        raise FileNotFound(f"File '{file_path}' does not exist!")
    if not file_path.is_file():
        raise FileNotFileError(f"File '{file_path}' is not a file!")
    if absolute and not file_path.is_absolute():
        raise PathNotAbsoluteError(f"File path '{file_path}' is not absolute!")
    if not os.access(file_path, os.R_OK):
        raise NoReadAccessError(f"Failed to read '{file_path}' file!")


def assert_file_write(file_path: Path, absolute=True):
    assert_file_read(file_path, absolute=absolute)
    if is_read_only(file_path):
        raise FileReadOnlyError(f"Failed to write '{file_path}': file is Read Only!")
    if not os.access(file_path, os.W_OK):
        raise NoWriteAccessError(f"Failed to write '{file_path}': no write access!")


def assert_file_run(file_path: Path, absolute=True):
    assert_file_read(file_path, absolute=absolute)
    if not os.access(file_path, os.X_OK):
        raise NoExeAccessError(f"Failed run '{file_path}': no execute access!")


def assert_path(directory_path: Path):
    if not directory_path.exists():
        return assert_path(directory_path.parent)
    if not directory_path.is_absolute():
        raise ValueError(f"Directory path '{directory_path}' is not absolute!")
    if not os.access(directory_path, os.R_OK):
        raise ValueError(f"Can't read from '{directory_path}' folder!")
    if not os.access(directory_path, os.W_OK):
        raise ValueError(f"Can't write to '{directory_path}' folder!")
    if not os.access(directory_path, os.X_OK):
        raise ValueError(f"Can't run .exe in '{directory_path}' folder!")
    try:
        os.listdir(directory_path)
    except Exception as e:
        raise ValueError(f"Can't access '{directory_path}' folder!") from e


def verify_path(directory_path: Path):
    if not directory_path.exists():
        assert_path(directory_path.parent)
    else:
        if not directory_path.is_dir():
            raise ValueError(f"Path '{directory_path}' is not a folder!")
        assert_path(directory_path)
    directory_path.mkdir(parents=True, exist_ok=True)
    assert_path(directory_path)


@dataclass
class Paths:
    Root: Path = Path('')
    Resources: Path = Path('Resources')
    Themes: Path = Path('Themes')
    Backups: Path = Path('Backups')
    Locale: Path = Path('Locale')

    def set_root_path(self, root_path: Path):
        for field in fields(self):
            path = self.__getattribute__(field.name)
            if not path.is_absolute():
                self.__setattr__(field.name, root_path / path)
            else:
                raise ValueError(f'Cannot set root "{root_path}" for absolute path "{path}"!')

    def verify(self):
        for path in self.__dict__.values():
            verify_path(path)


App = Paths()


def initialize(root_path: Path):
    # Library tkinterweb crashes with { or } chars in the path to tcl
    # Traceback: utilities.py, line 978, in load_tkhtml
    # _tkinter.TclError: missing close-brace
    if '{' in str(root_path) or '}' in str(root_path):
        raise Exception(f'Launcher initialization failed!\n\n'
                        f'Curly brackets {{ and }} in launcher path are not supported:\n'
                        f'{root_path}\n\n'
                        f'Please reinstall the launcher to another location.\n')

    App.set_root_path(root_path)
    App.verify()
