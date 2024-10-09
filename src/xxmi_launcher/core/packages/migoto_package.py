import logging
import shutil
import subprocess
import json
import time

from typing import List
from dataclasses import dataclass, field
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.package_manager import Package, PackageMetadata

from core.utils.dll_injector import DllInjector, direct_inject
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
    enable_hunting: bool = True
    dump_shaders: bool = False
    mute_warnings: bool = True
    debug_logging: bool = False
    unsafe_mode: bool = False
    unsafe_mode_signature: str = ''


class MigotoPackage(Package):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='XXMI',
            auto_load=True,
            github_repo_owner='SpectrumQT',
            github_repo_name='3Dmigoto',
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

    def install_latest_version(self, clean):
        Events.Fire(Events.PackageManager.InitializeInstallation())

        self.move_contents(self.downloaded_asset_path, self.package_path)

    def handle_open_mods_folder(self, event: MigotoManagerEvents.OpenModsFolder):
        subprocess.Popen(['explorer.exe', Config.Active.Importer.importer_path / 'Mods'])

    def handle_start_and_inject(self, event: MigotoManagerEvents.StartAndInject):
        process_name = event.game_exe_path.name

        try:
            # Copy XXMI package files to game instance
            self.deploy_client_files(process_name)
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
        launch_cmd = [str(event.start_exe_path)] + event.start_args + Config.Active.Importer.launch_options.split()
        launch_work_dir = event.work_dir
        launch_flags = ProcessPriority(Config.Active.Importer.process_priority).get_process_flags()
        use_hook = event.use_hook
        use_shell = False

        if Config.Active.Importer.custom_launch_enabled:
            custom_launch_cmd = Config.Active.Importer.custom_launch.strip()
            if custom_launch_cmd:
                launch_cmd = custom_launch_cmd
                launch_work_dir = None
                use_hook = Config.Active.Importer.custom_launch_inject_mode == 'Hook'
                use_shell = True

        extra_dll_paths = []
        if Config.Active.Importer.extra_libraries_enabled:
            extra_dll_paths += Config.Active.Importer.extra_dll_paths

        if use_hook:
            # Use SetWindowsHookEx injection method
            injector = DllInjector(self.package_path / '3dmloader.dll')
            try:
                # Setup global windows hook for 3dmigoto dll
                Events.Fire(Events.Application.SetupHook(library_name=dll_path.name, process_name=process_name))
                injector.hook_library(dll_path, process_name)

                # Start game's exe
                Events.Fire(Events.Application.StartGameExe(process_name=process_name))
                if len(extra_dll_paths) == 0:
                    subprocess.Popen(launch_cmd, creationflags=launch_flags, cwd=launch_work_dir, shell=use_shell)
                else:
                    pid = direct_inject(dll_paths=extra_dll_paths, process_name=process_name, start_cmd=launch_cmd,
                                        work_dir=launch_work_dir, creationflags=launch_flags, use_shell=use_shell)
                    if pid == -1:
                        raise ValueError(f'Failed to inject {str(extra_dll_paths)}!')

                # Early DLL injection verification
                hooked = injector.wait_for_injection(5)
                if hooked:
                    log.info(f'Successfully passed early {dll_path.name} -> {process_name} hook check!')

                # Wait until game window appears
                Events.Fire(Events.Application.WaitForProcess(process_name=process_name))
                result, pid = wait_for_process(process_name, with_window=True, timeout=30, check_visibility=True)
                if result == WaitResult.Timeout:
                    raise ValueError(f'Failed to start {process_name}!')

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
            Events.Fire(Events.Application.Inject(library_name=dll_path.name, process_name=process_name))
            dll_paths = [dll_path] + extra_dll_paths
            pid = direct_inject(dll_paths=dll_paths, process_name=process_name, start_cmd=launch_cmd,
                                work_dir=launch_work_dir, creationflags=launch_flags, use_shell=use_shell)
            if pid == -1:
                raise ValueError(f'Failed to inject {dll_path.name}!')

            Events.Fire(Events.Application.WaitForProcess(process_name=process_name))
            result, pid = wait_for_process(process_name, with_window=True, timeout=30, check_visibility=True)
            if result == WaitResult.Timeout:
                raise ValueError(f'Failed to start {process_name}!')

        # Wait a bit more for window to maximize
        time.sleep(1)

    def restore_package_files(self, e: Exception, process_name: str, validate=False):
        user_requested_restore = Events.Call(Events.Application.ShowError(
            modal=True,
            confirm_text='Restore',
            cancel_text='Cancel',
            message=f'XXMI installation is damaged!\n\n'
                    f'Details: {str(e).strip()}\n\n'
                    f'Would you like to restore XXMI automatically?',
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

        self.deploy_client_files(process_name, force=True)

    def deploy_client_files(self, process_name: str, force: bool = False):
        for client_file in ['d3d11.dll', 'd3dcompiler_47.dll', 'nvapi64.dll']:
            client_file_path = Config.Active.Importer.importer_path / client_file
            client_file_signature = Config.Active.Importer.deployed_migoto_signatures.get(client_file, '')

            deploy_pending = False
            if not client_file_path.exists() or not client_file_signature:
                log.debug(f'Deploying new {client_file_path}...')
                deploy_pending = True
            elif force:
                log.debug(f'Forcing re-deploy of {client_file_path}...')
                deploy_pending = True
            else:
                if client_file_signature != self.get_signature(client_file_path):
                    with open(client_file_path, 'rb') as f:
                        if self.security.verify(client_file_signature, f.read()):
                            log.debug(f'Deploying updated {client_file_path}...')
                            deploy_pending = True
                        else:
                            log.debug(f'Skipped auto-deploy for {client_file_path} (signature mismatch)!')

            if deploy_pending:
                Events.Fire(Events.Application.StatusUpdate(status='Ensuring the game is closed...'))
                result, pid = wait_for_process_exit(process_name=process_name, timeout=5, kill_timeout=0)
                if result == WaitResult.Timeout:
                    Events.Fire(Events.Application.ShowError(
                        modal=True,
                        message=f'Failed to stop {process_name}!\n\n'
                                'Please close the game manually and press [OK] to continue.',
                    ))
                package_file_path = self.package_path / client_file
                if package_file_path.exists():
                    shutil.copy2(package_file_path, client_file_path)
                    if deploy_pending:
                        Config.Active.Importer.deployed_migoto_signatures[client_file] = self.get_signature(client_file_path)
                else:
                    raise ValueError(f'XXMI package is missing critical file: {client_file_path.name}!\n')

    def validate_deployed_files(self):
        self.validate_files([Config.Active.Importer.importer_path / f for f in ['d3d11.dll', 'd3dcompiler_47.dll', 'nvapi64.dll']])
        self.validate_files([self.package_path / f for f in ['3dmloader.dll']])

    def validate_package_files(self):
        self.validate_files([self.package_path / f for f in ['3dmloader.dll', 'd3d11.dll', 'd3dcompiler_47.dll', 'nvapi64.dll']])

    def uninstall(self):
        log.debug(f'Uninstalling package {self.metadata.package_name}...')

        if self.package_path.is_dir():
            log.debug(f'Removing {self.package_path}...')
            shutil.rmtree(self.package_path)
