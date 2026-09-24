import logging

from core.events.path_manager import PathManagerEvents
from core.events.application import ApplicationEvents
from core.events.package_manager import PackageManagerEvents
from core.events.updater_manager import UpdaterManagerEvents
from core.events.launcher_manager import LauncherManagerEvents
from core.events.migoto_manager import MigotoManagerEvents
from core.events.model_importer import ModelImporterEvents
from core.events.gui_events import GUIEvents

log = logging.getLogger(__name__)

PathManager = PathManagerEvents
Application = ApplicationEvents
PackageManager = PackageManagerEvents
UpdaterManager = UpdaterManagerEvents
LauncherManager = LauncherManagerEvents
MigotoManager = MigotoManagerEvents
ModelImporter = ModelImporterEvents
GUI = GUIEvents

events = {}


def _log_event(event) -> bool:
    match event.__class__:
        # Skip window movement logging.
        case Application.MoveWindow:
            return False
        # Log only start and end of download.
        case PackageManager.UpdateDownloadProgress:
            if event.downloaded_bytes != 0 and event.downloaded_bytes != event.total_bytes:
                return False

    return True


def Call(event_data, **kw):
    log.debug(f'Called: {str(event_data)}')
    callbacks = events.get(event_data.__class__.__qualname__, None)
    if callbacks is not None:
        if len(callbacks) == 1:
            (event, callback, caller_id) = list(callbacks.values())[0]
            return callback(event_data, **kw)
        else:
            raise ValueError(f'Failed to call {str(event_data)}: 1 callback expected, {len(callbacks)} found!')
    else:
        raise ValueError(f'Failed to call {str(event_data)}: no callbacks found!')


def Fire(event_data, **kw):
    if _log_event(event_data):
        log.debug(f'FIRED: {str(event_data)}')
    callbacks = events.get(event_data.__class__.__qualname__, None)
    if callbacks is not None:
        for (event, callback, caller_id) in list(callbacks.values()):
            callback(event_data, **kw)


def Subscribe(event, callback, caller_id=None):
    event_name = event.__qualname__
    if event_name not in events:
        events[event_name] = {}
    callbacks = events[event_name]
    if len(callbacks) == 0:
        callback_id = f'{event_name}_0'
    else:
        last_callback_id = int(next(reversed(callbacks)).split('_')[-1])
        callback_id = f'{event_name}_{last_callback_id+1}'
    events[event_name][callback_id] = (event, callback, caller_id)
    return callback_id


def Unsubscribe(callback_id=None, event=None, callback=None, caller_id=None):
    if event is not None:
        callbacks = events.get(event.__qualname__, None)
        if callbacks is not None:
            _unsubscribe(callbacks, callback_id=callback_id, callback=callback, caller_id=caller_id)
    else:
        for callbacks in list(events.values()):
            _unsubscribe(callbacks, callback_id=callback_id, callback=callback, caller_id=caller_id)


def _unsubscribe(callbacks, callback_id=None, callback=None, caller_id=None):
    for del_callback_id, (event, del_callback, del_caller_id) in list(callbacks.items()):
        if callback_id is not None and callback_id != del_callback_id:
            continue
        if callback is not None and callback != del_callback:
            continue
        if caller_id is not None and caller_id != del_caller_id:
            continue
        del callbacks[del_callback_id]
