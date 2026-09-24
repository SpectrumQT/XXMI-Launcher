from dataclasses import dataclass


@dataclass
class LauncherManagerEvents:

    @dataclass
    class Update:
        pass

    @dataclass
    class CreateShortcut:
        pass
