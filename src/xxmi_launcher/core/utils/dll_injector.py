import logging
import time
import psutil
import subprocess
import win32api

import ctypes as ct
import ctypes.wintypes as wt

from typing import List, Optional
from pathlib import Path

from core.locale_manager import L


log = logging.getLogger(__name__)


class DllInjector:
    def __init__(self, injector_lib_path):
        self.lib = self.load(Path(injector_lib_path).resolve())
        self.dll_path = None
        self.target_process = None
        self.hook = None
        self.mutex = None

    @staticmethod
    def get_short_path(path: Path) -> str:
        try:
            full_path = str(path.resolve())
            return win32api.GetShortPathName(full_path)
        except Exception as e:
            return str(path.resolve())

    @staticmethod
    def load(injector_lib_path):
        if not injector_lib_path.exists():
            raise ValueError(L('error_dll_injector_file_not_found', 'Injector file not found: {injector_lib_path}!').format(path=injector_lib_path))

        try:
            lib = ct.cdll.LoadLibrary(str(injector_lib_path))
        except Exception as e:
            raise ValueError(L('error_dll_injector_load_failed', 'Failed to load injector library!')) from e

        try:
            lib.HookLibrary.argtypes = (wt.LPCWSTR, ct.POINTER(wt.HHOOK), ct.POINTER(wt.HANDLE))
            lib.HookLibrary.restype = ct.c_int

            lib.WaitForInjection.argtypes = (wt.LPCWSTR, wt.LPCWSTR, ct.c_int)
            lib.WaitForInjection.restype = ct.c_int

            lib.UnhookLibrary.argtypes = (ct.POINTER(wt.HHOOK), ct.POINTER(wt.HANDLE))
            lib.UnhookLibrary.restype = ct.c_int

            lib.Inject.argtypes = (wt.DWORD, wt.LPCWSTR)
            lib.Inject.restype = ct.c_int
        except Exception as e:
            raise ValueError(L('error_dll_injector_setup_failed', 'Failed to setup injector library!')) from e

        return lib

    def unload(self):
        # Define FreeLibrary arg1 type as HMODULE handle (C void * pointer)
        # By default, handle's Python int will be converted to C long and then raise OverflowError when cast as C int
        kernel32 = ct.WinDLL('kernel32', use_last_error=True)
        kernel32.FreeLibrary.argtypes = [wt.HMODULE]
        # Explicitly unload injector dll
        result = kernel32.FreeLibrary(self.lib._handle)
        if result == 0:
            raise ValueError(L('error_dll_injector_unload_failed', 'Failed to unload injector library!'))

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
                0:	L('dll_injector_shell_error_out_of_memory', 'The operating system is out of memory/resources'),
                2:	L('dll_injector_shell_error_file_not_found', 'File not found'),
                3:	L('dll_injector_shell_error_path_not_found', 'Path not found'),
                5:	L('dll_injector_shell_error_access_denied', 'Access denied'),
                11:	L('dll_injector_shell_error_not_win32_app', '.exe file is invalid or not a Win32 app'),
                26:	L('dll_injector_shell_error_sharing_violation', 'Sharing violation'),
                31:	L('dll_injector_shell_error_no_app_association', 'No application is associated with the file'),
                32:	L('dll_injector_shell_error_incomplete_app_association', 'File association is incomplete'),
            }
            error_text = codes.get(result, L('dll_injector_unknown_shell_error_code', 'Unknown ShellExecute error code {error_code}').format(error_code=result))
            raise ValueError(L('error_dll_injector_process_start_failed', 'Failed to start {process_name}: {error_text}!').format(process_name=exe_path.name, error_text=error_text))

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
        # if dll_paths:
            # for dll_path in dll_paths:
                # try:
                    # str(dll_path).encode('ascii')
                # except Exception as e:
                    # raise ValueError(L('error_dll_injector_non_ascii_path', """
                        # Please rename all folders from the path using only English letters:
                        # {dll_path}
                    # """).format(dll_path=dll_path)) from e

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
            raise ValueError(L('error_dll_injector_unknown_start_method', 'Unknown process start method `{start_method}`!').format(start_method=start_method))

        if dll_paths:
            pid = self.inject_libraries(dll_paths, process_name, timeout=inject_timeout)
            if pid == -1:
                raise ValueError(L('error_dll_injector_injection_failed', 'Failed to inject {dll_paths}!').format(dll_paths=str(dll_paths)))


    def hook_library(self, dll_path: Path, target_process: str):
        if self.hook is not None:
            dll_path = self.dll_path
            self.unhook_library()
            raise ValueError(L('error_dll_injector_unhook_failed', 'Invalid injector usage: {dll_path} was not unhooked!').format(dll_path=str(dll_path)))

        self.dll_path = wt.LPCWSTR(str(dll_path.resolve()))
        self.target_process = wt.LPCWSTR(target_process)
        self.hook = wt.HHOOK()
        self.mutex = wt.HANDLE()

        result = self.lib.HookLibrary(self.dll_path, ct.byref(self.hook), ct.byref(self.mutex))

        if result == 100:
            raise ValueError(L('error_dll_injector_another_instance', 'Another instance of 3DMigotoLoader is running!'))
        elif result == 200:
            raise ValueError(L('error_dll_injector_failed_to_load_dll', 'Failed to load {dll_path}!').format(dll_path=str(dll_path)))
        elif result == 300:
            raise ValueError(L('error_dll_injector_missing_entry_point', 'Library {dll_path} is missing expected entry point!').format(dll_path=str(dll_path)))
        elif result == 400:
            raise ValueError(L('error_dll_injector_hook_setup_failed', 'Failed to setup windows hook for {dll_path}!').format(dll_path=str(dll_path)))
        elif result != 0:
            raise ValueError(L('error_dll_injector_unknown_hook_error', 'Unknown error while hooking {dll_path}!').format(dll_path=str(dll_path)))
        if not bool(self.hook):
            raise ValueError(L('error_dll_injector_hook_is_null', 'Hook is NULL for {dll_path}!').format(dll_path=str(dll_path)))

    def wait_for_injection(self, timeout: int = 15) -> bool:
        if self.dll_path is None:
            raise ValueError(L('error_dll_injector_path_not_defined', 'Invalid injector usage: dll path is not defined!'))
        if self.target_process is None:
            raise ValueError(L('error_dll_injector_process_not_defined', 'Invalid injector usage: target process is not defined!'))
        if self.hook is None:
            raise ValueError(L('error_dll_injector_dll_not_hooked', 'Invalid injector usage: dll is not hooked!'))

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
        error_strings = {
            100: 'Process {pid} not found',
            200: 'Failed to allocate memory',
            300: 'Failed to write DLL path to process memory',
            400: 'Failed to create injection thread',
            500: 'Injection thread timed out',
            600: 'DLL injection failed'
        }
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
                            wide_dll_path = wt.LPCWSTR(str(dll_path.resolve()))
                            ret = self.lib.Inject(process.pid, wide_dll_path)
                            if ret != 0:
                                raise ValueError(L('error_dll_injector_extra_library_failed', """
                                    Failed to inject extra library {dll_path}:
                                    {error_text}!
                                    Please check Advanced Settings → Inject Libraries.
                                """).format(dll_path=dll_path, error_text=error_strings[ret].format(pid=process.pid)))
                        return process.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            time.sleep(0.1)
