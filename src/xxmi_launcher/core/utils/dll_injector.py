import time
import psutil
import subprocess

import ctypes as ct
import ctypes.wintypes as wt

from typing import List
from pathlib import Path
from pyinjector import inject

from core.i18n_manager import I18n, _


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
            raise ValueError(_("errors.injector.not_found").format(injector_lib_path=injector_lib_path))

        try:
            lib = ct.cdll.LoadLibrary(str(injector_lib_path))
        except Exception as e:
            raise ValueError(_("errors.injector.load_failed")) from e

        try:
            lib.HookLibrary.argtypes = (wt.LPCWSTR, ct.POINTER(wt.HHOOK), ct.POINTER(wt.HANDLE))
            lib.HookLibrary.restype = ct.c_int

            lib.WaitForInjection.argtypes = (wt.LPCWSTR, wt.LPCWSTR, ct.c_int)
            lib.WaitForInjection.restype = ct.c_int

            lib.UnhookLibrary.argtypes = (ct.POINTER(wt.HHOOK), ct.POINTER(wt.HANDLE))
            lib.UnhookLibrary.restype = ct.c_int
        except Exception as e:
            raise ValueError(_("errors.injector.setup_failed")) from e

        return lib

    def unload(self):
        # Define FreeLibrary arg1 type as HMODULE handle (C void * pointer)
        # By default, handle's Python int will be converted to C long and then raise OverflowError when cast as C int
        kernel32 = ct.WinDLL('kernel32', use_last_error=True)
        kernel32.FreeLibrary.argtypes = [wt.HMODULE]
        # Explicitly unload injector dll
        result = kernel32.FreeLibrary(self.lib._handle)
        if result == 0:
            raise ValueError(_("errors.injector.unload_failed"))

    def hook_library(self, dll_path: Path, target_process: str):
        if self.hook is not None:
            dll_path = self.dll_path
            self.unhook_library()
            raise ValueError(_("errors.injector.not_unhooked").format(dll_path=dll_path))

        self.dll_path = wt.LPCWSTR(str(dll_path.resolve()))
        self.target_process = wt.LPCWSTR(target_process)
        self.hook = wt.HHOOK()
        self.mutex = wt.HANDLE()

        result = self.lib.HookLibrary(self.dll_path, ct.byref(self.hook), ct.byref(self.mutex))

        if result == 100:
            raise ValueError(_("errors.injector.another_instance"))
        elif result == 200:
            raise ValueError(_("errors.injector.load_dll_failed").format(dll_path=dll_path))
        elif result == 300:
            raise ValueError(_("errors.injector.missing_entry").format(dll_path=dll_path))
        elif result == 400:
            raise ValueError(_("errors.injector.hook_failed").format(dll_path=dll_path))
        elif result != 0:
            raise ValueError(_("errors.injector.unknown_error").format(dll_path=dll_path))
        if not bool(self.hook):
            raise ValueError(_("errors.injector.null_hook").format(dll_path=dll_path))

    def wait_for_injection(self, timeout: int = 15) -> bool:
        if self.dll_path is None:
            raise ValueError(_("errors.injector.no_dll"))
        if self.target_process is None:
            raise ValueError(_("errors.injector.no_process"))
        if self.hook is None:
            raise ValueError(_("errors.injector.not_hooked"))

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
    # Pyinjector fails with non-ascii paths
    for dll_path in dll_paths:
        try:
            str(dll_path).encode('ascii')
        except Exception as e:
            raise ValueError(_("errors.injector.path_english").format(dll_path=dll_path)) from e

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
                            raise ValueError(_("errors.injector.extra_lib").format(dll_path=dll_path, e=e)) from e
                    return process.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        time.sleep(0.1)
