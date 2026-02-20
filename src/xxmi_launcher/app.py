import sys
import logging
import multiprocessing
import time

from pathlib import Path


def verify_msvc_integrity():
    """
    Does basic integrity checks of Microsoft Visual C++ Redistributable
    """

    try:
        import ctypes
    except BaseException as e:
        raise Exception(f'Failed to verify ctypes import!') from e

    msvc_dlls = [
        'msvcp140.dll',  # Common VC++ 2015-2022 DLL
        'vcruntime140.dll',  # Runtime DLL
        'vcruntime140_1.dll',  # Runtime DLL
        'ucrtbase.dll',  # Universal C Runtime DLL
    ]
    msvc_dll_handles = []

    # Check existence of MSVC++ DLLs
    for dll in msvc_dlls:
        try:
            # Load DLL from default path
            win_dll = ctypes.WinDLL(dll)
            # Cast DLL handle as c_void_p to adjust it to the platform’s bitness (32-bit or 64-bit)
            dll_handle = ctypes.cast(win_dll._handle, ctypes.c_void_p)
            # Store DLL handle for later version verification
            msvc_dll_handles.append((dll, dll_handle))
        except BaseException as e:
            raise Exception(f'Failed to verify {dll}!') from e

    # Try to load GetFileVersionInfo from win32api package
    # It's a good way to check MSVC++ by itself, as win32api requires it to function
    try:
        from win32api import GetFileVersionInfo, HIWORD, LOWORD
    except BaseException as e:
        raise Exception(f'Failed to verify win32api import!') from e

    if not callable(GetFileVersionInfo):
        raise Exception(f'Failed to verify GetFileVersionInfo being function!')
    if not callable(HIWORD):
        raise Exception(f'Failed to verify HIWORD being function!')
    if not callable(LOWORD):
        raise Exception(f'Failed to verify LOWORD being function!')

    # Create buffer to store path of loaded DLLs
    try:
        dll_path_buffer = ctypes.create_unicode_buffer(1024)

        # Read DLL versions
        dll_versions = []

        for (dll, dll_handle) in msvc_dll_handles:

            # Read path to loaded DLL from handle
            ctypes.windll.kernel32.GetModuleFileNameW(dll_handle, dll_path_buffer, 1024)

            # Get DLL version info
            version_info = GetFileVersionInfo(str(dll_path_buffer.value), '\\')

            ms_file_version = version_info['FileVersionMS']
            ls_file_version = version_info['FileVersionLS']

            version = [str(HIWORD(ms_file_version)), str(LOWORD(ms_file_version)),
                       str(HIWORD(ls_file_version)), str(LOWORD(ls_file_version))]

            dll_versions.append(f'{dll}: {".".join(version)}')

        logging.debug(f'Using MSVC++ DLLs: {str(dll_versions)}')

    except BaseException:
        pass


if __name__ == '__main__':
    # Multiprocessing support for Pyinstaller
    multiprocessing.freeze_support()

    if '__compiled__' in globals():
        # Nuitka (release build): `XXMI Launcher\Resources\Bin\XXMI Launcher.exe`
        root_path = Path(sys.argv[0]).resolve().parent.parent.parent
    elif getattr(sys, 'frozen', False):
        # Pyinstaller (debug build): `XXMI Launcher\Resources\Bin\XXMI Launcher.exe`
        root_path = Path(sys.executable).parent.parent.parent
    else:
        # Python (native): `XXMI Launcher\src\xxmi_launcher\app.py`
        root_path = Path(__file__).resolve().parent.parent.parent

    instance_id = int(time.time() * 1000) % 1000000

    logging.basicConfig(filename=root_path / 'XXMI Launcher Log.txt',
                        encoding='utf-8',
                        filemode='a',
                        format=f'%(asctime)s {instance_id:06} %(name)s %(levelname)s %(message)s',
                        level=logging.DEBUG)

    logging.debug(f'App Start')

    msvc_error = None
    gui = None

    try:
        import core.locale_manager as Locale
        Locale.initialize(root_path)

        try:
            verify_msvc_integrity()
        except BaseException as e:
            msvc_error = e

        import core.path_manager as Paths
        Paths.initialize(root_path)

        import gui.windows.main.main_window as main_window
        gui = main_window.MainWindow()

        if msvc_error is not None:
            raise msvc_error

        from core.application import Application
        Application(gui)

    except BaseException as init_error:
        # Handle init time error
        logging.exception(init_error)
        import traceback
        init_stack_trace = traceback.format_exc()

        try:
            # Try to initialize locale engine
            from core.locale_manager import L
        except BaseException:
            # Locale engine is FUBAR, fallback to dummy getter
            from textwrap import dedent
            L = lambda key, string: dedent(string.strip())

        try:
            # Try to show error in less scary message window of minimal gui
            page_link = 'https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170#latest-supported-redistributable-version'
            direct_link = 'https://aka.ms/vs/17/release/vc_redist.x64.exe'
            log_path = f'<a href="file:///{root_path / "XXMI Launcher Log.txt"}">XXMI Launcher Log.txt</a>'

            error_title = L('message_title_fatal_error', 'Fatal Error')

            if msvc_error is not None:
                error = L('error_msvc_integrity_verification_failed_md', """
                    **Microsoft Visual C++ Redistributable** is damaged or not installed!

                    Please try to reinstall it from [Microsoft Website]({page_link}) ([direct download]({direct_link})).
                    
                    Log file: {log_path}

                    Error: {error_text}
                """).format(
                    page_link=page_link,
                    direct_link=direct_link,
                    log_path=log_path,
                    error_text=msvc_error,
                )

            else:
                import core.error_manager as Errors

                if Errors.get_title(init_error):
                    # Error with title is already user-friendly
                    error_title = Errors.get_title(init_error)
                    error = init_error
                else:
                    # Wrap untitled error in more user-friendly text
                    error = L('error_launcher_crashed_on_init', """
                        Launcher has crashed during initialization:
                        
                        Log file: {log_path}
                        
                        Error: {error_text}
                    """).format(
                        log_path=log_path,
                        error_text=init_stack_trace,
                    )

            gui.show_messagebox(
                modal=True,
                title=error_title,
                message=error,
            )

        except BaseException as gui_error:
            # Fallback to the most basic messagebox
            logging.exception(gui_error)

            log_path = root_path / "XXMI Launcher Log.txt"

            if msvc_error is not None:
                error = L('error_msvc_integrity_verification_failed_plain', """
                    Microsoft Visual V C++ Redistributable is damaged or not installed!

                    Please reinstall it from https://aka.ms/vs/17/release/vc_redist.x64.exe
                    
                    Log file: {log_path}

                    Error: {error_text}
                """).format(
                    log_path=log_path,
                    error_text=msvc_error,
                )
            else:
                error = L('error_launcher_crashed_on_init', """
                    Launcher has crashed during initialization:
                    
                    Log file: {log_path}
                    
                    Error: {error_text}
                """).format(
                    log_path=log_path,
                    error_text=init_stack_trace,
                )

            from tkinter.messagebox import showerror
            showerror(
                title=f'XXMI Launcher - {L('message_title_fatal_error', 'Fatal Error')}',
                message=error,
            )
