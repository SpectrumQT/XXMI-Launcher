import subprocess
import time
import psutil

from pathlib import Path


class ProcessManager:
    """
    Generic Windows process manager.

    Processes can be identified by executable name.
    Processes started through this manager are additionally tracked by their PID using psutil,
    allowing subsequent operations to use a fast path without scanning all processes.

    Example:
        manager = ProcessManager(Path("steam.exe"))

        manager.start()
        manager.stop()
    """

    def __init__(self, executable: Path):
        self.executable = executable
        self.process_name = executable.name

        # Set when this manager starts a process itself.
        #
        # Keeping the psutil.Process instance gives us a fast path for is_running(), stop(), and wait_until_stopped().
        self._process: psutil.Process | None = None

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def is_running(self) -> bool:
        """
        Return True if the process is currently running.

        A process started by this manager is checked directly using its psutil.Process instance.
        Otherwise, fall back to searching for a process with the configured executable name.
        """
        return self._find_process() is not None

    def wait_until_running(
        self,
        timeout: float = 30.0,
        interval: float = 0.25,
    ) -> bool:
        """
        Wait until the process is running.

        Returns:
            True if the process starts within the timeout, otherwise False.
        """
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if self.is_running():
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
        args: list[str] | None = None,
        *,
        wait: bool = True,
        timeout: float = 30.0,
        check_running: bool = True,
    ) -> bool:
        """
        Start the executable.

        Args:
            args: Optional command-line arguments.
            wait: Whether to wait for the process to appear.
            timeout: Maximum time to wait for the process to start.
            check_running: Whether to return early if the executable is already running.

        Returns:
            True if the process is running, or was started successfully when wait=False.
        """
        if check_running and self.is_running():
            return True

        command = [str(self.executable)]

        if args:
            command.extend(args)

        # Use subprocess for launching because it provides the appropriate
        # Windows process creation flags and gives us the PID.
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS,
        )

        # Immediately wrap the newly created PID with psutil.
        # All subsequent operations can now use the fast path without scanning processes.
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

        Returns:
            True if the process is stopped within the timeout.
        """
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
        args: list[str],
        *,
        timeout: float = 30.0,
    ) -> bool:
        """
        Ask the application to terminate using command-line arguments.

        Example:
            steam.stop_with_args(["-shutdown"])

        Returns:
            True if the process terminates within the timeout.
        """
        if not self.is_running():
            return True

        subprocess.run(
            [str(self.executable), *args,],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        return self.wait_until_stopped(timeout)

    def restart(
        self,
        args: list[str] | None = None,
        *,
        stop_args: list[str] | None = None,
        timeout: float = 30.0,
    ) -> bool:
        """
        Restart the process.

        Args:
            args: Arguments passed to the process when starting it.
            stop_args: Optional arguments used for graceful shutdown.
            timeout: Maximum time allowed for stopping and starting.
        """
        if stop_args:
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
    # Internal helpers
    # -------------------------------------------------------------------------

    def _managed_process(self) -> psutil.Process | None:
        """
        Return the process started by this manager if it is still alive.

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

        First try the cached process created by start(). If there is no managed process,
        search for an externally started process by executable name.
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
                if process.info["name"] == self.process_name:
                    return process
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Processes can disappear between process_iter() and accessing
                # their information. Ignore those processes and continue.
                continue

        return None
