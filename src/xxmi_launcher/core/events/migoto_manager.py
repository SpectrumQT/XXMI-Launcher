from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MigotoManagerEvents:

    @dataclass
    class OpenModsFolder:
        pass

    @dataclass
    class StartAndInject:
        game_exe_path: Path
        start_exe_path: Path
        start_args: list[str] = field(default_factory=lambda: [])
        work_dir: str = None
        use_hook: bool = True
