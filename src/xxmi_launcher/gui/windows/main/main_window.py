import logging
import pyglet

from pathlib import Path

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from customtkinter import set_appearance_mode, set_default_color_theme

from gui.windows.message_window import MessageWindow

from gui.classes.windows import UIMainWindow, limit_scaling

from gui.windows.main.launcher_frame.launcher_frame import LauncherFrame

log = logging.getLogger(__name__)

# from customtkinter import set_widget_scaling, set_window_scaling, deactivate_automatic_dpi_awareness
# set_widget_scaling(2)
# set_window_scaling(2)
# deactivate_automatic_dpi_awareness()
# Limit automatic scaling in a way to fit arbitrary width and height on screen
limit_scaling(1280, 720)


class MainWindow(UIMainWindow):
    def __init__(self):
        super().__init__()

        self.hide()

        # Set appearance mode to same as one of user OS
        set_appearance_mode('System')
        # Fix pyglet font load
        pyglet.options['win32_gdi_font'] = True

        self.load_theme(Paths.App.Themes / 'Default')

        Events.Subscribe(Events.Application.ShowMessage,
                         lambda event: self.show_messagebox(event))
        Events.Subscribe(Events.Application.ShowError,
                         lambda event: self.show_messagebox(event))
        Events.Subscribe(Events.Application.ShowWarning,
                         lambda event: self.show_messagebox(event))
        Events.Subscribe(Events.Application.ShowInfo,
                         lambda event: self.show_messagebox(event))

    def load_theme(self, theme_path: Path):
        # Load custom tkinter theme
        try:
            set_default_color_theme(str(theme_path / 'custom-tkinter-theme.json'))
        except Exception as e:
            log.exception(e)
        # Load custom fonts
        fonts_path = theme_path / 'Fonts'
        for font_path in fonts_path.iterdir():
            if font_path.suffix != '.ttf':
                continue
            try:
                pyglet.font.add_file(str(font_path))
            except Exception as e:
                log.exception(e)

    def initialize(self):
        import gui.vars as Vars

        Vars.Settings.initialize(Config.Config, self)
        Vars.Settings.load()

        # def callback(var, new_value, old_value):
        #     print(var, new_value, old_value)
        # Vars.Settings.subscribe(Vars.Settings.Launcher.log_level, callback)
        # Vars.Settings.Launcher.log_level.set('TEST')
        # Vars.Settings.save()

        self.load_theme(Config.Active.Importer.theme_path)

        self.cfg.title = 'XXMI Launcher'
        self.cfg.icon_path = Config.Active.Importer.theme_path / 'window-icon.ico'

        self.cfg.width = 1280
        self.cfg.height = 720

        self.apply_config()

        self.center_window()

        self.launcher_frame = self.put(LauncherFrame(self))
        self.launcher_frame.grid(row=0, column=0, padx=0, pady=0, sticky='news')

        Events.Subscribe(Events.Application.MoveWindow, lambda event: self.move(event.offset_x, event.offset_y))

        Events.Fire(Events.Application.Ready())
        # Events.Fire(Events.Application.Busy())
        # Events.Fire(Events.PackageManager.InitializeInstallation())

        self.show()

        # self.open_settings()

        Events.Subscribe(Events.Application.OpenSettings,
                         lambda event: self.open_settings(wait_window=event.wait_window))
        Events.Subscribe(Events.Application.Minimize,
                         lambda event: self.minimize())
        Events.Subscribe(Events.Application.Close, self.handle_close)

    def handle_close(self, event):
        self.after(event.delay, self.close)

    def close(self):
        Events.Fire(Events.Application.Ready())
        super().close()

    def open_settings(self, wait_window=False):
        from gui.windows.settings.settings_window import SettingsWindow
        # settings = SettingsWindow(self)
        self.after(10, SettingsWindow, self)
        # if wait_window:
        #     self.wait_window(settings)

    def show_messagebox(self, event):
        if not self.exists:
            return False

        messagebox = MessageWindow(self, icon=event.icon,
                                title=event.title, message=event.message,
                                confirm_text=event.confirm_text, confirm_command=event.confirm_command,
                                cancel_text=event.cancel_text, cancel_command=event.cancel_command,
                                lock_master=event.lock_master, screen_center=event.screen_center)

        if event.modal:
            self.wait_window(messagebox)

        return messagebox.response

    def report_callback_exception(self, exc, val, tb):
        # raise exc
        self.show_messagebox(Events.Application.ShowError(
            modal=True,
            message=val,
        ))
        Events.Fire(Events.Application.Ready())
        logging.exception(val)
