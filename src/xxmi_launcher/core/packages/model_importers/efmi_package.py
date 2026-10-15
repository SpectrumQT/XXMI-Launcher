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
        "Launcher.exe",
    },
    display_names={
        "GRYPHLINK",
    },
    known_paths={
        Path("C:/Program Files/GRYPHLINK/Launcher.exe"),
        Path("C:/Program Files (x86)/GRYPHLINK/Launcher.exe"),
    },
    known_registry_paths={
        RegistryValuePath(root=winreg.HKEY_CURRENT_USER,
                          key=r"Software\GRYPHLINK\Launcher\94005b4608518100ed8df1d8107356a8", value="install_path"),
    },
    expected_relative_paths={
        "GRYPHLINK",
    },
)


@dataclass
class EFMIConfig(ModelImporterConfig):
    game: Game = Game.ARKNIGHTS_ENDFIELD
    game_exe_names: list[str] = field(default_factory=lambda: ['Endfield.exe'])
    game_folder_names: list[str] = field(default_factory=lambda: ['EndField Game'])
    game_folder_children: list[str] = field(default_factory=lambda: ['Endfield_Data'])
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

        parent_exe = None

        # Handle EGS installation.
        launcher_candidate_path = game_exe_path.parent.parent.parent
        if (launcher_candidate_path / "Launcher.exe").is_file():
            parent_exe = self.find_launcher_exe(launcher_candidate_path)

        # Hande GRYPHLINK installation.
        if not parent_exe:
            locator = AppLocator(APP_INFO)
            launcher_exe_path = locator.find()

            if launcher_exe_path:
                parent_exe = self.find_launcher_exe(launcher_exe_path.parent)

        if not parent_exe:
            raise ValueError(f"Cannot find GRYPHLINK launcher file Games.exe")

        CREATE_SUSPENDED = 0x00000004
        CREATE_NO_WINDOW = 0x08000000

        parent_launch_context = LaunchContext(
            start_method=StartMethod.NATIVE,
            process_name="Games.exe",
            target=ExecutableLaunch(
                exe_path=parent_exe,
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
