import logging
import json

from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events

from core.locale_manager import L

from core.config.model import AppConfig, ImportersConfig
from core.config.security import AppConfigSecurity
from core.config.serialization import converter

from core.config.enums import GameLaunch, StartMethod, ProcessStartMethodLegacy, InjectMode, InjectModeLegacy

from core import package_manager
from core.packages import launcher_package
from core.packages.model_importers import gimi_package
from core.packages.model_importers import srmi_package
from core.packages.model_importers import wwmi_package
from core.packages.model_importers import zzmi_package
from core.packages.model_importers import himi_package
from core.packages.model_importers import efmi_package

log = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, config: AppConfig):
        self.config: AppConfig = config
        self.security: AppConfigSecurity = AppConfigSecurity(config)

    @property
    def config_path(self) -> Path:
        return Paths.App.Root / 'XXMI Launcher Config.json'

    @staticmethod
    def config_to_dict(config: AppConfig) -> dict:
        return converter.unstructure(config)

    @staticmethod
    def config_from_dict(data: dict) -> AppConfig:
        return converter.structure(data, AppConfig)

    @classmethod
    def config_to_json(cls, config: AppConfig) -> str:
        return json.dumps(cls.config_to_dict(config), indent=4)

    @classmethod
    def config_from_json(cls, config_json: str) -> AppConfig:
        return cls.config_from_dict(json.loads(config_json))

    def load(self, config_path: Path | None = None) -> None:
        config_path = config_path or self.config_path

        try:
            if config_path.is_file():
                config_json = Paths.App.read_text(config_path)
                loaded_config = self.config_from_json(config_json)
            else:
                loaded_config = AppConfig()

            self.config.__dict__.update(loaded_config.__dict__)

            self._update_runtime_state()
            self._update_globals()

            config_changed = not self._ensure_security()

            if config_changed:
                self.save()

        except Exception:
            log.exception("Failed to load configuration")
            raise

    def save(self) -> None:
        try:
            config_json = self.config_to_json(self.config)
        except (TypeError, ValueError) as exc:
            log.exception("Failed to serialize configuration")
            raise RuntimeError("Failed to serialize configuration") from exc

        try:
            Paths.App.write_file(self.config_path, config_json)
        except OSError as exc:
            log.exception("Failed to write configuration to %s", self.config_path)
            raise RuntimeError(f"Failed to write configuration to {self.config_path}") from exc

    def validate_config(self):
        wrong_signatures = self.security.validate_config()

        if not wrong_signatures:
            return

        msg = '\n'.join([f'{k}: "{v}"' for k, v in wrong_signatures.items()])

        user_requested_reset = Events.Call(Events.Application.ShowError(
            modal=True,
            confirm_text=L('message_button_reset_unsecure_setting', 'Reset'),
            cancel_text=L('message_button_keep_unsecure_setting', 'Keep'),
            message=L('message_text_unsecure_setting_validation_failed', """
                Failed to validate unsecure settings!

                {msg}
            """).format(msg=msg)
        ))

        if user_requested_reset:
            self.security.reset_invalid_settings(wrong_signatures)
        else:
            self.security.sign_settings()

    def migrate(self, new_version: str):
        old_version = self.config.Launcher.config_version

        # Exit early if no version upgrade required.
        if old_version == new_version:
            return

        migrator = ConfigMigrator(self.config)

        if migrator.upgrade(old_version, new_version):
            self.save()

    def sign_settings(self, save_config: bool = True):
        self.security.sign_settings()
        if save_config:
            self.save()

    def _update_runtime_state(self) -> None:
        if self.config.Launcher.gui_theme:
            self.config.active_theme = self.config.Launcher.gui_theme

    def _update_globals(self):
        global Launcher
        global Packages
        global Importers

        Launcher = self.config.Launcher
        Packages = self.config.Packages
        Importers = self.config.Importers

    def _ensure_security(self) -> bool:
        if self.security.is_key_pair_valid():
            return True

        self.security.generate_key_pair()
        return False


class ConfigMigrator:
    def __init__(self, config: AppConfig):
        self.config = config

    def upgrade(self, old_version: str, new_version: str) -> bool:
        # Fresh installation: initialize the version.
        if not old_version:
            log.debug('Initializing new config...')
            self.config.Launcher.config_version = new_version
            return True

        changed = self._migrate_config(old_version)

        if changed:
            self.config.Launcher.config_version = new_version

        return changed

    def _migrate_config(self, old_version: str) -> bool:
        patches = {
            '2.1.6': self._run_patch_216,
            '2.1.9': self._run_patch_219,
            '2.3.0': self._run_patch_230,
        }

        changed = False

        for patch_version, patch_func in patches.items():
            if old_version < patch_version:
                log.debug(f'Upgrading launcher config from {old_version} to {patch_version}...')
                changed |= patch_func()

        return changed

    # region Patches

    def _run_patch_216(self) -> bool:
        try:
            settings = self.config.Importers.ZZMI.Importer
            new_game_exe_names = ['ZenlessZoneZero.exe', 'ZenlessZoneZeroBeta.exe']

            if settings.game_exe_names == new_game_exe_names:
                return False

            settings.game_exe_names = new_game_exe_names
            return True

        except (AttributeError, TypeError):
            log.debug('Could not apply config patch 2.1.6', exc_info=True)
            return False

    def _run_patch_219(self) -> bool:
        changed = False

        for importer in self.config.Importers.__dict__.values():
            try:
                # Force re-enable rendering setting enforcement to ensure d3dx.ini update
                if importer.Migoto.enforce_rendering is not True:
                    importer.Migoto.enforce_rendering = True
                    changed = True

                # Reload enforced rendering settings from package configuration
                ini_overrides = importer.Importer.d3dx_ini
                new_config = type(importer)()
                new_value = new_config.Importer.d3dx_ini['enforce_rendering']

                if ini_overrides.get('enforce_rendering') != new_value:
                    ini_overrides['enforce_rendering'] = new_value
                    changed = True

            except (AttributeError, KeyError, TypeError):
                log.debug('Could not apply config patch 2.1.9 to importer', exc_info=True)

        return changed

    def _run_patch_230(self) -> bool:
        for importer in self.config.Importers.__dict__.values():
            importer_name = type(importer).__name__
            # Handle legacy Custom Launch option.
            if importer.Importer.custom_launch_enabled:
                # Migrate Custom Launch option.
                if importer.Importer.custom_launch:
                    importer.Importer.game_launch = GameLaunch.CUSTOM
                    log.debug(f"[{importer_name}]: Migrated CUSTOM_LAUNCH {importer.Importer.custom_launch_enabled} -> {importer.Importer.game_launch}")

                # Handle legacy Inject Mode.
                match importer.Importer.custom_launch_inject_mode:
                    # Upgrade HOOK enum.
                    case InjectModeLegacy.HOOK:
                        importer.Importer.xxmi_dll_inject_mode = InjectMode.HOOK
                    # Upgrade INJECT enum.
                    case InjectModeLegacy.INJECT:
                        importer.Importer.xxmi_dll_inject_mode = InjectMode.DIRECT
                    # Handle BYPASS enum removal.
                    case InjectModeLegacy.BYPASS:
                        importer.Importer.xxmi_dll_inject_mode = InjectMode.SKIP
                log.debug(f"[{importer_name}]: Migrated INJECT_MODE {importer.Importer.custom_launch_inject_mode} -> {importer.Importer.xxmi_dll_inject_mode}")

            # Handle legacy start method.
            match importer.Importer.process_start_method:
                # Upgrade NATIVE enum.
                case ProcessStartMethodLegacy.NATIVE:
                    importer.Importer.start_method = StartMethod.NATIVE
                    log.debug(f"[{importer_name}]: Migrated START_METHOD {importer.Importer.process_start_method} -> {importer.Importer.start_method}")
                # Upgrade SHELL enum.
                case ProcessStartMethodLegacy.SHELL:
                    importer.Importer.start_method = StartMethod.SHELL
                    log.debug(f"[{importer_name}]: Migrated START_METHOD {importer.Importer.process_start_method} -> {importer.Importer.start_method}")
                # Handle MANUAL enum removal.
                case ProcessStartMethodLegacy.MANUAL:
                    importer.Importer.game_launch = GameLaunch.MANUAL
                    log.debug(f"[{importer_name}]: Migrated START_METHOD {importer.Importer.process_start_method} -> {importer.Importer.game_launch}")

            # Reset legacy options.
            importer.Importer.custom_launch_enabled = False
            importer.Importer.process_start_method = ProcessStartMethodLegacy.OPTION_REMOVED
            importer.Importer.custom_launch_inject_mode = InjectModeLegacy.OPTION_REMOVED

        return True

    # endregion


Config: AppConfig = AppConfig()
Manager: ConfigManager = ConfigManager(Config)

# Config aliases, intended to shorten dot names
Launcher: launcher_package.LauncherManagerConfig
Packages: package_manager.PackageManagerConfig
Importers: ImportersConfig
Active: (
    gimi_package.GIMIPackageConfig | srmi_package.SRMIPackageConfig
    | wwmi_package.WWMIPackageConfig | zzmi_package.ZZMIPackageConfig
    | himi_package.HIMIPackageConfig | efmi_package.EFMIPackageConfig
)


def get_resource_path(element, filename: str | Path, extensions: str | list[str] | None = None):
    filename = Path(filename)
    search_extensions = [filename.suffix]

    if extensions is not None:
        search_extensions += [ext for ext in list(extensions) if ext != filename.suffix]

    if len(filename.parts) > 1:
        class_path = filename
    else:
        class_path = element.get_resource_path() / filename

    for extension in search_extensions:
        resource_path = Config.theme_path / class_path.with_suffix(extension)
        if resource_path.is_file():
            return resource_path

    resource_path = Paths.App.Themes / 'Default' / class_path

    if not resource_path.is_file():
        raise FileNotFoundError(L('error_theme_resource_not_found', """
            Resource not found:

            {resource_path}

            Hint: You can also use other extensions: {extensions}
        """).format(
            resource_path=resource_path,
            extensions=", ".join(extensions or []))
        )

    return resource_path
