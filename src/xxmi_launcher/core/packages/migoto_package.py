import logging
import subprocess
import json
import time

from dataclasses import dataclass
from pathlib import Path

import core.error_manager as Errors
import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.locale_manager import L
from core.package_manager import Package, PackageMetadata
from core.config.enums import InputDisableMode, LogLevel

from core.utils.dll_injector import DllInjector
from core.utils.process_manager import LaunchContext

log = logging.getLogger(__name__)


@dataclass
class MigotoManagerConfig:
    enforce_rendering: bool = True
    enable_hunting: bool = False
    clear_unknown_settings: bool = True
    dump_shaders: bool = False
    mute_warnings: bool = True
    input: bool = True
    input_disable_mode: InputDisableMode = InputDisableMode.MODS
    toggle_input: str = 'ctrl alt shift VK_END'
    log_level: LogLevel = LogLevel.DISABLED
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
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2}))\r?$',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=False,
        ))

        Events.Subscribe(Events.MigotoManager.OpenModsFolder, self.handle_open_mods_folder)

    def get_installed_version(self, dll_path: Path | None = None) -> str:
        dll_path = dll_path or self.package_path / "d3d11.dll"

        if not dll_path.is_file():
            return ""

        has_valid_signature = False
        try:
            self.verify_signature(dll_path)
            has_valid_signature = True
        except Exception:
            pass

        if has_valid_signature:
            # Read XXMI DLL version directly from file. Supported for XXMI DLL v1.1.9+.
            file_version = self.get_file_version(dll_path, max_parts=3)
            # Old XXMI DLL files have file version frozen at 1.3.16 of original 3Dmigoto.
            if file_version != "1.3.16":
                return file_version

            # Read XXMI DLL version from manifest.
            try:
                with open(self.package_path / "Manifest.json", 'r') as f:
                    return json.load(f)["version"]
            except Exception:
                pass

        return "X.X.X"

    def get_deployed_version(self) -> str:
        dll_path = Config.Active.Importer.importer_path / 'd3d11.dll'
        return self.get_installed_version(dll_path)

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
            self.verify_files_integrity(self.package_path)
            self.deploy_package_files()
        except Exception as e:
            if Paths.App.is_av_error(e):
                raise self.wrap_av_error(e)
            raise

    def handle_open_mods_folder(self, event: Events.MigotoManager.OpenModsFolder):
        mods_path = Config.Active.Importer.importer_path / 'Mods'
        Paths.verify_path(mods_path)
        subprocess.Popen(['explorer.exe', mods_path])

    def run_pre_launch(self, launch_context: LaunchContext):
        # Deploy new or updated XXMI libraries to model importer folder
        try:
            self.deploy_package_files()
        except Exception as e:
            self.restore_package_files(e, validate=False)

        # Check signatures to prevent 3rd-party 3dmigoto libraries from loading
        if not Config.Active.Migoto.unsafe_mode:
            try:
                self.validate_deployed_files()
            except Exception as e:
                self.restore_package_files(e, validate=True)

    def restore_package_files(self, e: Exception, validate=False):
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

        self.deploy_package_files(force=True)

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

    def deploy_package_files(self, force: bool = False):
        Events.Fire(Events.Application.Busy())

        Paths.verify_path(Config.Active.Importer.importer_path)

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

        Events.Fire(Events.PackageManager.NotifyPackageVersions(detect_installed=True))

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
class InjectorContext:
    injector_path: Path
    process_name: str
    use_hook: bool
    xxmi_dll_path: Path
    inject_dll_paths: list[Path]


class MigotoInjector:
    def __init__(
        self,
        context: InjectorContext,
    ):
        self.context = context
        self.injector: DllInjector | None = None
        self._hooked: bool = False

    def __enter__(self) -> "MigotoInjector":
        self.injector = DllInjector(
            injector_lib_path=self.context.injector_path,
            load_hook=self.context.use_hook,
            load_inject=not self.context.use_hook or len(self.context.inject_dll_paths) > 0,
        )

        try:
            if self.context.use_hook:
                self.setup_hook_injector()
            else:
                self.setup_direct_injector()
        except BaseException:
            self.injector.unload()
            self.injector = None
            raise

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if self.context.use_hook:
                self.cleanup_hook_injector()
            else:
                self.cleanup_direct_injector()
        finally:
            self.injector.unload()
            self.injector = None

        return False

    def run(self):
        if self.context.use_hook:
            # Use WriteProcessMemory injection method
            self.run_hook_injector()
        else:
            # Use SetWindowsHookEx injection method
            self.run_direct_injector()

    def verify(self):
        if self.context.use_hook:
            # Use WriteProcessMemory injection method
            self.verify_hook_injector()
        else:
            # Use SetWindowsHookEx injection method
            self.verify_direct_injector()

    def setup_direct_injector(self):
        pass

    def cleanup_direct_injector(self):
        pass

    def verify_direct_injector(self):
        pass

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

        if dll_paths:
            pid = injector.inject_libraries(dll_paths, context.process_name, timeout=Config.Active.Importer.process_timeout)

    def setup_hook_injector(self):
        context = self.context

        # Setup global windows hook for 3dmigoto dll
        Events.Fire(Events.Application.SetupHook(library_name=context.xxmi_dll_path.name, process_name=context.process_name))
        self.injector.hook_library(context.xxmi_dll_path, context.process_name)


    def cleanup_hook_injector(self):
        if self.injector is not None:
            # Remove global hook to free system resources.
            self.injector.unhook_library()

    def run_hook_injector(self):
        injector = self.injector
        context = self.context

        if context.inject_dll_paths:
            pid = injector.inject_libraries(context.inject_dll_paths, context.process_name, timeout=Config.Active.Importer.process_timeout)

        # Early DLL injection verification
        self._hooked = injector.wait_for_injection(5)
        if self._hooked:
            log.info(f'Successfully passed early {context.xxmi_dll_path.name} -> {context.process_name} hook check!')

    def verify_hook_injector(self):
        injector = self.injector
        context = self.context

        # Late DLL injection verification
        Events.Fire(Events.Application.VerifyHook(library_name=context.xxmi_dll_path.name, process_name=context.process_name))

        if injector.wait_for_injection(5):
            log.info(f'Successfully passed late {context.xxmi_dll_path.name} -> {context.process_name} hook check!')
        elif not self._hooked:
            log.error(f'Failed to verify {context.xxmi_dll_path.name} -> {context.process_name} hook!')
