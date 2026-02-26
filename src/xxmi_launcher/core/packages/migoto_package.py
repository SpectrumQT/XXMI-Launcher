import logging
import subprocess
import json
import time

from typing import List
from dataclasses import dataclass, field
from pathlib import Path

import core.error_manager as Errors
import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.locale_manager import L
from core.package_manager import Package, PackageMetadata

from core.utils.dll_injector import DllInjector
from core.utils.process_tracker import wait_for_process, WaitResult, ProcessPriority, wait_for_process_exit

log = logging.getLogger(__name__)


@dataclass
class MigotoManagerEvents:

    @dataclass
    class OpenModsFolder:
        pass

    @dataclass
    class StartAndInject:
        game_exe_path: Path
        start_exe_path: Path
        start_args: List[str] = field(default_factory=lambda: [])
        work_dir: str = None
        use_hook: bool = True


@dataclass
class MigotoManagerConfig:
    enforce_rendering: bool = True
    enable_hunting: bool = False
    dump_shaders: bool = False
    mute_warnings: bool = True
    calls_logging: bool = False
    debug_logging: bool = False
    unsafe_mode: bool = False
    unsafe_mode_signature: str = ''


class MigotoPackage(Package):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='XXMI',
            auto_load=False,
            github_repo_owner='SpectrumQT',
            github_repo_name='XXMI-Libs-Package',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='XXMI-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$)',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=False,
        ))

        Events.Subscribe(Events.MigotoManager.OpenModsFolder, self.handle_open_mods_folder)
        Events.Subscribe(Events.MigotoManager.StartAndInject, self.handle_start_and_inject)

    def get_installed_version(self):
        try:
            with open(self.package_path / 'Manifest.json', 'r') as f:
                return json.load(f)['version']
        except Exception as e:
            return ''

    def wrap_av_error(self, e: Exception) -> Exception:
        return Errors.with_title(Exception(L('error_package_corrupted_by_antivirus', """
            **{package_name}** package is corrupted by antivirus (e.g. Windows Defender).
            
            Antiviruses update frequently, try again later, or consider whitelisting paths:
            
            - `{package_folder_path}`
            - `{xxmi_deployment_path}`
            
            Error: {error_text}
            
            This is likely a [false positive]({false_positive_link}). Libraries are built from [open source]({repo_link}) using [GitHub Actions]({github_actions_link}) and downloaded from [GitHub releases]({releases_link}).
        """).format(
            package_name='XXMI Libraries',
            false_positive_link='https://learn.microsoft.com/en-us/defender-endpoint/defender-endpoint-false-positives-negatives',
            repo_link='https://github.com/SpectrumQT/XXMI-Libs-Package',
            github_actions_link='https://github.com/features/actions',
            releases_link='https://github.com/SpectrumQT/XXMI-Libs-Package/releases',
            package_folder_path=str(self.package_path),
            xxmi_deployment_path=str(Config.Active.Importer.importer_path / 'd3d11.dll'),
            error_text=str(e),
        )), L('error_title_package_corrupted_by_antivirus', 'Data Corruption Detected'))

    def download_latest_version(self):
        try:
            super().download_latest_version()
        except Exception as e:
            if Paths.App.is_av_error(e):
                raise self.wrap_av_error(e)
            raise

    def install_latest_version(self, clean):
        try:
            Events.Fire(Events.PackageManager.InitializeInstallation())
            self.move_contents(self.downloaded_asset_path, self.package_path)
        except Exception as e:
            if Paths.App.is_av_error(e):
                raise self.wrap_av_error(e)
            raise

    def handle_open_mods_folder(self, event: MigotoManagerEvents.OpenModsFolder):
        mods_path = Config.Active.Importer.importer_path / 'Mods'
        Paths.verify_path(mods_path)
        subprocess.Popen(['explorer.exe', mods_path])

    def handle_start_and_inject(self, event: MigotoManagerEvents.StartAndInject):

        injector = MigotoInjector.from_event(event, self.package_path / '3dmloader.dll')

        context = injector.context

        # Deploy new or updated XXMI libraries to model importer folder
        if Config.Active.Importer.is_xxmi_dll_used():
            try:
                self.deploy_package_files(context.process_name)
            except Exception as e:
                self.restore_package_files(e, context.process_name, validate=False)

        # Check signatures to prevent 3rd-party 3dmigoto libraries from loading
        if not Config.Active.Migoto.unsafe_mode:
            try:
                self.validate_deployed_files()
            except Exception as e:
                self.restore_package_files(e, context.process_name, validate=True)

        Events.Fire(Events.Application.Busy())

        injector.run()

        # Wait a bit more for window to maximize
        time.sleep(1)

    def restore_package_files(self, e: Exception, process_name: str, validate=False):
        if Paths.App.is_av_error(e) or isinstance(e, FileNotFoundError):
            e = self.wrap_av_error(e)
        else:
            e = Exception(L('error_xxmi_libs_package_corruption', """
                **XXMI Libraries** package is corrupted.
                
                Details: {error_text}
            """).format(
                error_text=str(e).strip()
            ))

        user_requested_restore = Events.Call(Events.Application.ShowError(
            modal=True,
            title=L('message_title_package_repair', 'Package Repair Available'),
            message=L('message_text_package_repair', """
                {error_text}
                
                Would you like to repair the package automatically?
            """).format(error_text=str(e).strip()),
            confirm_text=L('message_button_repair_package', 'Repair'),
            cancel_text=L('message_button_cancel', 'Cancel'),
        ))

        if not user_requested_restore:
            raise e

        if validate:
            try:
                self.validate_package_files()
            except Exception as e:
                Events.Fire(Events.Application.Update(packages=[self.metadata.package_name], no_thread=True, force=True, reinstall=True, silent=True))
        else:
            Events.Fire(Events.Application.Update(packages=[self.metadata.package_name], no_thread=True, force=True, reinstall=True, silent=True))

        self.deploy_package_files(process_name, force=True)

    def should_deploy_package_file(self, file_name: str, file_path: Path, force: bool = False) -> tuple[bool, str]:
        # Handle forced redeployment
        if force:
            return True, 'Forcing re-deploy of {file_path}...'
        # Handle missing DLL
        if not file_path.is_file():
            return True, 'Deploying new {file_path}...'
        # Handle signature mismatch between deployed DLL and one from manifest of installed XXMI package
        deployed_signature = Config.Active.Importer.deployed_migoto_signatures.get(file_name, '')
        if not deployed_signature or deployed_signature != self.get_signature(file_path):

            if Config.Active.Migoto.unsafe_mode:
                # Lets deside what to do based on DLL origin
                with open(file_path, 'rb') as f:
                    if self.security.verify(deployed_signature, f.read()):
                        # DLL matches the signature of last deployed one, it should be safe to update it
                        return True, 'Deploying updated {file_path}...'
                    else:
                        # Third-party DLL found, lets leave its management to user
                        return False, 'Skipped auto-deploy for {file_path} (signature mismatch)!'
            else:
                # We should never reach this point unless the config is desynced (and if it is, lets redeploy)
                return True, 'Re-deploying {file_path}...'

        return False, ''

    def deploy_package_files(self, process_name: str, force: bool = False):
        Events.Fire(Events.Application.Busy())

        pending_removals = {}
        pending_deployments = {}

        package_files = ['d3d11.dll', 'd3dcompiler_47.dll', 'nvapi64.dll']

        for file_name in package_files:
            file_path = Config.Active.Importer.importer_path / file_name

            if file_name == 'nvapi64.dll':
                if file_path.is_file():
                    pending_removals[file_path] = 'Removing deprecated {file_path}...'
                continue

            deploy, message = self.should_deploy_package_file(file_name, file_path, force)
            if deploy:
                pending_removals[file_path] = 'Removing outdated {file_path}...'
                pending_deployments[file_path] = message
                continue

        if pending_deployments or pending_removals:
            Events.Fire(Events.Application.StatusUpdate(status=L('status_ensuring_game_closed', 'Ensuring the game is closed...')))
            result, pid = wait_for_process_exit(process_name=process_name, timeout=5, kill_timeout=0)
            if result == WaitResult.Timeout:
                Events.Fire(Events.Application.ShowError(
                    modal=True,
                    message=L('message_text_game_stop_failed', """
                        Failed to stop {process_name}!
                        
                        Please close the game manually and press [OK] to continue.
                    """).format(process_name=process_name),
                ))

        for file_path, message in pending_removals.items():
            if not file_path.is_file():
                continue
            if message:
                log.debug(message.format(file_path=file_path))
            try:
                Paths.App.remove_path(file_path)
            except Exception as e:
                raise ValueError(L('error_xxmi_dll_remove_failed', """
                    Failed to remove old XXMI library file before update!

                    File: `{dll_path}`

                    Error: {error_text}
                """).format(
                    dll_path=file_path,
                    error_text=str(e),
                )) from e

        for file_path, message in pending_deployments.items():
            if message:
                log.debug(message.format(file_path=file_path))
            package_file_path = self.package_path / file_path.name
            if package_file_path.is_file():
                Paths.App.copy_file(package_file_path, file_path)
                original_signature = self.get_signature(file_path)
                Config.Active.Importer.deployed_migoto_signatures[file_path.name] = original_signature
            else:
                raise FileNotFoundError(L('error_xxmi_missing_critical_file', 'XXMI package is missing critical file: {file_name}!').format(file_name=file_path.name))

    def validate_deployed_files(self):
        Events.Fire(Events.Application.Busy())

        package_libs = ['3dmloader.dll']
        self.validate_files([self.package_path / f for f in package_libs])

        importer_libs = ['d3d11.dll', 'd3dcompiler_47.dll']
        self.validate_files([Config.Active.Importer.importer_path / f for f in importer_libs])

    def validate_package_files(self):
        package_libs = ['3dmloader.dll', 'd3d11.dll', 'd3dcompiler_47.dll']
        self.validate_files([self.package_path / f for f in package_libs])

    def uninstall(self):
        log.debug(f'Uninstalling package {self.metadata.package_name}...')

        if self.package_path.is_dir():
            Paths.App.remove_path(self.package_path)


@dataclass
class LaunchContext:
    process_name: str
    start_exe_path: Path
    start_args: list[str]
    work_dir: str | None
    process_flags: int
    use_hook: bool
    custom_launch_cmd: str | None
    xxmi_dll_path: Path
    inject_dll_paths: list[Path]


class MigotoInjector:
    def __init__(self, context: LaunchContext, injector_path: Path):
        self.context = context
        self.injector_path = injector_path
        self.injector: DllInjector | None = None

    @classmethod
    def from_event(cls, event: MigotoManagerEvents.StartAndInject, injector_path: Path):
        context = cls.get_launch_context(event)
        return cls(context, injector_path)

    def run(self):
        context = self.context

        self.injector = DllInjector(
            injector_lib_path=self.injector_path,
            load_hook=context.use_hook,
            load_inject=not context.use_hook or len(context.inject_dll_paths) > 0,
        )

        if context.use_hook:
            # Use WriteProcessMemory injection method
            self.run_hook_injector()
        else:
            # Use SetWindowsHookEx injection method
            self.run_direct_injector()

    @staticmethod
    def get_launch_context(event: MigotoManagerEvents.StartAndInject) -> LaunchContext:

        start_args = list(event.start_args)
        if Config.Active.Importer.use_launch_options:
            start_args += Config.Active.Importer.launch_options.split()

        process_flags = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_DEFAULT_ERROR_MODE
        process_flags |= ProcessPriority(Config.Active.Importer.process_priority).get_process_flag()

        if not Config.Active.Importer.custom_launch_enabled:
            use_hook = event.use_hook
            custom_launch_cmd = None
        else:
            use_hook = Config.Active.Importer.custom_launch_inject_mode == 'Hook'
            custom_launch_cmd = Config.Active.Importer.custom_launch.strip() or None

        dll_paths = list(Config.Active.Importer.extra_dll_paths) if Config.Active.Importer.extra_libraries_enabled else []

        return LaunchContext(
            process_name=event.game_exe_path.name,
            start_exe_path=event.start_exe_path,
            start_args=start_args,
            work_dir=event.work_dir,
            process_flags=process_flags,
            use_hook=use_hook,
            custom_launch_cmd=custom_launch_cmd,
            xxmi_dll_path=Config.Active.Importer.importer_path / 'd3d11.dll',
            inject_dll_paths=dll_paths,
        )

    @staticmethod
    def wait_for_window(context: LaunchContext, injection_verified: bool):
        Events.Fire(Events.Application.WaitForProcess(process_name=context.process_name))

        result, pid = wait_for_process(context.process_name, with_window=True,
                                       timeout=Config.Active.Importer.process_timeout, check_visibility=True)

        if result == WaitResult.Timeout:
            if injection_verified:
                raise ValueError(L('error_migoto_game_detection_timeout', """
                    Failed to detect window of game process {process_name}!

                    If game window takes more than {start_timeout} seconds to appear, adjust **Timeout** in **General Settings**.

                    If game crashed, try to follow the [Crash Isolation Checklist]({checklist_link}).
                """).format(
                    process_name=context.process_name,
                    importer=Config.Launcher.active_importer,
                    start_timeout=Config.Active.Importer.process_timeout,
                    checklist_link='https://github.com/SpectrumQT/XXMI-Launcher/blob/main/.github/ISSUE_TEMPLATE/game-crash-report.md#-crash-isolation-checklist'
                ))
            else:
                raise ValueError(L('error_migoto_game_start_failed',
                    'Failed to start {process_name}!'
                ).format(process_name=context.process_name))

    def run_direct_injector(self):
        injector = self.injector
        context = self.context

        dll_paths = []
        if Config.Active.Importer.is_xxmi_dll_used():
            if not Config.Active.Importer.is_xxmi_dll_in_extra_libraries():
                dll_paths.append(context.xxmi_dll_path)
        dll_paths += context.inject_dll_paths

        if dll_paths:
            dll_names = ', '.join([dll_path.name for dll_path in dll_paths])
            Events.Fire(Events.Application.Inject(library_name=dll_names, process_name=context.process_name))
        else:
            Events.Fire(Events.Application.Bypass(process_name=context.process_name))

        try:
            injector.open_process(
                start_method=Config.Active.Importer.process_start_method,
                exe_path=str(context.start_exe_path),
                work_dir=context.work_dir,
                start_args=context.start_args,
                process_flags=context.process_flags,
                process_name=context.process_name,
                dll_paths=dll_paths,
                cmd=context.custom_launch_cmd,
                inject_timeout=Config.Active.Importer.process_timeout,
            )

            # Wait until game window appears
            self.wait_for_window(context, injection_verified=True)

        finally:
            self.injector.unload()

    def run_hook_injector(self):
        injector = self.injector
        context = self.context

        try:
            # Setup global windows hook for 3dmigoto dll
            Events.Fire(Events.Application.SetupHook(library_name=context.xxmi_dll_path.name, process_name=context.process_name))
            injector.hook_library(context.xxmi_dll_path, context.process_name)

            # Start game's exe
            Events.Fire(Events.Application.StartGameExe(process_name=context.process_name))

            injector.open_process(
                start_method = Config.Active.Importer.process_start_method,
                exe_path = str(context.start_exe_path),
                work_dir = context.work_dir,
                start_args = context.start_args,
                process_flags = context.process_flags,
                process_name = context.process_name,
                dll_paths = context.inject_dll_paths,
                cmd = context.custom_launch_cmd,
                inject_timeout=Config.Active.Importer.process_timeout,
            )

            # Early DLL injection verification
            hooked = injector.wait_for_injection(5)
            if hooked:
                log.info(f'Successfully passed early {context.xxmi_dll_path.name} -> {context.process_name} hook check!')

            # Wait until game window appears
            self.wait_for_window(context, injection_verified=hooked)

            # Late DLL injection verification
            Events.Fire(Events.Application.VerifyHook(library_name=context.xxmi_dll_path.name, process_name=context.process_name))

            if injector.wait_for_injection(5):
                log.info(f'Successfully passed late {context.xxmi_dll_path.name} -> {context.process_name} hook check!')
            elif not hooked:
                log.error(f'Failed to verify {context.xxmi_dll_path.name} -> {context.process_name} hook!')

        finally:
            # Remove global hook to free system resources
            injector.unhook_library()
            injector.unload()
