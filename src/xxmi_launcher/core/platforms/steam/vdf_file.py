import vdf

from pathlib import Path
from typing import Any

import core.path_manager as Paths


class VdfFile:
    """
    Read and write a Valve VDF file.

    This class is intentionally unaware of Steam-specific structure.
    It only handles file I/O and VDF serialization.

    Example:
        config = VdfFile(Path("localconfig.vdf"))

        data = config.load()
        data["some"]["value"] = "example"
        config.save(data)
    """

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, Any]:
        """
        Load and deserialize the VDF file.

        Returns:
            The parsed VDF document.

        Raises:
            FileNotFoundError: If the file does not exist.
            OSError: If the file cannot be read.
            vdf.VDFError: If the file contains invalid VDF.
        """

        config_text = Paths.App.read_text(self.path)
        return vdf.loads(config_text)

        # with self.path.open("r", encoding="utf-8") as file:
        #     return vdf.load(file)

    def save(self, data: dict[str, Any]) -> None:
        """
        Serialize and write a VDF document.

        Args:
            data: VDF document to write.

        Raises:
            OSError: If the file cannot be written.
        """

        config_text = vdf.dumps(data, pretty=True)
        Paths.App.write_file(self.path, config_text)

        # with self.path.open("w", encoding="utf-8") as file:
        #     vdf.dump(data, file, pretty=True)

    def exists(self) -> bool:
        """
        Return True if the VDF file exists.
        """
        return self.path.is_file()
