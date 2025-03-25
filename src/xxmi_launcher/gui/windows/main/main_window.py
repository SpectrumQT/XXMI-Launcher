import json
import logging
import shutil

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

        # Use dark mode theme colors
        set_appearance_mode('Dark')

        # Fix pyglet font load
        pyglet.options['win32_gdi_font'] = True

        self.active_theme = None

        self.load_theme('Default')

        Events.Subscribe(Events.Application.ShowMessage,
                         lambda event: self.show_messagebox(event))
        Events.Subscribe(Events.Application.ShowError,
                         lambda event: self.show_messagebox(event))
        Events.Subscribe(Events.Application.ShowWarning,
                         lambda event: self.show_messagebox(event))
        Events.Subscribe(Events.Application.ShowInfo,
                         lambda event: self.show_messagebox(event))

    def load_theme(self, theme: str):
        # Skip loading the same theme
        if self.active_theme == theme:
            return
        theme_path = Paths.App.Themes / theme
        theme_json_path = theme_path / 'custom-tkinter-theme.json'
        # Ensure customtkinter theme integrity
        if not self.validate_theme(theme_json_path):
            return
        # Load customtkinter theme
        try:
            set_default_color_theme(str(theme_json_path))
        except Exception as e:
            log.exception(e)
        # Load custom fonts
        fonts_path = theme_path / 'Fonts'
        if fonts_path.is_dir():
            for font_path in fonts_path.iterdir():
                if font_path.suffix != '.ttf':
                    continue
                try:
                    pyglet.font.add_file(str(font_path))
                except Exception as e:
                    log.exception(e)
        # Set icon path
        icon_path = theme_path / 'window-icon.ico'
        if icon_path.is_file():
            self.cfg.icon_path = icon_path
        # Set theme as active
        self.active_theme = theme

    def validate_theme(self, theme_json_path):
        theme_name = theme_json_path.parent.name
        if theme_name == 'Default':
            return True

        # Make sure that theme exists
        if not theme_json_path.is_file():
            Config.Config.active_theme = 'Default'
            Config.Launcher.gui_theme = 'Default'
            self.load_theme('Default')
            Events.Fire(Events.Application.ShowWarning(
                message=f'Failed to load {theme_name} theme:\n\n'
                        f'Theme folder does not exist!'
            ))
            return False

        if not theme_json_path.parent.is_dir():
            Config.Config.active_theme = 'Default'
            Config.Launcher.gui_theme = 'Default'
            self.load_theme('Default')
            Events.Fire(Events.Application.ShowWarning(
                message=f'Failed to load {theme_name} theme:\n\n'
                        f'Theme file `custom-tkinter-theme.json` does not exist!'
            ))
            return False

        try:
            with open(theme_json_path, 'r') as f:
                theme_data = json.load(f)
                theme_api_version = theme_data['Metadata']['theme_api_version']
        except:
            theme_api_version = '0.0.0'

        if theme_api_version <  '1.0.1':
            default_json_path = Paths.App.Themes / 'Default' / 'custom-tkinter-theme.json'
            set_default_color_theme(str(default_json_path))
            update_dialogue = Events.Application.ShowWarning(
                modal=True,
                screen_center=not self.is_shown(),
                lock_master=self.is_shown(),
                icon='update-icon.ico',
                title='Theme Update Required',
                confirm_text='Use Default',
                cancel_text='Patch Theme',
                message=f'Selected {theme_name} theme cannot be loaded!\n\n'
                        f'Click `Use Default` to use default theme instead (ensures proper visuals).\n'
                        f'Click `Patch Theme` to replace `custom-tkinter-theme.json` with new one.',
            )
            user_requested_default_theme = self.show_messagebox(update_dialogue)
            if user_requested_default_theme:
                Config.Config.active_theme = 'Default'
                Config.Launcher.gui_theme = 'Default'
                self.load_theme('Default')
            else:
                Events.Fire(Events.Application.VerifyFileAccess(path=theme_json_path, write=True))
                theme_json_path.unlink()
                shutil.copy2(default_json_path, theme_json_path)
                self.load_theme(theme_name)

        return True

    def reload_theme(self, last_mod_time=0):
        if not Config.Config.Launcher.theme_dev_mode:
            return

        theme_path = Paths.App.Themes / self.active_theme
        mod_time = theme_path.stat().st_mtime

        # self._verify_chain()

        if mod_time != last_mod_time:
            try:
                set_default_color_theme(str(theme_path / 'custom-tkinter-theme.json'))
            except Exception as e:
                log.exception(e)
            self._apply_theme(recursive=True)

        self.after(100, self.reload_theme, mod_time)

    def _verify_chain(self):
        self._verify_chain_recursive(self)

    def _verify_chain_recursive(self, widget):
        for child in widget.children.values():
            if not hasattr(child, 'elements'):
                continue
            if not hasattr(child.master, 'elements'):
                raise Exception(f'Object of class {child.__class__.__qualname__} master is not of UIElement base class!')
            if child not in child.master.elements.values():
                raise Exception(f'Object of class {child.__class__.__qualname__} is not listed in elements of master {child.master.__class__.__qualname__}!\n'
                                f'{child.__dict__}')
            self._verify_chain_recursive(child)

    def initialize(self):
        import gui.vars as Vars

        Vars.Settings.initialize(Config.Config, self)
        Vars.Settings.load()

        # def callback(var, new_value, old_value):
        #     print(var, new_value, old_value)
        # Vars.Settings.subscribe(Vars.Settings.Launcher.log_level, callback)
        # Vars.Settings.Launcher.log_level.set('TEST')
        # Vars.Settings.save()

        self.load_theme(Config.Config.active_theme)

        self.cfg.title = 'XXMI Launcher'

        self.cfg.width = 1280
        self.cfg.height = 720

        self.apply_config()

        self.center_window()

        self.launcher_frame = self.put(LauncherFrame(self))
        self.launcher_frame.grid(row=0, column=0, padx=0, pady=0, sticky='news')

        # Auto reload
        self.reload_theme()

        Events.Subscribe(Events.Application.MoveWindow, lambda event: self.move(event.offset_x, event.offset_y))
        Events.Subscribe(Events.GUI.ToggleThemeDevMode, self.reload_theme)

        Events.Fire(Events.Application.Ready())
        # Events.Fire(Events.Application.Busy())
        # Events.Fire(Events.PackageManager.InitializeDownload())
        # Events.Fire(Events.PackageManager.UpdateDownloadProgress(downloaded_bytes=430000, total_bytes=1000000))
        # Events.Fire(Events.PackageManager.InitializeInstallation())

        self.show()

        # self.open_settings()
        Events.Subscribe(Events.Application.Minimize,
                         lambda event: self.minimize())
        Events.Subscribe(Events.Application.Close, self.handle_close)

    def handle_close(self, event):
        self.after(event.delay, self.close)

    def close(self):
        Events.Fire(Events.Application.Ready())
        super().close()

    def show_messagebox(self, event):
        if not self.exists:
            return False

        if event.lock_master is None:
            event.lock_master = self.is_shown()

        if event.screen_center is None:
            event.screen_center = not self.is_shown()

        messagebox = MessageWindow(self, icon=event.icon,
                                title=event.title, message=event.message,
                                confirm_text=event.confirm_text, confirm_command=event.confirm_command,
                                cancel_text=event.cancel_text, cancel_command=event.cancel_command,
                                radio_options=event.radio_options,
                                lock_master=event.lock_master, screen_center=event.screen_center)

        if event.modal:
            self.wait_window(messagebox)

        if messagebox.radio_var is not None:
            return messagebox.response, messagebox.radio_var.get()

        return messagebox.response

    def report_callback_exception(self, exc, val, tb):
        # raise exc
        self.show_messagebox(Events.Application.ShowError(
            modal=True,
            message=val,
        ))
        Events.Fire(Events.Application.Ready())
        logging.exception(val)
