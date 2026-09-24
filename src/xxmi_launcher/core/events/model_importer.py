from dataclasses import dataclass


@dataclass
class ModelImporterEvents:

    @dataclass
    class Install:
        pass

    @dataclass
    class StartGame:
        pass

    @dataclass
    class ValidateGameFolder:
        game_folder: str

    @dataclass
    class CreateShortcut:
        pass

    @dataclass
    class DetectGameFolder:
        pass

    @dataclass
    class OptimizeMods:
        silent: bool = True
        reset_cache: bool = False
