import logging
import time
import psutil
import subprocess

import ctypes as ct
import ctypes.wintypes as wt

from typing import List, Optional
from pathlib import Path
from pyinjector import inject

from core.locale_manager import T


log = logging.getLogger(__name__)


class DllInjector:
    def __init__(self, injector_lib_path):
        self.lib = self.load(Path(injector_lib_path).resolve())
        self.dll_path = None
        self.target_process = None
        self.hook = None
        self.mutex = None

    @staticmethod
    def load(injector_lib_path):
        if not injector_lib_path.exists():
            raise ValueError(T('dll_injector_file_not_found', 'Injector file not found: {}!').format(injector_lib_path))

        try:
            lib = ct.cdll.LoadLibrary(str(injector_lib_path))
        except Exception as e:
            raise ValueError(T('dll_injector_load_failed', 'Failed to load injector library!')) from e

        try:
            lib.HookLibrary.argtypes = (wt.LPCWSTR, ct.POINTER(wt.HHOOK), ct.POINTER(wt.HANDLE))
            lib.HookLibrary.restype = ct.c_int

            lib.WaitForInjection.argtypes = (wt.LPCWSTR, wt.LPCWSTR, ct.c_int)
            lib.WaitForInjection.restype = ct.c_int

            lib.UnhookLibrary.argtypes = (ct.POINTER(wt.HHOOK), ct.POINTER(wt.HANDLE))
            lib.UnhookLibrary.restype = ct.c_int
        except Exception as e:
            raise ValueError(T('dll_injector_setup_failed', 'Failed to setup injector library!')) from e

        return lib

    def unload(self):
        # Define FreeLibrary arg1 type as HMODULE handle (C void * pointer)
        # By default, handle's Python int will be converted to C long and then raise OverflowError when cast as C int
        kernel32 = ct.WinDLL('kernel32', use_last_error=True)
        kernel32.FreeLibrary.argtypes = [wt.HMODULE]
        # Explicitly unload injector dll
        result = kernel32.FreeLibrary(self.lib._handle)
        if result == 0:
            raise ValueError(T('dll_injector_unload_failed', 'Failed to unload injector library!'))

    def start_process(self, exe_path: str, work_dir: Optional[str] = None, start_args: str = ''):
        if work_dir is None:
            work_dir = ''

        result = self.lib.StartProcess(
            wt.LPCWSTR(exe_path),
            wt.LPCWSTR(work_dir),
            wt.LPCWSTR(start_args)
        )

        if result != 0:
            codes = {
                0:	'The operating system is out of memory/resources',
                2:	'File not found',
                3:	'Path not found',
                5:	'Access denied',
                11:	'.exe file is invalid or not a Win32 app',
                26:	'Sharing violation',
                31:	'No application is associated with the file',
                32:	'File association is incomplete',
            }
            error_text = codes.get(result, T('dll_injector_unknown_shell_error', 'Unknown ShellExecute error code {}').format(result))
            raise ValueError(T('dll_injector_failed_to_start', 'Failed to start {}: {}!').format(exe_path.name, error_text))

    def open_process(self,
                     start_method: str,
                     exe_path: Optional[str],
                     work_dir: Optional[str],
                     start_args: Optional[List[str]],
                     process_flags: Optional[int],
                     process_name: Optional[str] = None,
                     dll_paths: Optional[List[Path]] = None,
                     cmd: Optional[str] = None,
                     inject_timeout: int = 15):

        log.debug(f'Starting game process {process_name} using {start_method} method: exe_path={exe_path}, work_dir={work_dir}, start_args={start_args}, process_flags={process_flags}, cmd={cmd}, dll_paths={dll_paths}')

        start_method = start_method.upper()

        # Pyinjector fails with non-ascii paths
        if dll_paths:
            for dll_path in dll_paths:
                try:
                    str(dll_path).encode('ascii')
                except Exception as e:
                    raise ValueError(T('dll_injector_non_ascii_path', 'Please rename all folders from the path using only English letters:\n{}').format(dll_path)) from e

        if start_method == 'NATIVE':
            if cmd is None:
                cmd = [exe_path] + start_args
                use_shell = False
            else:
                use_shell = True
            subprocess.Popen(cmd, creationflags=process_flags, cwd=work_dir, shell=use_shell)

        elif start_method == 'SHELL':
            if cmd is None:
                self.start_process(exe_path, work_dir, ' '.join(start_args))
            else:
                # cmd = ' '.join([f'start \"\" \"{exe_path}\"'] + start_args)
                self.start_process('cmd.exe', None, f'/C "{cmd}"')

        elif start_method == 'MANUAL':
            log.debug(f'Waiting for user to start the game process {process_name}...')

        else:
            raise ValueError(T('dll_injector_unknown_start_method', 'Unknown process start method `{}`!').format(start_method))

        if dll_paths:
            pid = self.inject_libraries(dll_paths, process_name, timeout=inject_timeout)
            if pid == -1:
                raise ValueError(T('dll_injector_injection_failed', 'Failed to inject {}!').format(str(dll_paths)))


    def hook_library(self, dll_path: Path, target_process: str):
        if self.hook is not None:
            dll_path = self.dll_path
            self.unhook_library()
            raise ValueError(T('dll_injector_not_unhooked', 'Invalid injector usage: {} was not unhooked!').format(str(dll_path)))

        self.dll_path = wt.LPCWSTR(str(dll_path.resolve()))
        self.target_process = wt.LPCWSTR(target_process)
        self.hook = wt.HHOOK()
        self.mutex = wt.HANDLE()

        result = self.lib.HookLibrary(self.dll_path, ct.byref(self.hook), ct.byref(self.mutex))

        if result == 100:
            raise ValueError(T('dll_injector_another_instance', 'Another instance of 3DMigotoLoader is running!'))
        elif result == 200:
            raise ValueError(T('dll_injector_failed_to_load_dll', 'Failed to load {}!').format(str(dll_path)))
        elif result == 300:
            raise ValueError(T('dll_injector_missing_entry_point', 'Library {} is missing expected entry point!').format(str(dll_path)))
        elif result == 400:
            raise ValueError(T('dll_injector_hook_setup_failed', 'Failed to setup windows hook for {}!').format(str(dll_path)))
        elif result != 0:
            raise ValueError(T('dll_injector_unknown_hook_error', 'Unknown error while hooking {}!').format(str(dll_path)))
        if not bool(self.hook):
            raise ValueError(T('dll_injector_hook_is_null', 'Hook is NULL for {}!').format(str(dll_path)))

    def wait_for_injection(self, timeout: int = 15) -> bool:
        if self.dll_path is None:
            raise ValueError(T('dll_injector_path_not_defined', 'Invalid injector usage: dll path is not defined!'))
        if self.target_process is None:
            raise ValueError(T('dll_injector_process_not_defined', 'Invalid injector usage: target process is not defined!'))
        if self.hook is None:
            raise ValueError(T('dll_injector_not_hooked', 'Invalid injector usage: dll is not hooked!'))

        result = self.lib.WaitForInjection(self.dll_path, self.target_process, ct.c_int(timeout))

        if result != 0:
            return False
        return True

    def unhook_library(self) -> bool:
        if self.hook is None and self.mutex is None:
            return True
        result = self.lib.UnhookLibrary(ct.byref(self.hook), ct.byref(self.mutex))
        self.dll_path = None
        self.target_process = None
        self.hook = None
        self.mutex = None
        if result != 0:
            return False
        return True

    def inject_libraries(self, dll_paths: List[Path], process_name: str = None, pid: int = None, timeout: int = 15):

        time_start = time.time()

        while True:

            current_time = time.time()

            if timeout != -1 and current_time - time_start >= timeout:
                # Timeout reached, lets signal it with -1 return pid
                return -1

            for process in psutil.process_iter():
                try:
                    if process.name() == process_name or process.pid == pid:
                        for dll_path in dll_paths:
                            try:
                                inject(process.pid, str(dll_path))
                            except Exception as e:
                                raise ValueError(T('dll_injector_extra_library_failed', 'Failed to inject extra library {}:\n{}!\nPlease check Advanced Settings -> Inject Libraries.').format(dll_path, str(e))) from e
                        return process.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            time.sleep(0.1)
