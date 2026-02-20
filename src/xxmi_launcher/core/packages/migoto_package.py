import logging
import shutil
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
        subprocess.Popen(['explorer.exe', Config.Active.Importer.importer_path / 'Mods'])

    def handle_start_and_inject(self, event: MigotoManagerEvents.StartAndInject):
        process_name = event.game_exe_path.name

        Events.Fire(Events.Application.Busy())

        try:
            # Copy XXMI package files to game instance
            self.deploy_package_files(process_name)
        except Exception as e:
            # Attempt to restore damaged game instance files
            self.restore_package_files(e, process_name, validate=False)

        Events.Fire(Events.Application.Busy())

        if not Config.Active.Migoto.unsafe_mode:
            try:
                # Check signatures to prevent 3rd-party 3dmigoto libraries from loading
                self.validate_deployed_files()
            except Exception as e:
                self.restore_package_files(e, process_name, validate=True)

        Events.Fire(Events.Application.Busy())

        dll_path = Config.Active.Importer.importer_path / 'd3d11.dll'

        start_args = event.start_args
        if Config.Active.Importer.use_launch_options:
            start_args += Config.Active.Importer.launch_options.split()

        process_flags = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_DEFAULT_ERROR_MODE
        process_flags |= ProcessPriority(Config.Active.Importer.process_priority).get_process_flag()

        use_hook = event.use_hook

        custom_launch_cmd = None
        if Config.Active.Importer.custom_launch_enabled:
            use_hook = Config.Active.Importer.custom_launch_inject_mode == 'Hook'
            custom_launch_cmd = Config.Active.Importer.custom_launch.strip() or None

        extra_dll_paths = []
        if Config.Active.Importer.extra_libraries_enabled:
            extra_dll_paths += Config.Active.Importer.extra_dll_paths

        injector = DllInjector(self.package_path / '3dmloader.dll')

        if use_hook:
            # Use SetWindowsHookEx injection method
            try:
                # Setup global windows hook for 3dmigoto dll
                Events.Fire(Events.Application.SetupHook(library_name=dll_path.name, process_name=process_name))
                injector.hook_library(dll_path, process_name)

                # Start game's exe
                Events.Fire(Events.Application.StartGameExe(process_name=process_name))

                injector.open_process(
                    start_method = Config.Active.Importer.process_start_method,
                    exe_path = str(event.start_exe_path),
                    work_dir = event.work_dir,
                    start_args = start_args,
                    process_flags = process_flags,
                    process_name = process_name,
                    dll_paths = extra_dll_paths,
                    cmd = custom_launch_cmd,
                    inject_timeout=Config.Active.Importer.process_timeout,
                )

                # Early DLL injection verification
                hooked = injector.wait_for_injection(5)
                if hooked:
                    log.info(f'Successfully passed early {dll_path.name} -> {process_name} hook check!')

                # Wait until game window appears
                Events.Fire(Events.Application.WaitForProcess(process_name=process_name))
                result, pid = wait_for_process(process_name, with_window=True, timeout=Config.Active.Importer.process_timeout, check_visibility=True)
                if result == WaitResult.Timeout:
                    if hooked:
                        raise ValueError(L('error_migoto_game_detection_timeout', """
                            Failed to detect window of game process {process_name}!
    
                            If game window takes more than {start_timeout} seconds to appear, adjust **Timeout** in **General Settings**.
    
                            If game crashed, try to follow the [Crash Isolation Checklist]({checklist_link}).
                        """).format(
                            process_name=process_name,
                            importer=Config.Launcher.active_importer,
                            start_timeout=Config.Active.Importer.process_timeout,
                            checklist_link='https://github.com/SpectrumQT/XXMI-Launcher/blob/main/.github/ISSUE_TEMPLATE/game-crash-report.md#-crash-isolation-checklist'
                        ))
                    else:
                        raise ValueError(L('error_migoto_game_start_failed',
                            'Failed to start {process_name}!'
                        ).format(process_name=process_name))

                # Late DLL injection verification
                Events.Fire(Events.Application.VerifyHook(library_name=dll_path.name, process_name=process_name))
                if injector.wait_for_injection(5):
                    log.info(f'Successfully passed late {dll_path.name} -> {process_name} hook check!')
                elif not hooked:
                    log.error(f'Failed to verify {dll_path.name} -> {process_name} hook!')

            except Exception as e:
                raise e

            finally:
                # Remove global hook to free system resources
                injector.unhook_library()
                injector.unload()

        else:
            # Use WriteProcessMemory injection method
            dll_paths = []
            if Config.Active.Importer.is_xxmi_dll_used():
                if not Config.Active.Importer.is_xxmi_dll_in_extra_libraries():
                    dll_paths.append(dll_path)
            dll_paths += extra_dll_paths

            dll_names = ', '.join([dll_path.name for dll_path in dll_paths])

            Events.Fire(Events.Application.Inject(library_name=dll_names, process_name=process_name))

            try:
                injector.open_process(
                    start_method=Config.Active.Importer.process_start_method,
                    exe_path=str(event.start_exe_path),
                    work_dir=event.work_dir,
                    start_args=start_args,
                    process_flags=process_flags,
                    process_name=process_name,
                    dll_paths=dll_paths,
                    cmd=custom_launch_cmd,
                    inject_timeout=Config.Active.Importer.process_timeout,
                )

            except Exception as e:
                raise e

            finally:
                injector.unload()

            Events.Fire(Events.Application.WaitForProcess(process_name=process_name))
            result, pid = wait_for_process(process_name, with_window=True, timeout=Config.Active.Importer.process_timeout, check_visibility=True)
            if result == WaitResult.Timeout:
                raise ValueError(L('error_migoto_game_detection_timeout', """
                    Failed to detect window of game process {process_name}!

                    If game window takes more than {start_timeout} seconds to appear, adjust **Timeout** in **General Settings**.

                    If game crashed, try to follow the [Crash Isolation Checklist]({checklist_link}).
                """).format(
                    process_name=process_name,
                    importer=Config.Launcher.active_importer,
                    start_timeout=Config.Active.Importer.process_timeout,
                    checklist_link='https://github.com/SpectrumQT/XXMI-Launcher/blob/main/.github/ISSUE_TEMPLATE/game-crash-report.md#-crash-isolation-checklist'
                ))

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
                error_text=str(e).strip())
            )

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

    def deploy_package_files(self, process_name: str, force: bool = False):
        for file_name in ['d3d11.dll', 'd3dcompiler_47.dll', 'nvapi64.dll']:
            deployment_path = Config.Active.Importer.importer_path / file_name
            deployed_signature = Config.Active.Importer.deployed_migoto_signatures.get(file_name, '')

            deploy_pending = False
            remove_pending = False

            if file_name == 'nvapi64.dll':
                if deployment_path.is_file():
                    # nvapi64.dll is found at deployment path, it's no longer supported and should be removed
                    log.debug(f'Removing deprecated {deployment_path}...')
                    remove_pending = True
                else:
                    # DLL should not be deployed and does not exist, lets exit early
                    continue

            if deploy_pending or remove_pending:
                # Some DLL already got special treatment, no further checks required
                pass
            elif force:
                # Forced redeployment requested, lets just redeploy without any extra checks
                log.debug(f'Forcing re-deploy of {deployment_path}...')
                deploy_pending = True
            elif not deployment_path.is_file():
                # DLL is not found at deployment path, we must deploy one
                log.debug(f'Deploying new {deployment_path}...')
                deploy_pending = True
            elif not deployed_signature or deployed_signature != self.get_signature(deployment_path):
                # Signature of deployed DLL doesn't match one from manifest of installed XXMI package
                if Config.Active.Migoto.unsafe_mode:
                    # Lets deside what to do based on DLL origin
                    with open(deployment_path, 'rb') as f:
                        if self.security.verify(deployed_signature, f.read()):
                            # DLL matches the signature of last deployed one, it should be safe to update it
                            log.debug(f'Deploying updated {deployment_path}...')
                            deploy_pending = True
                        else:
                            # Third-party DLL found, lets leave its management to user
                            log.debug(f'Skipped auto-deploy for {deployment_path} (signature mismatch)!')
                else:
                    # We should never reach this point unless the config is desynced (and if it is, lets redeploy)
                    log.debug(f'Re-deploying updated {deployment_path}...')
                    deploy_pending = True

            if deploy_pending or remove_pending:
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
                if remove_pending:
                    deployment_path.unlink()
                    continue
                if deploy_pending:
                    package_file_path = self.package_path / file_name
                    if package_file_path.exists():
                        shutil.copy2(package_file_path, deployment_path)
                        if deploy_pending:
                            original_signature = self.get_signature(deployment_path)
                            Config.Active.Importer.deployed_migoto_signatures[file_name] = original_signature
                    else:
                        raise FileNotFoundError(L('error_xxmi_missing_critical_file', 'XXMI package is missing critical file: {file_name}!').format(file_name=deployment_path.name))

    def validate_deployed_files(self):
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
            log.debug(f'Removing {self.package_path}...')
            shutil.rmtree(self.package_path)
