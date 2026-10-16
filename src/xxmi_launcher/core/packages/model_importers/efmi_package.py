import re
import logging
import winreg

from dataclasses import dataclass, field
from typing import Any, Iterable
from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.locale_manager import L
from core.package_manager import PackageMetadata

from core.config.enums import GameLaunch, InjectMode, StartMethod
from core.packages.model_importers.model_importer import ModelImporterPackage, ModelImporterConfig, Version
from core.packages.migoto_package import MigotoManagerConfig
from core.platforms.game import Game
from core.utils.process_manager import ProcessManager, ProcessPriorityClass, LaunchContext, ExecutableLaunch
from core.platforms.app_locator import RegistryValuePath, AppInfo, AppLocator

log = logging.getLogger(__name__)


APP_INFO = AppInfo(
    exe_names={
        "Games.exe",
    },
    display_names={
        "GRYPHLINK",
        "hypergryph launcher",
        "鹰角启动器",
    },
    known_paths={
        Path("C:/Program Files/GRYPHLINK/Launcher.exe"),
        Path("C:/Program Files/Hypergryph Launcher/Launcher.exe"),
        Path("C:/Program Files (x86)/GRYPHLINK/Launcher.exe"),
        Path("C:/Program Files (x86)/Hypergryph Launcher/Launcher.exe"),
    },
    known_registry_paths={
        RegistryValuePath(
            root=winreg.HKEY_CURRENT_USER,
            key=r"Software\GRYPHLINK\Launcher\94005b4608518100ed8df1d8107356a8", value="install_path"
        ),
    },
)


@dataclass
class EFMIConfig(ModelImporterConfig):
    game: Game = Game.ARKNIGHTS_ENDFIELD
    game_exe_names: list[str] = field(default_factory=lambda: ['Endfield.exe'])
    game_folder_names: list[str] = field(default_factory=lambda: ['EndField Game'])
    game_folder_children: list[str] = field(default_factory=lambda: ['Endfield_Data'])
    launcher_folder_names: list[str] = field(default_factory=lambda: ["GRYPHLINK", "Hypergryph Launcher"])
    launcher_folder_files: list[str] = field(default_factory=lambda: ["Launcher.exe"])
    game_process_exe: str = "Endfield.exe"
    process_timeout: int = 60
    importer_folder: str = 'EFMI/'
    launch_options: str = ''
    d3d11_mode_cmd_args: str = "-force-d3d11"
    xxmi_dll_inject_mode: InjectMode = InjectMode.DIRECT
    d3dx_ini: dict[str, dict[str, dict[str, Any]]] = field(default_factory=lambda: {
        'core': {
            'Loader': {
                'loader': 'XXMI Launcher.exe',
            },
        },
        'enforce_rendering': {
            'Rendering': {
                'texture_hash': 0,
                'track_texture_updates': 0,
                'track_region_hashes': 1,
                'track_implicit_index_buffers': 1,
                'allow_buffer_resize': 0,
            },
        },
        'enable_hunting': {
            'Hunting': {
                'hunting': {'on': 2, 'off': 0},
            },
        },
        'dump_shaders': {
            'Hunting': {
                'marking_actions': {'on': 'clipboard hlsl asm regex', 'off': 'clipboard'},
            },
        },
    })


@dataclass
class EFMIPackageConfig:
    Importer: EFMIConfig = field(
        default_factory=lambda: EFMIConfig()
    )
    Migoto: MigotoManagerConfig = field(
        default_factory=lambda: MigotoManagerConfig()
    )


class EFMIPackage(ModelImporterPackage):
    def __init__(self):
        super().__init__(PackageMetadata(
            package_name='EFMI',
            auto_load=False,
            github_repo_owner='SpectrumQT',
            github_repo_name='EFMI-Package',
            asset_version_pattern=r'.*(\d\.\d\.\d).*',
            asset_name_format='EFMI-PACKAGE-v%s.zip',
            signature_pattern=r'^## Signature[\r\n]+- ((?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2}))\r?$',
            signature_public_key='MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEYac352uRGKZh6LOwK0fVDW/TpyECEfnRtUp+bP2PJPP63SWOkJ3a/d9pAnPfYezRVJ1hWjZtpRTT8HEAN/b4mWpJvqO43SAEV/1Q6vz9Rk/VvRV3jZ6B/tmqVnIeHKEb',
            exit_after_update=False,
            installation_path='EFMI/',
            requirements=['XXMI'],
            required_versions={'XXMI': '0.7.5'},
        ))
        self.autodetect_patterns = {
            'common': re.compile(r'([a-zA-Z]:[^:\"\']*EndField[^:\"\']*)'),
        }
        self.autodetect_files = {
            '{APPDATA}/LocalLow/Gryphline/Endfield/Player.log': ['common'],
        }
        self.autodetect_known_paths = [
            r"C:\Program Files\GRYPHLINK\games\EndField Game",
            r"D:\GRYPHLINK\games\EndField Game"
        ]

    @staticmethod
    def get_latest_version_path(paths: Iterable[Path]) -> Path:
        return max(paths, key=lambda path: tuple(map(int, path.parent.name.split("."))))

    @staticmethod
    def find_launcher_exe(launcher_path: Path) -> Path | None:
        candidates = []
        for path in launcher_path.iterdir():
            if path.is_file():
                continue
            exe_path = path / "Games.exe"
            if exe_path.is_file():
                candidates.append(exe_path)
        if not candidates:
            return None
        return EFMIPackage.get_latest_version_path(candidates)

    def validate_folder_path(self, folder_path: Path | str) -> Path:
        folder_path = Path(folder_path)
        if not str(folder_path) or str(folder_path) == '.':
            raise ValueError(L("error_text_folder_not_specified", "Folder is not specified!"))
        if not folder_path.is_absolute():
            raise ValueError(L("error_text_folder_not_absolute", "Specified folder path is not absolute!"))
        if not folder_path.is_dir():
            raise ValueError(L("error_text_folder_not_found", "Specified folder is not found!"))
        return folder_path

    def normalize_game_launcher_folder(self, launcher_folder_path: Path | str) -> Path:
        launcher_folder_path = self.validate_folder_path(launcher_folder_path)
        if (launcher_folder_path / "Launcher.exe").is_file():
            return launcher_folder_path
        if (launcher_folder_path.parent / "Launcher.exe").is_file():
            return launcher_folder_path.parent
        raise ValueError(L("error_text_file_not_found_in_dir", """
            Failed to find `{file_name}` in specified folder!
        """).format(
            file_name="Launcher.exe"
        ))

    def validate_game_launcher_folder(self, launcher_folder_path: Path) -> Path:
        launcher_folder_path = self.normalize_game_launcher_folder(launcher_folder_path)
        launcher_exe_path = self.find_launcher_exe(launcher_folder_path)
        if launcher_exe_path is not None:
            return launcher_exe_path
        raise ValueError((L("error_text_file_not_found_in_subdir", """
            Failed to find `{file_name}` in subfolders!
        """).format(
            file_name="Games.exe"
        )))

    def notify_launcher_folder_not_configured(self):
        user_requested_settings = Events.Call(Events.Application.ShowError(
            title=L('message_title_launcher_folder_not_configured', "Official Launcher Folder Not Configured"),
            message=L('message_text_launcher_folder_not_configured', """
                Please set **{general_settings_launcher_folder_label}** option of **General Settings**.
            """),
            confirm_text=L('message_button_open_settings', 'Open Settings'),
            cancel_text=L('message_button_cancel', 'Cancel'),
            modal=True,
        ))

        if user_requested_settings:
            Events.Fire(Events.Application.OpenSettings())

    def notify_launcher_folder_detection_failure(self):
        user_requested_settings = Events.Call(Events.Application.ShowError(
            title=L('message_title_launcher_detection_failed', "Game Launcher Not Found"),
            message=L('message_text_launcher_detection_failed', """
                Could not find the official launcher on your device.
    
                Please set the **{general_settings_launcher_folder_label}** manually in **General Settings**.
            """),
            confirm_text=L('message_button_open_settings', 'Open Settings'),
            cancel_text=L('message_button_cancel', 'Cancel'),
            modal=True,
        ))

        if user_requested_settings:
            Events.Fire(Events.Application.OpenSettings())

    def notify_launcher_folder_detection(self, folders_index):
        if len(folders_index) == 1:
            folder_id = 0
            user_confirmed_launcher_folder = Events.Call(Events.Application.ShowInfo(
                title=L('message_title_launcher_detected_single', "Official Launcher Found"),
                message=L('message_text_launcher_detected_single', """
                    Please confirm that this is the correct **{general_settings_launcher_folder_label}**:
                    ```
                    {launcher_folder}
                    ```
                    Alternatively, set it manually in **General Settings**.
                """).format(launcher_folder=folders_index[0]),
                confirm_text=L('message_button_confirm', 'Confirm'),
                cancel_text=L('message_button_open_settings', 'Open Settings'),
                modal=True,
            ))
            if user_confirmed_launcher_folder is None:
                user_confirmed_launcher_folder = True
        else:
            folders_index = [
                L("detected_launcher", "Detected launcher") + f" {i + 1}" + f"<pre><code>{launcher_folder}</code></pre>"
                for i, launcher_folder in enumerate(folders_index)
            ]
            (user_confirmed_launcher_folder, folder_id) = Events.Call(Events.Application.ShowWarning(
                title=L('message_title_launcher_detected_multiple', "Multiple Official Launchers Found"),
                message=L('message_text_launcher_detected_multiple', """
                    Please select the correct **{general_settings_launcher_folder_label}** below, or set it in **General Settings**.

                """),
                confirm_text=L('message_button_confirm', 'Confirm'),
                cancel_text=L('message_button_open_settings', 'Open Settings'),
                radio_options=folders_index,
                modal=True,
            ))
        return user_confirmed_launcher_folder, folder_id

    def get_game_launcher_folder_candidates(self) -> list[Path]:
        launcher_folder_candidates = []

        # Handle EGS installation.
        if Config.Importers.EFMI.Importer.game_folder:
            game_folder = Path(Config.Importers.EFMI.Importer.game_folder)
            try:
                launcher_exe_path = self.validate_game_launcher_folder(game_folder)
                launcher_folder_candidates.append(game_folder)
            except:
                pass

        # Handle GRYPHLINK installation.
        if not launcher_folder_candidates:
            locator = AppLocator(APP_INFO)

            for exe_path in locator.find_all():
                launcher_folder_candidate = exe_path.parent.parent
                try:
                    launcher_exe_path = self.validate_game_launcher_folder(launcher_folder_candidate)
                    launcher_folder_candidates.append(launcher_folder_candidate)
                except:
                    pass

        return launcher_folder_candidates

    def detect_game_launcher_folder(self):

        Events.Fire(Events.Application.StatusUpdate(status=L("status_detecting_game_launcher", """
            Detecting official launcher installation folder...
        """)))

        try:
            launcher_folder_candidates = self.get_game_launcher_folder_candidates()

            # Notify user if there are no launcher folders detected
            if len(launcher_folder_candidates) == 0:
                self.notify_launcher_folder_detection_failure()
                # User is already notified, lets skip error popup
                raise UserWarning

            # Notify user if about launcher folder detection, ask which to use if there are more than 1 folder found
            (user_confirmed_launcher_folder, launcher_folder_id) = self.notify_launcher_folder_detection(launcher_folder_candidates)
            if user_confirmed_launcher_folder is None:
                # User neither confirmed detection result nor decided to open settings
                # With multiple launcher installations detected it might end up miserably, lets show them error
                raise Exception

            # Set folder with selected launcher_folder_id as launcher folder
            launcher_folder = launcher_folder_candidates[launcher_folder_id]

            Config.Importers.EFMI.Importer.launcher_folder = str(launcher_folder)

        except UserWarning:
            # Upcast UserWarning
            raise UserWarning

        except Exception as e:
            self.notify_launcher_folder_not_configured()
            # User is already notified, lets skip error popup
            raise UserWarning

        return launcher_folder

    def override_launch_context(
        self,
        launch_context: LaunchContext,
        game_path: Path | None,
        game_exe_path: Path | None,
    ) -> None:
        if Config.Importers.EFMI.Importer.game_launch != GameLaunch.DIRECT:
            return

        if Config.Importers.EFMI.Importer.start_method != StartMethod.NATIVE:
            return

        if game_exe_path is None:
            return

        if not isinstance(launch_context.target, ExecutableLaunch):
            return

        # Steam version doesn't have GRYPHLINK launcher requirement nonsense.
        if "steamapps" in launch_context.target.exe_path.parts:
            return

        if not Config.Importers.EFMI.Importer.launcher_folder:
            self.detect_game_launcher_folder()

        launcher_exe_path = self.validate_game_launcher_folder(Path(Config.Importers.EFMI.Importer.launcher_folder))

        CREATE_SUSPENDED = 0x00000004
        CREATE_NO_WINDOW = 0x08000000

        parent_launch_context = LaunchContext(
            start_method=StartMethod.NATIVE,
            process_name="Games.exe",
            target=ExecutableLaunch(
                exe_path=launcher_exe_path,
                cmd_args="",
            ),
            process_flags=CREATE_SUSPENDED | CREATE_NO_WINDOW
        )

        parent_process = ProcessManager(parent_launch_context)

        if parent_process.is_running():
            if not parent_process.stop(timeout=5):
                raise ValueError(f"Failed to stop already running GRYPHLINK launcher process Games.exe")

        parent_process.start()

        if not parent_process.wait_until_running(timeout=15):
            raise ValueError(f"Failed to start GRYPHLINK launcher process Games.exe")

        launch_context.parent_process = parent_process

    def get_installed_version(self):
        try:
            return str(Version(Config.Importers.EFMI.Importer.importer_path / 'Core' / 'EFMI' / 'main.ini'))
        except Exception as e:
            return ''
