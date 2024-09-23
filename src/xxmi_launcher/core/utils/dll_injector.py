import time
import psutil
import subprocess

import ctypes as ct
import ctypes.wintypes as wt

from typing import List
from pathlib import Path
from pyinjector import inject


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
            raise ValueError(f'Injector file not found: {injector_lib_path}!')

        try:
            lib = ct.cdll.LoadLibrary(str(injector_lib_path))
        except Exception as e:
            raise ValueError(f'Failed to load injector library!') from e

        try:
            lib.HookLibrary.argtypes = (wt.LPCWSTR, ct.POINTER(wt.HHOOK), ct.POINTER(wt.HANDLE))
            lib.HookLibrary.restype = ct.c_int

            lib.WaitForInjection.argtypes = (wt.LPCWSTR, wt.LPCWSTR, ct.c_int)
            lib.WaitForInjection.restype = ct.c_int

            lib.UnhookLibrary.argtypes = (ct.POINTER(wt.HHOOK), ct.POINTER(wt.HANDLE))
            lib.UnhookLibrary.restype = ct.c_int
        except Exception as e:
            raise ValueError(f'Failed to setup injector library!') from e

        return lib

    def unload(self):
        # Define FreeLibrary arg1 type as HMODULE handle (C void * pointer)
        # By default, handle's Python int will be converted to C long and then raise OverflowError when cast as C int
        kernel32 = ct.WinDLL('kernel32', use_last_error=True)
        kernel32.FreeLibrary.argtypes = [wt.HMODULE]
        # Explicitly unload injector dll
        result = kernel32.FreeLibrary(self.lib._handle)
        if result == 0:
            raise ValueError(f'Failed to unload injector library!')

    def hook_library(self, dll_path: Path, target_process: str):
        if self.hook is not None:
            dll_path = self.dll_path
            self.unhook_library()
            raise ValueError(f'Invalid injector usage: {str(dll_path)} was not unhooked!')

        self.dll_path = wt.LPCWSTR(str(dll_path.resolve()))
        self.target_process = wt.LPCWSTR(target_process)
        self.hook = wt.HHOOK()
        self.mutex = wt.HANDLE()

        result = self.lib.HookLibrary(self.dll_path, ct.byref(self.hook), ct.byref(self.mutex))

        if result == 100:
            raise ValueError(f'Another instance of 3DMigotoLoader is running!')
        elif result == 200:
            raise ValueError(f'Failed to load {str(dll_path)}!')
        elif result == 300:
            raise ValueError(f'Library {str(dll_path)} is missing expected entry point!')
        elif result == 400:
            raise ValueError(f'Failed to setup windows hook for {str(dll_path)}!')
        elif result != 0:
            raise ValueError(f'Unknown error while hooking {str(dll_path)}!')
        if not bool(self.hook):
            raise ValueError(f'Hook is NULL for {str(dll_path)}!')

    def wait_for_injection(self, timeout: int = 15) -> bool:
        if self.dll_path is None:
            raise ValueError(f'Invalid injector usage: dll path is not defined!')
        if self.target_process is None:
            raise ValueError(f'Invalid injector usage: target process is not defined!')
        if self.hook is None:
            raise ValueError(f'Invalid injector usage: dll is not hooked!')

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


def direct_inject(dll_paths: List[Path], process_name: str = None, pid: int = None, start_cmd: list = None, work_dir: str = '', timeout: int = 15, creationflags: int = None, use_shell: bool = False):
    if start_cmd:
        subprocess.Popen(start_cmd, cwd=work_dir, creationflags=creationflags, shell=use_shell)

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
                            raise ValueError(f'Failed to inject extra library {dll_path}:\n{str(e)}!\nPlease check Advanced Settings -> Inject Libraries.') from e
                    return process.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        time.sleep(0.1)
