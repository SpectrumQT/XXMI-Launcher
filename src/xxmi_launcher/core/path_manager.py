import os
import stat

from pathlib import Path
from dataclasses import dataclass, fields

from core.i18n_manager import I18n, _


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
        raise NoWriteAccessError(_("errors.path.no_write").format(directory_path=file_path))


def assert_file_read(file_path: Path, absolute=True):
    if not file_path.exists():
        raise FileNotFound(_("errors.path.file_not_found").format(file_path=file_path))
    if not file_path.is_file():
        raise FileNotFileError(_("errors.path.not_file").format(file_path=file_path))
    if absolute and not file_path.is_absolute():
        raise PathNotAbsoluteError(_("errors.path.not_absolute").format(directory_path=file_path))
    if not os.access(file_path, os.R_OK):
        raise NoReadAccessError(_("errors.path.no_read").format(directory_path=file_path))


def assert_file_write(file_path: Path, absolute=True):
    assert_file_read(file_path, absolute=absolute)
    if is_read_only(file_path):
        raise FileReadOnlyError(_("errors.path.file_read_only").format(file_path=file_path))
    if not os.access(file_path, os.W_OK):
        raise NoWriteAccessError(_("errors.path.no_write").format(directory_path=file_path))


def assert_file_run(file_path: Path, absolute=True):
    assert_file_read(file_path, absolute=absolute)
    if not os.access(file_path, os.X_OK):
        raise NoExeAccessError(_("errors.path.no_execute").format(directory_path=file_path))


def assert_path(directory_path: Path):
    if not directory_path.exists():
        return assert_path(directory_path.parent)
    if not directory_path.is_absolute():
        raise ValueError(_("errors.path.not_absolute").format(directory_path=directory_path))
    if not os.access(directory_path, os.R_OK):
        raise ValueError(_("errors.path.no_read").format(directory_path=directory_path))
    if not os.access(directory_path, os.W_OK):
        raise ValueError(_("errors.path.no_write").format(directory_path=directory_path))
    if not os.access(directory_path, os.X_OK):
        raise ValueError(_("errors.path.no_execute").format(directory_path=directory_path))
    try:
        os.listdir(directory_path)
    except Exception as e:
        raise ValueError(_("errors.path.no_access").format(directory_path=directory_path)) from e


def verify_path(directory_path: Path):
    if not directory_path.exists():
        assert_path(directory_path.parent)
    else:
        if not directory_path.is_dir():
            raise ValueError(_("errors.path.not_folder").format(directory_path=directory_path))
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
                raise ValueError(_("errors.path.absolute_root").format(path=path, root_path=root_path))

    def verify(self):
        for path in self.__dict__.values():
            verify_path(path)


App = Paths()


def initialize(root_path: Path):
    # Library tkinterweb crashes with { or } chars in the path to tcl
    # Traceback: utilities.py, line 978, in load_tkhtml
    # _tkinter.TclError: missing close-brace
    if '{' in str(root_path) or '}' in str(root_path):
        raise Exception(_("errors.path.curly_brackets").format(root_path=root_path))

    App.set_root_path(root_path)
    App.verify()
