import os
import stat

from pathlib import Path
from dataclasses import dataclass, fields

from core.locale_manager import L


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
        raise NoWriteAccessError(L('error_remove_readonly_failed',
            'Failed to remove Read Only flag from file {path}: {error_text}!'
        ).format(path=file_path, error_text=e))


def set_read_only(file_path: Path):
    try:
        os.chmod(
            file_path,
            stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        )
    except Exception as e:
        raise NoWriteAccessError(L('error_set_readonly_failed',
            'Failed to set Read Only flag on file {path}: {error_text}!'
        ).format(path=file_path, error_text=e))


def assert_file_read(file_path: Path, absolute=True):
    if not file_path.exists():
        raise FileNotFound(L('error_file_not_exist', "File '{path}' does not exist!").format(path=file_path))
    if not file_path.is_file():
        raise FileNotFileError(L('error_not_a_file', "File '{path}' is not a file!").format(path=file_path))
    if absolute and not file_path.is_absolute():
        raise PathNotAbsoluteError(L('error_path_not_absolute', "File path '{path}' is not absolute!").format(path=file_path))
    if not os.access(file_path, os.R_OK):
        raise NoReadAccessError(L('error_no_read_access', "Failed to read '{path}' file!").format(path=file_path))


def assert_file_write(file_path: Path, absolute=True):
    assert_file_read(file_path, absolute=absolute)
    if is_read_only(file_path):
        raise FileReadOnlyError(L('error_file_readonly', "Failed to write '{path}': file is Read Only!").format(path=file_path))
    if not os.access(file_path, os.W_OK):
        raise NoWriteAccessError(L('error_no_write_access', "Failed to write '{path}': no write access!").format(path=file_path))


def assert_file_run(file_path: Path, absolute=True):
    assert_file_read(file_path, absolute=absolute)
    if not os.access(file_path, os.X_OK):
        raise NoExeAccessError(L('error_no_exe_access', "Failed run '{path}': no execute access!").format(path=file_path))


def assert_path(directory_path: Path):
    if not directory_path.exists():
        return assert_path(directory_path.parent)
    if not directory_path.is_absolute():
        raise ValueError(L('error_dir_not_absolute', "Directory path '{path}' is not absolute!").format(path=directory_path))
    if not os.access(directory_path, os.R_OK):
        raise ValueError(L('error_cant_read_folder', "Can't read from '{path}' folder!").format(path=directory_path))
    if not os.access(directory_path, os.W_OK):
        raise ValueError(L('error_cant_write_folder', "Can't write to '{path}' folder!").format(path=directory_path))
    if not os.access(directory_path, os.X_OK):
        raise ValueError(L('error_cant_run_exe_folder', "Can't run .exe in '{path}' folder!").format(path=directory_path))
    try:
        os.listdir(directory_path)
    except Exception as e:
        raise ValueError(L('error_cant_access_folder', "Can't access '{path}' folder!").format(path=directory_path)) from e


def verify_path(directory_path: Path):
    if not directory_path.exists():
        assert_path(directory_path.parent)
    else:
        if not directory_path.is_dir():
            raise ValueError(L('error_not_a_folder', "Path '{path}' is not a folder!").format(path=directory_path))
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
                raise ValueError(L('error_cannot_set_root_absolute',
                    'Cannot set root "{root_path}" for absolute path "{path}"!'
                ).format(root_path=root_path, path=path))

    def verify(self):
        for path in self.__dict__.values():
            verify_path(path)


App = Paths()


def initialize(root_path: Path):
    # Library tkinterweb crashes with { or } chars in the path to tcl
    # Traceback: utilities.py, line 978, in load_tkhtml
    # _tkinter.TclError: missing close-brace
    if '{' in str(root_path) or '}' in str(root_path):
        raise Exception(L('error_curly_brackets_error', """
            Launcher initialization failed!
            
            Curly brackets {{ and }} in launcher path are not supported:
            {root_path}
            
            Please reinstall the launcher to another location.

        """).format(root_path=root_path))

    App.set_root_path(root_path)
    App.verify()
