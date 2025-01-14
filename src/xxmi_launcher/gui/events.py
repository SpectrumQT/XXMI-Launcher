
from dataclasses import dataclass
from enum import Enum, auto


class Stage(Enum):
    Ready = auto()
    Busy = auto()
    Download = auto()


@dataclass
class GUIEvents:

    @dataclass
    class LauncherFrame:

        @dataclass
        class StageUpdate:
            stage: Stage

        @dataclass
        class ToggleToolbox:
            show: bool = False
            hide_on_leave: bool = False

        @dataclass
        class ToggleImporter:
            importer_id: str
            index: int
            show: bool = False

        @dataclass
        class HoverImporter:
            importer_id: str
            hover: bool = False

    @dataclass
    class ToggleThemeDevMode:
        enabled: bool = False
