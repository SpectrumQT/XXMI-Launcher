import core.event_manager as Events
import core.path_manager as Paths
import core.config_manager as Config
import gui.vars as Vars

from gui.events import Stage
from gui.classes.containers import UIFrame
from gui.classes.widgets import UIButton, UIText, UIProgressBar, UILabel, UIImageButton, UIImage
from gui.windows.main.launcher_frame.top_bar import TopBarFrame
from gui.windows.main.launcher_frame.bottom_bar import BottomBarFrame
from gui.windows.main.launcher_frame.tool_bar import ToolBarFrame


class LauncherFrame(UIFrame):
    def __init__(self, master):
        super().__init__(master, width=master.cfg.width, height=master.cfg.height, fg_color='transparent')

        self.current_stage = None
        self.staged_widgets = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Background
        self.canvas.grid(row=0, column=0)

        def upd_bg(event):
            self.set_background_image(Config.get_resource_path(self) / f'background-image-{event.importer_id.lower()}.jpg', width=master.cfg.width, height=master.cfg.height)
        upd_bg(Events.Application.LoadImporter(importer_id=Config.Launcher.active_importer))
        self.subscribe(Events.Application.LoadImporter, upd_bg)

        self.put(ImporterVersionText(self))
        self.put(LauncherVersionText(self))

        # Top Panel
        self.put(TopBarFrame(self, self.canvas))

        # Bottom Panel
        self.put(BottomBarFrame(self, self.canvas, width=master.cfg.width, height=master.cfg.height)).grid(row=0, column=0, sticky='swe')

        # Action Panel
        self.put(UpdateButton(self))
        tools_button = self.put(ToolsButton(self))
        self.put(StartButton(self, tools_button))
        self.put(InstallButton(self, tools_button))
        self.put(ToolBarFrame(self, self.canvas))

        # Application Events
        self.subscribe(
            Events.Application.Ready,
            lambda event: Events.Fire(Events.GUI.LauncherFrame.StageUpdate(Stage.Ready)))
        self.subscribe(
            Events.PackageManager.InitializeDownload,
            lambda event: Events.Fire(Events.GUI.LauncherFrame.StageUpdate(Stage.Download)))
        self.subscribe(
            Events.Application.Busy,
            lambda event: Events.Fire(Events.GUI.LauncherFrame.StageUpdate(Stage.Busy)))


class ImporterVersionText(UIText):
    def __init__(self, master):
        super().__init__(x=20,
                         y=95,
                         text='',
                         font='Roboto 14',
                         fill='#cccccc',
                         activefill='white',
                         anchor='nw',
                         master=master)
        self.subscribe_set(
            Events.PackageManager.VersionNotification,
            lambda event: f'{Config.Launcher.active_importer} ' + (event.package_states[
                Config.Launcher.active_importer].installed_version or 'Not Installed!'))
        # self.subscribe_show(
        #     Events.GUI.LauncherFrame.StageUpdate,
        #     lambda event: event.stage == Stage.Ready)


class MainActionButton(UIImageButton):
    def __init__(self, **kwargs):
        self.command = kwargs['command']
        defaults = {}
        defaults.update(
            y=640,
            height=64,
            button_normal_opacity=0.95,
            button_hover_opacity=1,
            button_normal_brightness=0.95,
            button_hover_brightness=1,
            button_selected_brightness=0.8,
            bg_normal_opacity=0.95,
            bg_hover_opacity=1,
            bg_normal_brightness=0.95,
            bg_hover_brightness=1,
            bg_selected_brightness=0.8,
        )
        defaults.update(kwargs)
        super().__init__(**defaults)


class UpdateButton(MainActionButton):
    def __init__(self, master):
        super().__init__(
            x=800,
            width=64,
            button_image_path='button-update.png',
            command=lambda: Events.Fire(Events.Application.Update(force=True)),
            master=master)
        self.stage = None
        self.set_tooltip('Update packages to latest versions', delay=0.01)
        self.subscribe(Events.PackageManager.VersionNotification, self.handle_version_notification)
        self.subscribe(Events.GUI.LauncherFrame.StageUpdate, self.handle_stage_update)

    def handle_stage_update(self, event):
        self.stage = event.stage
        self.show(self.stage == Stage.Ready)

    def handle_version_notification(self, event):
        pending_update_message = []
        for package_name, package in event.package_states.items():
            if (package.installed_version != package.latest_version) and package.latest_version != '' and package.installed_version != '':
                pending_update_message.append(
                    f'{package_name}: {package.installed_version} -> {package.latest_version}')
        if len(pending_update_message) > 0:
            self.enabled = True
            self.set_tooltip('Update packages to latest versions:\n' + '\n'.join(pending_update_message))
            self.show(self.stage == Stage.Ready)
        else:
            self.enabled = False
            self.set_tooltip('No updates available!')
            self.hide()


class StartButton(MainActionButton):
    def __init__(self, master, tools_button):
        super().__init__(
            x=1023,
            width=32,
            height=32,
            button_image_path='button-start.png',
            button_x_offset=-14,
            bg_image_path='button-start-background.png',
            bg_width=340,
            bg_height=64,
            text='Start',
            text_x_offset=36,
            text_y_offset=-1,
            font=('Microsoft YaHei', 17, 'bold'),
            command=lambda: Events.Fire(Events.Application.Launch()),
            master=master)
        self.tools_button = tools_button
        self.stage = None
        self.subscribe(Events.GUI.LauncherFrame.StageUpdate, self.handle_stage_update)
        self.subscribe(
            Events.PackageManager.VersionNotification,
            self.handle_version_notification)

    def handle_version_notification(self, event):
        installed = event.package_states[Config.Launcher.active_importer].installed_version != ''
        self.set_enabled(installed)
        self.show(self.stage == Stage.Ready)

    def handle_stage_update(self, event):
        self.stage = event.stage
        self.show(self.stage == Stage.Ready)

    def _handle_enter(self, event):
        self.tools_button._handle_enter(None, True)
        super()._handle_enter(self)

    def _handle_leave(self, event):
        self.tools_button._handle_leave(None, True)
        super()._handle_leave(self)

    def _handle_button_press(self, event):
        self.tools_button.set_selected(True)
        super()._handle_button_press(self)

    def _handle_button_release(self, event):
        self.tools_button.selected = False
        self.tools_button._handle_leave(None, True)
        super()._handle_button_release(self)


class InstallButton(MainActionButton):
    def __init__(self, master, tools_button):
        super().__init__(
            x=1023,
            width=32,
            height=32,
            # button_image_path='button-start.png',
            # button_x_offset=-14,
            bg_image_path='button-start-background.png',
            bg_width=340,
            bg_height=64,
            text='Install',
            text_x_offset=18,
            text_y_offset=-1,
            font=('Microsoft YaHei', 17, 'bold'),
            command=lambda: Events.Fire(Events.Application.Update(packages=[Config.Launcher.active_importer], force=True, reinstall=True)),
            master=master)
        self.tools_button = tools_button
        self.subscribe(Events.GUI.LauncherFrame.StageUpdate, self.handle_stage_update)
        self.subscribe(
            Events.PackageManager.VersionNotification,
            self.handle_version_notification)

    def handle_version_notification(self, event):
        not_installed = event.package_states[Config.Launcher.active_importer].installed_version == ''
        self.set_enabled(not_installed)
        self.show(self.stage == Stage.Ready)

    def handle_stage_update(self, event):
        self.stage = event.stage
        self.show(self.stage == Stage.Ready)

    def _handle_enter(self, event):
        self.tools_button._handle_enter(None, True)
        super()._handle_enter(self)

    def _handle_leave(self, event):
        self.tools_button._handle_leave(None, True)
        super()._handle_leave(self)

    def _handle_button_press(self, event):
        self.tools_button.set_selected(True)
        super()._handle_button_press(self)

    def _handle_button_release(self, event):
        self.tools_button.selected = False
        self.tools_button._handle_leave(None, True)
        super()._handle_button_release(self)


class ToolsButton(MainActionButton):
    def __init__(self, master):
        super().__init__(
            x=1210,
            width=37,
            button_image_path='button-tools.png',
            command=lambda: True,
            master=master)
        self.subscribe_show(Events.GUI.LauncherFrame.StageUpdate, lambda event: event.stage == Stage.Ready)

    def _handle_enter(self, event, suppress=False):
        if not suppress:
            Events.Fire(Events.GUI.LauncherFrame.ToggleToolbox(show=True))
        super()._handle_enter(self)

    def _handle_leave(self, event, suppress=False):
        if not suppress:
            Events.Fire(Events.GUI.LauncherFrame.ToggleToolbox(hide_on_leave=True))
        super()._handle_leave(self)


class LauncherVersionText(UIText):
    def __init__(self, master):
        super().__init__(x=20,
                         y=680,
                         text='',
                         font=('Roboto', 14),
                         fill='#bbbbbb',
                         activefill='#cccccc',
                         anchor='nw',
                         master=master)
        self.subscribe_set(
            Events.PackageManager.VersionNotification,
            lambda event: f'{event.package_states["Launcher"].installed_version}')
        self.subscribe_show(
            Events.GUI.LauncherFrame.StageUpdate,
            lambda event: event.stage == Stage.Ready)

