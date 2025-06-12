
from core.locale_manager import L, T
import core.event_manager as Events
import core.path_manager as Paths
import core.config_manager as Config
import gui.vars as Vars

from gui.events import Stage
from gui.classes.containers import UIFrame
from gui.classes.widgets import UIButton, UIText, UIProgressBar, UILabel, UIImageButton, UIImage


class BottomBarFrame(UIFrame):
    def __init__(self, master, canvas, width, height, **kwargs):
        super().__init__(master=master, canvas=canvas, **kwargs)

        self.set_background_image(image_path='background-image.png', width=width, height=240, y=500)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.put(LeftStatusText(self))
        self.put(RightStatusText(self))
        self.put(DownloadProgressBar(self)).grid(row=0, column=0, padx=0, pady=(0, 0), sticky='swe')
        self.put(InstallationProgressBar(self)).grid(row=0, column=0, padx=0, pady=(0, 0), sticky='swe')

        self.subscribe(Events.GUI.LauncherFrame.StageUpdate, self.handle_stage_update)

    def handle_stage_update(self, event):
        if event.stage == Stage.Busy or event.stage == Stage.Download:
            self.grid()
            self.background_image.configure(opacity=1)
        else:
            self.grid_remove()
            self.background_image.configure(opacity=0.75)


class DownloadProgressBar(UIProgressBar):
    def __init__(self, master):
        super().__init__(
            orientation='horizontal',
            height=18,
            corner_radius=0,
            master=master)
        self.subscribe_show(Events.GUI.LauncherFrame.StageUpdate, lambda event: event.stage == Stage.Download)
        self.subscribe(
            Events.PackageManager.StartDownload,
            lambda event: self.initialize_download())
        self.subscribe(
            Events.PackageManager.UpdateDownloadProgress,
            lambda event: self.update_progress(event.downloaded_bytes, event.total_bytes))
        self.subscribe(
            Events.PackageManager.StartDownload,
            lambda event: self.initialize_download())

    def initialize_download(self):
        self.set(100)
        self.set(0)

    def update_progress(self, downloaded_bytes, total_bytes):
        progress = downloaded_bytes / total_bytes
        self.set(progress)


class InstallationProgressBar(UIProgressBar):
    def __init__(self, master):
        super().__init__(
            mode='indeterminate',
            orientation='horizontal',
            height=18,
            corner_radius=0,
            master=master)
        self.subscribe_show(Events.GUI.LauncherFrame.StageUpdate, lambda event: event.stage == Stage.Busy)

        self.subscribe(
            Events.Application.Ready,
            lambda event: self.stop())
        self.subscribe(
            Events.Application.Launch,
            lambda event: self.start())
        self.subscribe(
            Events.Application.Busy,
            lambda event: self.start())


class LeftStatusText(UIText):
    def __init__(self, master):
        super().__init__(x=15,
                         y=664,
                         text='',
                         font=('Roboto', 19),
                         fill='#f0f0f0',
                         activefill='#f0f0f0',
                         anchor='nw',
                         master=master)

        # Show widget only during Download or Installation
        self.subscribe_show(
            Events.GUI.LauncherFrame.StageUpdate,
            lambda event: event.stage == Stage.Download or event.stage == Stage.Busy)

        # Application Events
        self.subscribe_set(
            Events.Application.Launch,
            lambda event: str(L('bottom_bar_initializing_launch', 'Initializing game launch...')))
        self.subscribe_set(
            Events.Application.SetupHook,
            lambda event: str(L('bottom_bar_hooking', 'Hooking {library} to {process}...').format(library=event.library_name, process=event.process_name)))
        self.subscribe_set(
            Events.Application.VerifyHook,
            lambda event: str(L('bottom_bar_verifying_hook', 'Verifying {library} load into {process}...').format(library=event.library_name, process=event.process_name)))
        self.subscribe_set(
            Events.Application.Inject,
            lambda event: str(L('bottom_bar_injecting', 'Injecting {library} to {process}...').format(library=event.library_name, process=event.process_name)))
        self.subscribe_set(
            Events.Application.StartGameExe,
            lambda event: str(L('bottom_bar_launching_game', 'Launching game...')))
        self.subscribe_set(
            Events.Application.WaitForProcess,
            lambda event: str(L('bottom_bar_waiting_process', 'Waiting for {process} to start...').format(process=event.process_name)))
        self.subscribe_set(
            Events.Application.Close,
            lambda event: str(L('bottom_bar_closing_launcher', 'Closing launcher...')))
        self.subscribe_set(
            Events.Application.StatusUpdate,
            lambda event: event.status)

        # PackageManager Action Events
        self.subscribe_set(
            Events.PackageManager.StartCheckUpdate,
            lambda event: str(L('bottom_bar_checking_updates', 'Checking for updates...')))

        # PackageManager Download Events
        self.subscribe_set(
            Events.PackageManager.InitializeDownload,
            lambda event: str(L('bottom_bar_connecting_github', 'Connecting to GitHub...')))
        self.subscribe_set(
            Events.PackageManager.StartDownload,
            lambda event: str(L('bottom_bar_downloading', 'Downloading {asset}...').format(asset=event.asset_name)))
        self.subscribe_set(
            Events.PackageManager.StartIntegrityVerification,
            lambda event: str(L('bottom_bar_verifying_integrity', 'Verifying {asset} integrity...').format(asset=event.asset_name)))

        # PackageManager Installation Events
        self.subscribe_set(
            Events.PackageManager.InitializeInstallation,
            lambda event: str(L('bottom_bar_initializing_installation', 'Initializing update installation...')))
        self.subscribe_set(
            Events.PackageManager.StartFileWrite,
            lambda event: str(L('bottom_bar_writing_file', 'Writing {asset} on disk...').format(asset=event.asset_name)))
        self.subscribe_set(
            Events.PackageManager.StartFileMove,
            lambda event: str(L('bottom_bar_moving_file', 'Moving {asset}...').format(asset=event.asset_name)))
        self.subscribe_set(
            Events.PackageManager.StartUnpack,
            lambda event: str(L('bottom_bar_unpacking', 'Unpacking {asset}...').format(asset=event.asset_name)))


class RightStatusText(UIText):
    def __init__(self, master):
        super().__init__(x=1265,
                         y=664,
                         text='',
                         font=('Roboto', 19),
                         fill='#f0f0f0',
                         activefill='#f0f0f0',
                         anchor='ne',
                         master=master)
        self.subscribe_show(
            Events.GUI.LauncherFrame.StageUpdate,
            lambda event: event.stage == Stage.Download)
        self.subscribe(
            Events.PackageManager.UpdateDownloadProgress,
            lambda event: self.update_progress(event.downloaded_bytes, event.total_bytes))

    def update_progress(self, downloaded_bytes, total_bytes):
        progress = downloaded_bytes / total_bytes
        progress_text = '%.2f%% (%s/%s)' % (progress * 100, self.format_size(downloaded_bytes), self.format_size(total_bytes))
        self.set(progress_text)

    @staticmethod
    def format_size(num_bytes):
        units = ('B', 'KB', 'MB', 'GB', 'TB')
        for power, unit in enumerate(units):
            if num_bytes < 1024 ** (power + 1):
                return '%.2f%s' % (num_bytes / 1024 ** power, unit)
