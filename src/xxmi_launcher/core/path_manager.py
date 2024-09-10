import os

from pathlib import Path
from dataclasses import dataclass, fields


def assert_path(directory_path: Path):
    if not directory_path.exists():
        return assert_path(directory_path.parent)
    if not directory_path.is_absolute():
        raise ValueError(f"Directory path '{directory_path}' is not absolute!")
    if not os.access(directory_path, os.R_OK):
        raise ValueError(f"Can't read from '{directory_path}' folder!")
    if not os.access(directory_path, os.W_OK):
        raise ValueError(f"Can't write to '{directory_path}' folder!")
    if not os.access(directory_path, os.X_OK):
        raise ValueError(f"Can't run .exe in '{directory_path}' folder!")
    try:
        os.listdir(directory_path)
    except Exception as e:
        raise ValueError(f"Can't access '{directory_path}' folder!") from e


def verify_path(directory_path: Path):
    if not directory_path.exists():
        assert_path(directory_path.parent)
    else:
        if not directory_path.is_dir():
            raise ValueError(f"Path '{directory_path}' is not a folder!")
        assert_path(directory_path)
    directory_path.mkdir(parents=True, exist_ok=True)
    assert_path(directory_path)


@dataclass
class Paths:
    Root: Path = Path('')
    Resources: Path = Path('Resources')
    Themes: Path = Path('Themes')
    Downloads: Path = Path('Downloads')
    Backups: Path = Path('Backups')

    def set_root_path(self, root_path: Path):
        for field in fields(self):
            path = self.__getattribute__(field.name)
            if not path.is_absolute():
                self.__setattr__(field.name, root_path / path)
            else:
                raise ValueError(f'Cannot set root "{root_path}" for absolute path "{path}"!')

    def verify(self):
        for path in self.__dict__.values():
            verify_path(path)


App = Paths()


def initialize(root_path: Path):
    App.set_root_path(root_path)
    App.verify()
