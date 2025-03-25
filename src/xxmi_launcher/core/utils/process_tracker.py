import time
import psutil
import subprocess

from typing import Tuple
from enum import Enum
from multiprocessing import Process, Value
from pyinjector import inject

import win32gui
import win32process


class ProcessPriority(Enum):
    IDLE_PRIORITY_CLASS = 'Low'
    BELOW_NORMAL_PRIORITY_CLASS = 'Below Normal'
    NORMAL_PRIORITY_CLASS = 'Normal'
    ABOVE_NORMAL_PRIORITY_CLASS = 'Above Normal'
    HIGH_PRIORITY_CLASS = 'High'
    REALTIME_PRIORITY_CLASS = 'Realtime'

    def get_process_flag(self):
        return getattr(subprocess, self.name)


def get_hwnds_for_pid(pid, check_visibility: bool = False):
    def callback(hwnd, hwnds):
        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
        if found_pid == pid:
            if check_visibility and (not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd)):
                return True
            hwnds.append(hwnd)
        return True
    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds


def get_process(process_id=None, process_name=None):
    for process in psutil.process_iter():
        try:
            if process.name() == process_name or process.pid == process_id:
                return process
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None


class WaitResult(Enum):
    Found = 0
    NotFound = -100
    Timeout = -200
    Terminated = -300


def wait_for_process(process_name, timeout=10, with_window=False, cmd=None, inject_dll=None, check_visibility: bool = False) -> Tuple[WaitResult, int]:
    process = ProcessWaiter(process_name, timeout, with_window, cmd=cmd, inject_dll=inject_dll, check_visibility=check_visibility)
    process.start()
    process.join()
    result = int(process.data.value)
    """
    Possible result values:
    0...MAX_PID: exit before timeout with process found
    -200: timeout reached
    """

    if result < 0:
        return WaitResult(result), -1
    else:
        return WaitResult.Found, result


def wait_for_process_exit(process_name, timeout=10, kill_timeout=-1) -> Tuple[WaitResult, int]:
    process = ProcessWaiter(process_name, timeout, wait_exit=True, kill_timeout=kill_timeout)
    process.start()
    process.join()
    result = int(process.data.value)
    """
    Possible result values:
    0...MAX_PID: process exit before timeout
    -100: exit before timeout with process not found
    -200: timeout reached with process alive
    -300: process terminated after kill_timeout
    """

    if result < 0:
        return WaitResult(result), -1
    else:
        return WaitResult.Found, result


class ProcessWaiter(Process):
    """
    Waits for process spawn or exit
    Possible self.data.value returns:
    0...MAX_PID: exit before timeout with process found
    -100: exit before timeout with process not found
    -200: timeout reached
    -300: process terminated after kill_timeout
    """
    def __init__(self, process_name, timeout=-1, with_window=False, wait_exit=False, kill_timeout=-1, cmd=None, inject_dll=None, check_visibility: bool = False):
        Process.__init__(self)
        self.process_name = process_name
        self.timeout = int(timeout)
        self.with_window = with_window
        self.check_visibility = check_visibility
        self.wait_exit = wait_exit
        self.kill_timeout = kill_timeout
        self.cmd = cmd
        self.inject_dll = inject_dll
        self.data = Value('i', -100)

    def run(self):

        if self.cmd:
            subprocess.Popen(self.cmd)

        time_start = time.time()

        while True:

            current_time = time.time()

            if self.timeout != -1 and current_time - time_start >= self.timeout:
                break

            process = get_process(process_name=self.process_name)

            if process is not None:
                # Process is found
                self.data.value = process.pid

                if not self.wait_exit:
                    # We're in wait-for-process-spawn mode
                    if not self.with_window:
                        # Exit loop: process is found and waiting for window is not required
                        if self.inject_dll:
                            inject(process.pid, str(self.inject_dll))
                        return
                    elif len(get_hwnds_for_pid(pid=self.data.value, check_visibility=self.check_visibility)) != 0:
                        # Exit loop: process is found and window is also found
                        if self.inject_dll:
                            inject(process.pid, str(self.inject_dll))
                        return

                # Start process termination attempts once kill_timeout is reached
                if self.kill_timeout != -1 and current_time - time_start >= self.kill_timeout:
                    self.data.value = -300
                    process.kill()

            elif self.wait_exit:
                return

            time.sleep(0.1)

        # Timeout reached, lets signal it with -200 return code
        self.data.value = -200
