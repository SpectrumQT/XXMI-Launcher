from dataclasses import dataclass
from pathlib import Path


@dataclass
class UpdaterManagerEvents:

    @dataclass
    class UpdateLauncher:
        downloaded_asset_path: Path
