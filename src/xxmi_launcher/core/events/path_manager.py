from pathlib import Path
from dataclasses import dataclass

@dataclass
class PathManagerEvents:

    @dataclass
    class VerifyFileAccess:
        path: Path
        abs_path: bool = True
        read: bool = True
        write: bool = False
        exe: bool = False
        extension_filter: str | list[str] | None = None

    @dataclass
    class WriteFile:
        path: Path
        size: int

    @dataclass
    class RemovePath:
        path: Path

    @dataclass
    class RenamePath:
        src_path: Path
        dst_path: Path

    @dataclass
    class CopyFile:
        src_path: Path
        dst_path: Path

    @dataclass
    class CopyDirectory:
        src_path: Path
        dst_path: Path
