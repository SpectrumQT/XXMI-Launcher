import sys
import logging
import multiprocessing

from pathlib import Path

if __name__ == '__main__':
    # Multiprocessing support for Pyinstaller
    multiprocessing.freeze_support()

    if '__compiled__' in globals():
        # Nuitka (release build): `XXMI Launcher\Resources\Bin\XXMI Launcher.exe`
        root_path = Path(sys.executable).parent.parent.parent
    elif getattr(sys, 'frozen', False):
        # Pyinstaller (debug build): `XXMI Launcher\Resources\Bin\XXMI Launcher.exe`
        root_path = Path(sys.executable).parent.parent.parent
    else:
        # Python (native): `XXMI Launcher\src\xxmi_launcher\app.py`
        root_path = Path(__file__).resolve().parent.parent.parent

    # import binascii
    # arr = []
    # bytestring = binascii.unhexlify(''.join(arr))
    # test = bytestring.decode("ascii")

    logging.basicConfig(filename=root_path / 'XXMI Launcher Log.txt',
                        encoding='utf-8',
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        level=logging.DEBUG)

    logging.debug(f'App Start')

    try:
        import core.path_manager as Paths
        Paths.initialize(root_path)

        import gui.windows.main.main_window as main_window
        gui = main_window.MainWindow()

        import core.event_manager as Events

        from core.application import Application
        Application(gui)

    except BaseException as e:
        logging.exception(e)

        gui.show_messagebox(Events.Application.ShowError(
            modal=True,
            screen_center=True,
            lock_master=False,
            message=str(e),
        ))
