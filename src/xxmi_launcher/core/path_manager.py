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
        from core.locale_manager import T
        raise NoWriteAccessError(T('path_manager_remove_readonly_failed', 'Failed to remove Read Only flag from file {}: {}!').format(file_path, str(e)))


def assert_file_read(file_path: Path, absolute=True):
    from core.locale_manager import T
    if not file_path.exists():
        raise FileNotFound(T('path_manager_file_not_exist', "File '{}' does not exist!").format(file_path))
    if not file_path.is_file():
        raise FileNotFileError(T('path_manager_not_a_file', "File '{}' is not a file!").format(file_path))
    if absolute and not file_path.is_absolute():
        raise PathNotAbsoluteError(T('path_manager_path_not_absolute', "File path '{}' is not absolute!").format(file_path))
    if not os.access(file_path, os.R_OK):
        raise NoReadAccessError(T('path_manager_no_read_access', "Failed to read '{}' file!").format(file_path))


def assert_file_write(file_path: Path, absolute=True):
    assert_file_read(file_path, absolute=absolute)
    from core.locale_manager import T
    if is_read_only(file_path):
        raise FileReadOnlyError(T('path_manager_file_readonly', "Failed to write '{}': file is Read Only!").format(file_path))
    if not os.access(file_path, os.W_OK):
        raise NoWriteAccessError(T('path_manager_no_write_access', "Failed to write '{}': no write access!").format(file_path))


def assert_file_run(file_path: Path, absolute=True):
    assert_file_read(file_path, absolute=absolute)
    from core.locale_manager import T
    if not os.access(file_path, os.X_OK):
        raise NoExeAccessError(T('path_manager_no_exe_access', "Failed run '{}': no execute access!").format(file_path))


def assert_path(directory_path: Path):
    if not directory_path.exists():
        return assert_path(directory_path.parent)
    from core.locale_manager import T
    if not directory_path.is_absolute():
        raise ValueError(T('path_manager_dir_not_absolute', "Directory path '{}' is not absolute!").format(directory_path))
    if not os.access(directory_path, os.R_OK):
        raise ValueError(T('path_manager_cant_read_folder', "Can't read from '{}' folder!").format(directory_path))
    if not os.access(directory_path, os.W_OK):
        raise ValueError(T('path_manager_cant_write_folder', "Can't write to '{}' folder!").format(directory_path))
    if not os.access(directory_path, os.X_OK):
        raise ValueError(T('path_manager_cant_run_exe_folder', "Can't run .exe in '{}' folder!").format(directory_path))
    try:
        os.listdir(directory_path)
    except Exception as e:
        raise ValueError(T('path_manager_cant_access_folder', "Can't access '{}' folder!").format(directory_path)) from e


def verify_path(directory_path: Path):
    if not directory_path.exists():
        assert_path(directory_path.parent)
    else:
        if not directory_path.is_dir():
            from core.locale_manager import T
            raise ValueError(T('path_manager_not_a_folder', "Path '{}' is not a folder!").format(directory_path))
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
                from core.locale_manager import T
                raise ValueError(T('path_manager_cannot_set_root_absolute', 'Cannot set root "{}" for absolute path "{}"!').format(root_path, path))

    def verify(self):
        for path in self.__dict__.values():
            verify_path(path)


App = Paths()


def initialize(root_path: Path):
    # Library tkinterweb crashes with { or } chars in the path to tcl
    # Traceback: utilities.py, line 978, in load_tkhtml
    # _tkinter.TclError: missing close-brace
    if '{' in str(root_path) or '}' in str(root_path):
        from core.locale_manager import T
        raise Exception(T('path_manager_curly_brackets_error',
                        'Launcher initialization failed!\n\n'
                        'Curly brackets {{ and }} in launcher path are not supported:\n'
                        '{}\n\n'
                        'Please reinstall the launcher to another location.\n').format(root_path))

    App.set_root_path(root_path)
    App.verify()
