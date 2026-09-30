from typing import Union, Callable, List, Optional
from dataclasses import dataclass, field

from core.locale_manager import L


@dataclass
class ApplicationEvents:

    @dataclass
    class ConfigUpdate:
        pass

    @dataclass
    class OpenSettings:
        wait_window: bool = False
        tab_name: str = ''

    @dataclass
    class CloseSettings:
        save: bool = False

    @dataclass
    class LoadImporter:
        importer_id: str
        reload: bool = False

    @dataclass
    class ToggleImporter:
        importer_id: str

    @dataclass
    class Ready:
        pass

    @dataclass
    class Busy:
        pass

    @dataclass
    class RunPreLaunch:
        cmd: str = ''

    @dataclass
    class Launch:
        pass

    @dataclass
    class RunPostLoad:
        cmd: str = ''

    @dataclass
    class StatusUpdate:
        status: str

    @dataclass
    class MoveWindow:
        offset_x: int
        offset_y: int

    @dataclass
    class Minimize:
        pass

    @dataclass
    class Maximize:
        pass

    @dataclass
    class Close:
        delay: int = 0
        pass

    @dataclass
    class Restart:
        delay: int = 0

    @dataclass
    class LoadLocale:
        locale_name: str
        skip_reload: bool = False

    @dataclass
    class Update:
        no_install: bool = False
        no_check: bool = False
        force: bool = False
        reinstall: bool = False
        packages: Union[list, None] = None
        silent: bool = False
        no_thread: bool = False

    @dataclass
    class CheckForUpdates:
        pass

    @dataclass
    class SetupHook:
        library_name: str
        process_name: str

    @dataclass
    class Inject:
        library_name: str
        process_name: str

    @dataclass
    class Bypass:
        process_name: str

    @dataclass
    class WaitForProcess:
        process_name: str

    @dataclass
    class StartGameExe:
        process_name: str

    @dataclass
    class VerifyHook:
        library_name: str
        process_name: str

    @dataclass
    class ShowMessage:
        modal: bool = False
        title: str = field(default_factory=lambda: L('message_title_message', 'Message'))
        message: str = '< Text >'
        confirm_text: str = field(default_factory=lambda: L('message_button_ok', 'OK'))
        confirm_command: Optional[Callable] = None
        cancel_text: str = ''
        cancel_command: Optional[Callable] = None
        radio_options: Optional[List[str]] = None
        checkbox_options: Optional[List[str]] = None
        selected_id: int = 0

    @dataclass
    class ShowError(ShowMessage):
        title: str = field(default_factory=lambda: L('message_title_error', 'Error'))

    @dataclass
    class ShowWarning(ShowMessage):
        title: str = field(default_factory=lambda: L('message_title_warning', 'Warning'))

    @dataclass
    class ShowInfo(ShowMessage):
        title: str = field(default_factory=lambda: L('message_title_info', 'Info'))

    @dataclass
    class ShowDialogue(ShowMessage):
        confirm_text: str = field(default_factory=lambda: L('message_button_confirm', 'Confirm'))
        cancel_text: str = field(default_factory=lambda: L('message_button_cancel', 'Cancel'))

    @dataclass
    class OpenDonationCenter:
        mode: str = 'NORMAL'
        model_importer: str = ''
        launch_count: int = 0