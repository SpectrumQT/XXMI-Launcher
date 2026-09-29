import logging
import subprocess
import time
import shlex
import psutil
import win32gui
import win32process
import ctypes as ct

from enum import Enum
from dataclasses import dataclass, replace
from pathlib import Path

from core.locale_manager import L

from core.config.enums import StartMethod, ProcessPriority


log = logging.getLogger(__name__)


class ProcessPriorityClass(Enum):
    IDLE_PRIORITY_CLASS = ProcessPriority.LOW
    BELOW_NORMAL_PRIORITY_CLASS = ProcessPriority.BELOW_NORMAL
    NORMAL_PRIORITY_CLASS = ProcessPriority.NORMAL
    ABOVE_NORMAL_PRIORITY_CLASS = ProcessPriority.ABOVE_NORMAL
    HIGH_PRIORITY_CLASS = ProcessPriority.HIGH
    # REALTIME_PRIORITY_CLASS =

    def get_process_flag(self):
        return getattr(subprocess, self.name)


@dataclass
class ExecutableLaunch:
    exe_path: Path
    cmd_args: str


@dataclass
class CommandLaunch:
    process_name: str
    cmd: str


@dataclass
class LaunchContext:
    start_method: StartMethod
    target: ExecutableLaunch | CommandLaunch
    work_dir: Path | None = None
    process_flags: int | None = None

    @property
    def target_process_name(self) -> str:
        if isinstance(self.target, ExecutableLaunch):
            return self.target.exe_path.name
        return self.target.process_name


class ProcessManager:
    """
    Generic Windows process manager.

    Launching is described by LaunchContext:
      - NATIVE + ExecutableLaunch -> subprocess.Popen()
      - NATIVE + CommandLaunch    -> subprocess.Popen(..., shell=True)
      - SHELL  + ExecutableLaunch -> ShellExecuteW()
      - SHELL  + CommandLaunch    -> cmd.exe through ShellExecuteW()

    Process identification is separate from launching:
      - Native launches are tracked by PID when possible.
      - Shell launches fall back to executable-name lookup.
    """

    def __init__(
        self,
        executable_or_context: Path | LaunchContext,
    ):
        if isinstance(executable_or_context, LaunchContext):
            self.launch_context = executable_or_context
        else:
            self.launch_context = LaunchContext(
                start_method=StartMethod.NATIVE,
                target=ExecutableLaunch(
                    exe_path=Path(executable_or_context),
                    cmd_args="",
                ),
            )

        # Set when this manager starts a process itself.
        self._process: psutil.Process | None = None

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    @property
    def executable(self) -> Path | None:
        """
        Return the executable path when the launch target is ExecutableLaunch.

        Returns None for CommandLaunch.
        """
        target = self.launch_context.target

        if isinstance(target, ExecutableLaunch):
            return target.exe_path

        return None

    def is_running(self) -> bool:
        """
        Return True if the configured process is currently running.

        A process started by this manager is checked directly using its psutil.Process instance.
        Otherwise, fall back to searching for a process with the configured executable name.
        """
        return self._find_process() is not None

    def wait_until_running(
        self,
        timeout: float = 30.0,
        interval: float = 0.25,
        wait_for_window: bool = False,
    ) -> bool:
        """
        Wait until the process is running.

        Args:
            timeout: Maximum time to wait.
            interval: Polling interval.
            wait_for_window: If True, also wait until the process has a visible top-level window.

        Returns:
            True if the process starts and (optionally) its window becomes visible within the timeout, otherwise False.
        """
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            process = self._find_process()
            if process is not None:
                if not wait_for_window or self._has_visible_window(process):
                    return True

            time.sleep(interval)

        # Perform one final check in case the process started immediately after the last polling iteration.
        return self.is_running()

    def wait_until_stopped(
        self,
        timeout: float = 30.0,
        interval: float = 0.25,
    ) -> bool:
        """
        Wait until the process has stopped.

        Args:
            timeout: Maximum time to wait.
            interval: Polling interval.

        If the process was started by this manager, use psutil's native wait() instead of repeatedly polling.

        For externally started processes, fall back to polling by name.

        Returns:
            True if the process stops within the timeout, otherwise False.
        """
        process = self._managed_process()

        if process is not None:
            try:
                # psutil can wait directly for a process that we know about.
                process.wait(timeout=timeout)
                self._process = None
                return True
            except psutil.TimeoutExpired:
                return False

        # We don't own this process, so we don't have a Process instance that we can reliably wait on.
        # Poll for it disappearing instead.
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if not self.is_running():
                return True

            time.sleep(interval)

        return not self.is_running()

    def start(
        self,
        args: str | None = None,
        *,
        wait: bool = True,
        timeout: float = 30.0,
        check_running: bool = True,
    ) -> bool:
        """
        Start the configured LaunchContext.

        Args:
            Optional replacement arguments.

            This is supported only for ExecutableLaunch. 
            For CommandLaunch, the command string is already fully specified by the context.

            args: Optional command-line arguments.
            wait: Whether to wait for the process to appear.
            timeout: Maximum time to wait for the process to start.
            check_running: Whether to return early if the executable is already running.

        Returns:
            True if the process is running, or was started successfully when wait=False.
        """
        if check_running and self.is_running():
            return True

        context = self.launch_context

        # Preserve the old ProcessManager.start(args=[...]) API.
        if args is not None:
            if not isinstance(context.target, ExecutableLaunch):
                raise ValueError("args cannot be supplied when LaunchContext uses CommandLaunch")

            context = replace(context, target=replace(context.target, cmd_args=args))

        log.debug(f"Starting process: args={args}, wait={wait}, timeout={timeout}, check_running={check_running}, context={context}")

        process = self._launch(context)

        # Native subprocess launches give us a PID directly.
        #
        # ShellExecuteW does not, so shell launches intentionally leave
        # _process unset and use process-name discovery instead.
        if process is not None:
            self._process = psutil.Process(process.pid)

        if not wait:
            return True

        return self.wait_until_running(timeout)

    def stop(
        self,
        *,
        timeout: float = 30.0,
    ) -> bool:
        """
        Forcefully terminate the process.

        For applications that provide a graceful shutdown mechanism (such as Steam), use stop_with_args() instead.

        Note that name-based discovery can match another instance with the same executable name.

        Returns:
            True if the process is stopped within the timeout.
        """
        log.debug(f"Stopping process: timeout={timeout}, context={self.launch_context}")

        process = self._find_process()

        if process is None:
            self._process = None
            return True

        try:
            process.kill()
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            # The process exited between _find_process() and kill().
            self._process = None
            return True
        except psutil.AccessDenied:
            # We found the process but do not have permission to terminate it.
            return False

        # For a process started by this manager, this uses psutil.wait().
        # For an externally discovered process, it falls back to polling.
        stopped = self.wait_until_stopped(timeout)

        if stopped:
            self._process = None

        return stopped

    def stop_with_args(
        self,
        args: str | None = None,
        *,
        timeout: float = 30.0,
    ) -> bool:
        """
        Ask an executable to terminate using command-line arguments.

        This requires ExecutableLaunch because there must be a concrete executable to invoke.

        Example:
            steam.stop_with_args(["-shutdown"])

        Returns:
            True if the process terminates within the timeout.
        """
        log.debug(f"Stopping process: timeout={timeout}, args={args}, context={self.launch_context}")

        if self.executable is None:
            raise ValueError("stop_with_args() requires LaunchContext to use ExecutableLaunch" )

        if not self.is_running():
            return True

        if args:
            args = " " + args.strip()

        subprocess.run(
            str(self.executable) + args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )

        return self.wait_until_stopped(timeout)

    def restart(
        self,
        args: str | None = None,
        *,
        stop_args: str | None = None,
        timeout: float = 30.0,
    ) -> bool:
        """
        Restart the configured process.

        Args:
            args: Arguments passed to the process when starting it.
            stop_args: Optional arguments used for graceful shutdown.
            timeout: Maximum time allowed for stopping and starting.
        """
        if stop_args is not None:
            if not self.stop_with_args(stop_args, timeout=timeout):
                return False
        else:
            if not self.stop(timeout=timeout):
                return False

        return self.start(
            args,
            timeout=timeout,
        )

    # -------------------------------------------------------------------------
    # Launching
    # -------------------------------------------------------------------------

    def _launch(
        self,
        context: LaunchContext,
    ) -> subprocess.Popen | None:
        """
        Execute the supplied LaunchContext.

        Returns:
            subprocess.Popen for native launches.
            None for ShellExecuteW launches.
        """
        flags = context.process_flags or 0

        match context.start_method, context.target:
            case StartMethod.NATIVE, ExecutableLaunch() as target:
                return subprocess.Popen(
                    [str(target.exe_path), *shlex.split(target.cmd_args)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=flags,
                    cwd=context.work_dir,
                )

            case StartMethod.NATIVE, CommandLaunch() as target:
                return subprocess.Popen(
                    target.cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=flags,
                    cwd=context.work_dir,
                    shell=True,
                )

            case StartMethod.SHELL, ExecutableLaunch() as target:
                if flags:
                    raise ValueError("process_flags are not supported with StartMethod.SHELL")

                self._shell_execute(
                    exe_path=str(target.exe_path),
                    work_dir=str(context.work_dir),
                    start_args=target.cmd_args,
                )
                return None

            case StartMethod.SHELL, CommandLaunch() as target:
                if flags:
                    raise ValueError("process_flags are not supported with StartMethod.SHELL")

                self._shell_execute(
                    exe_path="cmd.exe",
                    work_dir=str(context.work_dir),
                    start_args=f'/D /S /C "{target.cmd}"',
                )
                return None

            case _:
                raise ValueError(f"Unsupported LaunchContext: {context!r}")

    @staticmethod
    def _shell_execute(
        exe_path: str,
        work_dir: str | None,
        start_args: str = "",
    ) -> None:
        """
        Launch a process through Windows ShellExecuteW.

        ShellExecuteW succeeds when its return value is > 32.
        Values 0..32 are failure codes.
        """
        result = ct.windll.shell32.ShellExecuteW(
            None,
            "open",
            exe_path,
            start_args,
            work_dir or "",
            1,  # SW_SHOWNORMAL
        )

        if result <= 32:
            codes = {
                0: L('dll_injector_shell_error_out_of_memory', 'The operating system is out of memory/resources'),
                2: L('dll_injector_shell_error_file_not_found', 'File not found'),
                3: L('dll_injector_shell_error_path_not_found', 'Path not found'),
                5: L('dll_injector_shell_error_access_denied', 'Access denied'),
                11: L('dll_injector_shell_error_not_win32_app', '.exe file is invalid or not a Win32 app'),
                26: L('dll_injector_shell_error_sharing_violation', 'Sharing violation'),
                31: L('dll_injector_shell_error_no_app_association', 'No application is associated with the file'),
                32: L('dll_injector_shell_error_incomplete_app_association', 'File association is incomplete'),
            }

            error_text = codes.get(result, f"Unknown ShellExecute error code {result}")

            raise ValueError(f"Failed to start {Path(exe_path).name}: {error_text}!")

    # -------------------------------------------------------------------------
    # Process lookup
    # -------------------------------------------------------------------------

    def _managed_process(self) -> psutil.Process | None:
        """
        Return the process started natively by this manager if it is still alive.

        This is the fast path.

        The cached psutil.Process object is checked with is_running() rather than assuming that the PID is still valid.
        This prevents a stale process reference from being treated as alive.
        """

        process = self._process

        if process is None:
            return None

        try:
            if process.is_running():
                return process
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

        # The process has exited or can no longer be inspected.
        self._process = None

        return None

    def _find_process(self) -> psutil.Process | None:
        """
        Find the process managed by this instance.

        Native processes started by this manager use the cached PID first.
        Otherwise, fall back to executable-name lookup.
        """

        # Fast path:
        # We started this process ourselves, so there is no reason to scan every process on the system.
        process = self._managed_process()

        if process is not None:
            return process

        # Fallback:
        # The application may have already been running before this manager was created,
        # so locate it by executable name.
        for process in psutil.process_iter(["name"]):
            try:
                if process.info["name"] == self.launch_context.target_process_name:
                    return process
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Processes can disappear between process_iter() and accessing
                # their information. Ignore those processes and continue.
                continue

        return None

    @staticmethod
    def _has_visible_window(process: psutil.Process) -> bool:
        """
        Return True when the process owns at least one visible top-level window.
        """
        try:
            return len(ProcessManager._get_hwnds_for_pid(process.pid, True)) > 0

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

    @staticmethod
    def _get_hwnds_for_pid(pid, check_visibility=False):

        def callback(hwnd, hwnds):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)

            if found_pid != pid:
                return True

            if check_visibility:
                if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
                    return True

            hwnds.append(hwnd)
            return True

        hwnds = []
        win32gui.EnumWindows(callback, hwnds)

        return hwnds