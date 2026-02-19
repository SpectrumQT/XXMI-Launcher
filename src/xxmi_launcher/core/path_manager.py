import logging
import os
import stat
import time
import errno
import tempfile
import random
import shutil

from pathlib import Path
from dataclasses import dataclass, fields

from core.locale_manager import L

log = logging.getLogger(__name__)


@dataclass
class PathManagerEvents:

    @dataclass
    class VerifyFileAccess:
        path: Path
        abs_path: bool = True
        read: bool = True
        write: bool = False
        exe: bool = False

    @dataclass
    class WriteFile:
        path: Path
        size: int

    @dataclass
    class RemovePath:
        path: Path

    @dataclass
    class RenamePath:
        src_path: Path
        dst_path: Path

    @dataclass
    class CopyFile:
        src_path: Path
        dst_path: Path

    @dataclass
    class CopyDirectory:
        src_path: Path
        dst_path: Path


import core.event_manager as Events


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

    TRANSIENT_ERRNOS = {errno.EACCES, errno.EBUSY, errno.ENOENT, 32, 145}
    CHUNK_SIZE = 8 * 1024 * 1024

    def __post_init__(self):
        Events.Subscribe(PathManagerEvents.VerifyFileAccess, self.handle_verify_file_access)

    def handle_verify_file_access(self, event: PathManagerEvents.VerifyFileAccess):
        if event.read:
            assert_file_read(event.path, absolute=event.abs_path)
        if event.write:
            self.verify_file_write(event.path)
        if event.exe:
            assert_file_read(event.path)

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

    @staticmethod
    def is_subpath(child, parent):
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False

    @classmethod
    def verify_file_write(cls, path: Path | str):
        try:
            assert_file_write(path)
        except FileReadOnlyError:
            user_response = Events.Call(Events.Application.ShowError(
                modal=True,
                title=L('message_title_file_write_failed_read_only', 'File Read Only Error'),
                message=L('message_text_file_write_failed_read_only', """
                    Failed to write Read Only file {path}!

                    Press [Confirm] to remove this flag and continue.
                """).format(path=path),
                confirm_text=L('message_button_remove_flag', 'Remove Flag'),
                cancel_text=L('message_button_abort', 'Abort'),
            ))
            if user_response is True:
                log.debug(f'Removing Read-Only flag from {path}...')
                remove_read_only(path)
                assert_file_write(path)
            else:
                raise ValueError(L('error_critical_file_write_failed', 'Failed to write critical file: {path}!').format(path=path))

    @staticmethod
    def get_free_path(target: Path, id_start: int = 0) -> Path:
        """
        Generate a temporary path based on the target path.

        - For a directory: <target>_0, <target>_1, ...
        - For a file: <parent>/<stem>_0<suffix>, <parent>/<stem>_1<suffix>, ...
        """
        target = Path(target).resolve()
        counter = id_start

        if target.exists():
            while True:
                if target.is_dir() or target.suffix == '':
                    temp_path = target.with_name(f'{target.name}_{counter}')
                else:
                    temp_path = target.with_name(f'{target.stem}_{counter}{target.suffix}')
                if not temp_path.exists():
                    return temp_path
                counter += 1
        else:
            return target

    @classmethod
    def remove_path(
        cls,
        path: Path | str,
        timeout: float = 10.0,
        base_delay: float = 0.001,
        max_delay: float = 0.5,
        ignore_missing: bool = True,
        silent: bool = False,
    ):
        """
        Remove a file or directory with retries on transient errors.
        """
        path = Path(path).resolve()

        if not path.exists():
            if ignore_missing:
                return
            else:
                raise FileNotFoundError(path)

        if not silent:
            Events.Fire(PathManagerEvents.RemovePath(path=path))

        # Calculate IO deadline
        deadline = time.monotonic() + timeout

        # Remove file or directory
        delay = base_delay
        while True:
            try:
                if path.is_file() or path.is_symlink():
                    cls.verify_file_write(path)
                    path.unlink()
                elif path.is_dir():
                    for root, dirs, files in os.walk(path):
                        for f in files:
                            cls.verify_file_write(Path(root) / f)
                    shutil.rmtree(path)
                break
            except (OSError, PermissionError) as e:
                err_no = getattr(e, 'errno', None) or getattr(e, 'winerror', None)
                if err_no not in cls.TRANSIENT_ERRNOS or time.monotonic() > deadline:
                    raise

                # Retry with exponential backoff + jitter
                time.sleep(delay + delay * 0.1 * (2 * random.random() - 1))
                delay = min(delay * 2, max_delay)

    @classmethod
    def rename_path(
        cls,
        src_path: Path | str,
        dst_path: Path | str,
        timeout: float = 10.0,
        base_delay: float = 0.001,
        max_delay: float = 0.5,
        keep_existing_files: bool = True,
        unlink_src_on_fail: bool = False,
        silent: bool = False,
    ):
        """
        Replace dst_path with src_path, with retries on transient errors (AV/OS locks).
        """
        src_path = Path(src_path).resolve()
        dst_path = Path(dst_path).resolve()

        if not silent:
            Events.Fire(PathManagerEvents.RenamePath(src_path=src_path, dst_path=dst_path))

        # Calculate IO deadline
        deadline = time.monotonic() + timeout

        # Handle src_path is inside dst_path (stage src_path externally)
        if src_path.is_dir() and cls.is_subpath(src_path, dst_path):
            staging_root = dst_path.parent
            temp_path = cls.get_free_path(staging_root / f'{dst_path.name}_staging')
            cls.rename_path(src_path, temp_path, silent=True)
            src_path = temp_path

        # Handle existing dst_path dir (including dst_path is inside src_path)
        backup_dir: Path | None = None
        if dst_path.is_dir():
            # Rename exiting dst_path folder to prevent collision with src_path renaming
            backup_dir = cls.get_free_path(dst_path)
            cls.rename_path(dst_path, backup_dir, timeout=timeout, base_delay=base_delay, max_delay=max_delay, silent=silent)

        # Replace existing dst_path with src_path (or just rename)
        delay = base_delay
        while True:
            try:
                # If dst_path exists and is a directory (rare if backup moved it), remove it first
                if dst_path.is_dir():
                    cls.remove_path(dst_path)
                # Replace destination
                os.replace(src_path, dst_path)
                # Merge back missing files if requested
                if keep_existing_files and backup_dir and backup_dir.exists():
                    for root, dirs, files in os.walk(backup_dir):
                        root = Path(root)
                        target_root = dst_path / root.relative_to(backup_dir)
                        # Ensure directories exist
                        target_root.mkdir(parents=True, exist_ok=True)
                        for d in dirs:
                            (target_root / d).mkdir(exist_ok=True)
                        # Move files
                        for file in files:
                            src_file = root / file
                            dst_file = target_root / file
                            if not dst_file.exists():
                                cls.rename_path(src_file, dst_file, silent=silent)
                # If we moved the original dir to backup, remove it now
                if backup_dir and backup_dir.exists():
                    cls.remove_path(backup_dir)
                return
            except (OSError, PermissionError) as e:
                err_no = getattr(e, 'errno', None) or getattr(e, 'winerror', None)
                if err_no not in cls.TRANSIENT_ERRNOS or time.monotonic() > deadline:
                    if unlink_src_on_fail:
                        try:
                            cls.remove_path(src_path)
                        except (OSError, PermissionError):
                            pass
                    raise

                # Retry with exponential backoff + jitter
                time.sleep(delay + delay * 0.1 * (2 * random.random() - 1))
                delay = min(delay * 2, max_delay)

    @staticmethod
    def read_text(file_path: Path | str, encoding: str = 'utf-8') -> str:
        file_path = Path(file_path).resolve()
        assert_file_read(file_path)
        return file_path.read_text(encoding=encoding)

    @staticmethod
    def read_bytes(file_path: Path | str) -> bytes:
        file_path = Path(file_path).resolve()
        assert_file_read(file_path)
        return file_path.read_bytes()

    @classmethod
    def copy_file(cls, src_path: Path | str, dst_path: Path | str, silent: bool = False):
        src_path = Path(src_path).resolve()
        dst_path = Path(dst_path).resolve()
        if not silent:
            Events.Fire(PathManagerEvents.CopyFile(src_path=src_path, dst_path=dst_path))
        cls.write_file(dst_path, src_path, silent=silent)

    @classmethod
    def copy_dir(cls, src_dir: Path | str, dst_dir: Path | str, keep_existing_files: bool = True, silent: bool = False):
        """
        Recursively copy a directory safely using a temporary directory and atomic rename.
        """
        src_dir = Path(src_dir).resolve()
        dst_dir = Path(dst_dir).resolve()

        if not silent:
            Events.Fire(PathManagerEvents.CopyDirectory(src_path=src_dir, dst_path=dst_dir))

        # Create temporary directory for copying
        tmp_dir = cls.get_free_path(dst_dir, id_start=0)

        if not tmp_dir.exists():
            tmp_dir.mkdir(parents=True)

        try:
            # Recursively copy files and subdirectories
            for root, dirs, files in os.walk(src_dir):
                rel_root = Path(root).relative_to(src_dir)
                target_root = tmp_dir / rel_root
                target_root.mkdir(parents=True, exist_ok=True)

                for f in files:
                    src_file = Path(root) / f
                    dst_file = target_root / f
                    cls.copy_file(src_file, dst_file, silent=silent)

            # Rename temporary directory to final destination
            cls.rename_path(tmp_dir, dst_dir, keep_existing_files=keep_existing_files, unlink_src_on_fail=True, silent=silent)

        finally:
            # Cleanup temporary directory if anything remains
            if tmp_dir.exists():
                cls.remove_path(tmp_dir, ignore_missing=True)

    @classmethod
    def write_file(
        cls,
        file_path: Path | str,
        data: str | bytes | bytearray | Path,
        encoding: str = 'utf-8',
        timeout: float = 10.0,
        base_delay: float = 0.001,
        max_delay: float = 0.5,
        silent: bool = False,
    ) -> int:
        """
        Write data to a file with retries on transient errors (AV/OS locks).
        """
        file_path = Path(file_path).resolve()

        if not silent:
            size = len(data) if not isinstance(data, Path) else -1
            Events.Fire(PathManagerEvents.WriteFile(path=file_path, size=size))

        if file_path.is_file():
            cls.verify_file_write(file_path)

        is_binary = isinstance(data, (bytes, bytearray, Path))
        mode = 'wb' if is_binary else 'w'
        written_total = 0

        # Calculate IO deadline
        deadline = time.monotonic() + timeout

        # Create temp file and write data to it
        tmp_path = None
        delay = base_delay
        while True:
            try:
                fd, tmp_name = tempfile.mkstemp(dir=file_path.parent)
                tmp_path = Path(tmp_name)
                with os.fdopen(fd, mode, encoding=encoding if not is_binary else None) as f:
                    # Write bytes/string directly
                    if isinstance(data, (bytes, bytearray, str)):
                        for i in range(0, len(data), cls.CHUNK_SIZE):
                            chunk = data[i:i + cls.CHUNK_SIZE]
                            written_total += f.write(chunk)
                            f.flush()
                            os.fsync(f.fileno())
                    elif isinstance(data, Path):
                        # Chunked read from source file
                        with open(data, 'rb') as fr:
                            while chunk := fr.read(cls.CHUNK_SIZE):
                                written_total += f.write(chunk)
                                f.flush()
                                os.fsync(f.fileno())
                break

            except (OSError, PermissionError) as e:
                if tmp_path and tmp_path.exists():
                    try:
                        os.unlink(tmp_path)
                    except (OSError, PermissionError):
                        pass

                err_no = getattr(e, 'errno', None) or getattr(e, 'winerror', None)
                if err_no not in cls.TRANSIENT_ERRNOS or time.monotonic() > deadline:
                    raise e

                # Retry with exponential backoff + jitter
                time.sleep(delay + delay * 0.1 * (2 * random.random() - 1))
                delay = min(delay * 2, max_delay)

        # Replace existing file with temp file
        remaining_timeout = max(0.0, deadline - time.monotonic())
        cls.rename_path(tmp_path, file_path, remaining_timeout, base_delay, max_delay, unlink_src_on_fail=True, silent=silent)

        return written_total

    @staticmethod
    def is_av_error(e: Exception) -> bool:
        win_err = getattr(e, 'winerror', None)
        err_no = getattr(e, 'errno', None)
        return (
            win_err == 225 or
            err_no in (errno.EACCES, errno.EBUSY, errno.ENOENT, 22, 32, 145) or
            isinstance(e, (PermissionError, FileNotFoundError))
        )

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
