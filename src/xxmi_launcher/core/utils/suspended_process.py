import subprocess

import ctypes as ct

from ctypes import wintypes
from pathlib import Path
from dataclasses import dataclass


# Win32 process creation constants
CREATE_SUSPENDED = 0x00000004
EXTENDED_STARTUPINFO_PRESENT = 0x00080000

PROC_THREAD_ATTRIBUTE_PARENT_PROCESS = 0x00020000

_kernel32 = ct.WinDLL("kernel32", use_last_error=True)


class _STARTUPINFOW(ct.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ct.POINTER(wintypes.BYTE)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class _STARTUPINFOEXW(ct.Structure):
    _fields_ = [
        ("StartupInfo", _STARTUPINFOW),
        ("lpAttributeList", ct.c_void_p),
    ]


class _PROCESS_INFORMATION(ct.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


_kernel32.InitializeProcThreadAttributeList.argtypes = [
    ct.c_void_p,
    wintypes.DWORD,
    wintypes.DWORD,
    ct.POINTER(ct.c_size_t),
]
_kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL

_kernel32.UpdateProcThreadAttribute.argtypes = [
    ct.c_void_p,
    wintypes.DWORD,
    ct.c_size_t,
    ct.c_void_p,
    ct.c_size_t,
    ct.c_void_p,
    ct.POINTER(ct.c_size_t),
]
_kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL

_kernel32.DeleteProcThreadAttributeList.argtypes = [ct.c_void_p]
_kernel32.DeleteProcThreadAttributeList.restype = None

_kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    ct.c_void_p,
    ct.c_void_p,
    wintypes.BOOL,
    wintypes.DWORD,
    ct.c_void_p,
    wintypes.LPCWSTR,
    ct.c_void_p,
    ct.POINTER(_PROCESS_INFORMATION),
]
_kernel32.CreateProcessW.restype = wintypes.BOOL

_kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
_kernel32.ResumeThread.restype = wintypes.DWORD

_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL


def _raise_win32_error(message: str) -> None:
    error = ct.get_last_error()
    description = ct.FormatError(error).strip()
    raise OSError(error, f"{message}: {description}")


@dataclass
class SuspendedProcess:
    pid: int
    process_handle: int | None
    thread_handle: int | None

    def resume(self) -> int:
        """Resume the primary thread by decrementing its suspend count."""
        if self.thread_handle is None:
            raise RuntimeError("The primary-thread handle is no longer available")

        previous_count = int(_kernel32.ResumeThread(wintypes.HANDLE(self.thread_handle)))

        if previous_count == 0xFFFFFFFF:
            _raise_win32_error("Could not resume the process thread")

        # A previous count of 1 means the thread is now runnable.
        # If the count was greater than 1, another resume may be needed.
        if previous_count <= 1:
            self._close_thread_handle()

        return previous_count

    def _close_thread_handle(self) -> None:
        if self.thread_handle is not None:
            _kernel32.CloseHandle(wintypes.HANDLE(self.thread_handle))
            self.thread_handle = None

    def close(self) -> None:
        """Close the handles owned by this launch result."""
        self._close_thread_handle()

        if self.process_handle is not None:
            _kernel32.CloseHandle(wintypes.HANDLE(self.process_handle))
            self.process_handle = None


def create_suspended_with_parent(
    executable: Path,
    arguments: list[str],
    parent_handle: int,
    work_dir: Path | None,
    process_flags: int,
) -> SuspendedProcess:
    if not parent_handle:
        raise ValueError("parent_handle must be a valid process handle")

    size = ct.c_size_t()

    # First call queries the required attribute-list size.
    _kernel32.InitializeProcThreadAttributeList(None, 1, 0, ct.byref(size))

    if not size.value:
        _raise_win32_error("Could not determine the attribute-list size")

    storage = ct.create_string_buffer(size.value)
    attributes = ct.cast(storage, ct.c_void_p)

    if not _kernel32.InitializeProcThreadAttributeList(attributes, 1, 0, ct.byref(size)):
        _raise_win32_error("Could not initialize the attribute list")

    try:
        parent = wintypes.HANDLE(parent_handle)

        if not _kernel32.UpdateProcThreadAttribute(
            attributes,
            0,
            PROC_THREAD_ATTRIBUTE_PARENT_PROCESS,
            ct.cast(ct.byref(parent), ct.c_void_p),
            ct.sizeof(parent),
            None,
            None,
        ):
            _raise_win32_error("Could not set the parent process")

        startup = _STARTUPINFOEXW()
        startup.StartupInfo.cb = ct.sizeof(startup)
        startup.lpAttributeList = attributes

        process_info = _PROCESS_INFORMATION()

        # Build a writable, correctly quoted Windows command line.
        command = ct.create_unicode_buffer(
            subprocess.list2cmdline([str(executable), *arguments])
        )

        flags = (
            CREATE_SUSPENDED
            | subprocess.CREATE_NO_WINDOW
            | EXTENDED_STARTUPINFO_PRESENT
            | int(process_flags or 0)
        )

        success = _kernel32.CreateProcessW(
            str(executable),
            ct.cast(command, wintypes.LPWSTR),
            None,
            None,
            False,  # Do not inherit handles.
            flags,
            None,
            str(work_dir or executable.parent),
            ct.cast(ct.byref(startup), ct.c_void_p),
            ct.byref(process_info),
        )

        if not success:
            _raise_win32_error(f"Could not create {executable.name} with the requested parent")

        return SuspendedProcess(
            pid=int(process_info.dwProcessId),
            process_handle=int(process_info.hProcess),
            thread_handle=int(process_info.hThread),
        )

    finally:
        _kernel32.DeleteProcThreadAttributeList(attributes)
