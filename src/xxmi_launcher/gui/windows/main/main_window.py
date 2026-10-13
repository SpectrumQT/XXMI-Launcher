import json
import logging
import pyglet

import core.path_manager as Paths
import core.event_manager as Events
import core.config_manager as Config

from core.locale_manager import L

from customtkinter import set_appearance_mode, set_default_color_theme, ScalingTracker, set_widget_scaling, set_window_scaling

from core.config.enums import WindowScale
from gui.classes.windows import UIMainWindow, calculate_scaling_limit, get_monitor_dpi, install_scaling_tracker_guard, enable_high_quality_dpi_awareness
from gui.windows.main.message_frame.message_frame import MessageFrame
from gui.windows.main.launcher_frame.launcher_frame import LauncherFrame

log = logging.getLogger(__name__)

from customtkinter import deactivate_automatic_dpi_awareness
# set_widget_scaling(2)
# set_window_scaling(2)
# deactivate_automatic_dpi_awareness()


class MainWindow(UIMainWindow):
    def __init__(self):
        self._window_scale = 0

        # Enable crisp Windows rendering before CTk initialization.
        enable_high_quality_dpi_awareness()
        install_scaling_tracker_guard()
        self.handle_scale_window(None)

        super().__init__()

        self.hide()

        self.cfg.title = 'XXMI Launcher'
        self.cfg.width = 1280
        self.cfg.height = 720

        # Use dark mode theme colors
        set_appearance_mode('Dark')

        # Fix pyglet font load
        pyglet.options['win32_gdi_font'] = True

        self.active_theme = None
        self.launcher_frame = None
        self.message_frame = None

        self.minimal_gui = True

        Events.Subscribe(Events.Application.ShowMessage, lambda event: self.show_messagebox(event))
        Events.Subscribe(Events.Application.ShowError, lambda event: self.show_messagebox(event))
        Events.Subscribe(Events.Application.ShowWarning, lambda event: self.show_messagebox(event))
        Events.Subscribe(Events.Application.ShowInfo, lambda event: self.show_messagebox(event))

    def load_theme(self, theme: str):
        # Skip loading the same theme
        if self.active_theme == theme:
            return

        theme_path = Paths.App.Themes / theme
        theme_json_path = theme_path / 'custom-tkinter-theme.json'

        # Ensure customtkinter theme integrity
        if not self.validate_theme(theme_json_path):
            theme = 'Default'
            Config.Launcher.gui_theme = theme
            theme_path = Paths.App.Themes / theme
            theme_json_path = theme_path / 'custom-tkinter-theme.json'
            if self.active_theme == theme:
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
        Config.Config.active_theme = theme

    def validate_theme(self, theme_json_path):
        theme_name = theme_json_path.parent.name

        # Make sure that theme exists
        if not theme_json_path.is_file():
            Events.Fire(Events.Application.ShowWarning(
                modal=True,
                message=L('message_text_theme_load_failed_no_folder', """
                    Failed to load {theme} theme:
                    
                    Theme folder does not exist!
                """).format(theme=theme_name)
            ))
            return False

        if not theme_json_path.parent.is_dir():
            Events.Fire(Events.Application.ShowWarning(
                modal=True,
                message=L('message_text_theme_load_failed_no_file', """
                    Failed to load {theme} theme:
                    
                    Theme file `custom-tkinter-theme.json` does not exist!
                """).format(theme=theme_name)
            ))
            return False

        if theme_name == 'Default':
            return True

        try:
            theme_data = json.loads(Paths.App.read_text(theme_json_path))
            theme_api_version = theme_data['Metadata']['theme_api_version']
        except:
            theme_api_version = '0.0.0'

        if theme_api_version <  '1.1.0':
            update_dialogue = Events.Application.ShowWarning(
                modal=True,
                title=L('message_title_theme_update_required', 'Theme Update Required'),
                confirm_text=L('message_button_theme_use_default', 'Use Default'),
                cancel_text=L('message_button_patch_theme', 'Patch Theme'),
                message=L('message_text_theme_update_required', """
                    Selected {theme} theme cannot be loaded!
                    
                    Click `Use Default` to use default theme instead (ensures proper visuals).
                    Click `Patch Theme` to replace `custom-tkinter-theme.json` with new one.
                """).format(theme=theme_name)
            )

            user_requested_default_theme = self.show_messagebox(update_dialogue)

            if user_requested_default_theme is False:
                default_json_path = Paths.App.Themes / 'Default' / 'custom-tkinter-theme.json'
                Paths.App.copy_file(default_json_path, theme_json_path)
                return True
            else:
                return False

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

        self.minimal_gui = False

        Vars.Settings.initialize(Config.Config, self)
        Vars.Settings.load()

        # def callback(var, new_value, old_value):
        #     print(var, new_value, old_value)
        # Vars.Settings.subscribe(Vars.Settings.Launcher.log_level, callback)
        # Vars.Settings.Launcher.log_level.set('TEST')
        # Vars.Settings.save()

        self.load_theme(Config.Config.active_theme)

        self.apply_config()

        self.center_window()

        self.launcher_frame = self.put(LauncherFrame(self))
        self.launcher_frame.grid(row=0, column=0, padx=0, pady=0, sticky='news')

        # Auto reload
        self.reload_theme()

        Events.Subscribe(Events.GUI.ToggleThemeDevMode, self.reload_theme)
        Events.Subscribe(Events.GUI.ReloadGUI, self.reload_gui)

        Events.Fire(Events.Application.Ready())
        # Events.Fire(Events.Application.Busy())
        # Events.Fire(Events.PackageManager.InitializeDownload())
        # Events.Fire(Events.PackageManager.UpdateDownloadProgress(downloaded_bytes=430000, total_bytes=1000000))
        # Events.Fire(Events.PackageManager.InitializeInstallation())

        self.show()

        Events.Subscribe(Events.Application.Minimize, lambda event: self.minimize())
        Events.Subscribe(Events.Application.Close, self.handle_close)
        Events.Subscribe(Events.GUIEvents.ScaleWindow, self.handle_scale_window)

    def handle_scale_window(self, event: Events.Application.ConfigUpdate | None):
        tracker = ScalingTracker
        is_auto = Config.Config.Launcher.window_scale == WindowScale.AUTO
        has_tk = self.__dict__.get("tk") is not None

        if is_auto:
            # Enable CustomTkinter's automatic DPI multiplier.
            tracker.deactivate_automatic_dpi_awareness = False

            if has_tk:
                # Refresh the cached DPI for each existing window.
                for window in tuple(tracker.window_dpi_scaling_dict):
                    try:
                        if window.winfo_exists():
                            tracker.window_dpi_scaling_dict[window] = tracker.get_window_dpi_scaling(window)
                    except Exception:
                        pass

                dpi_scaling = tracker.window_dpi_scaling_dict.get(self)
                if dpi_scaling is None:
                    dpi_scaling = tracker.get_window_dpi_scaling(self)
            else:
                # Called before CTk.__init__().
                x_dpi, y_dpi = get_monitor_dpi()
                dpi_scaling = (x_dpi + y_dpi) / (2 * 96)

            # Calculate the desired effective scale, including monitor DPI.
            target_scale = calculate_scaling_limit(1280, 720, 1.0, 1.0, 0.8, dpi_scaling=dpi_scaling)

            # Convert the effective scale to CustomTkinter's base scale.
            # Its callback multiplies this by the cached DPI factor.
            target_scale = max(target_scale, dpi_scaling * 0.4)
            target_scale = min(max(0.5, target_scale), 6.0)
            applied_scale = target_scale / dpi_scaling

        else:
            ScalingTracker.deactivate_automatic_dpi_awareness = True

            # TODO: Add native (low quality) Windows scaling support
            # deactivate_automatic_dpi_awareness()

            # In fixed mode, keep the DPI multiplier at 1.0.
            for window in tuple(tracker.window_dpi_scaling_dict):
                tracker.window_dpi_scaling_dict[window] = 1.0

            if Config.Config.Launcher.window_scale == WindowScale.CUSTOM:
                requested_scale = Config.Config.Launcher.custom_window_scale / 100
            else:
                requested_scale = int(Config.Config.Launcher.window_scale.name.removeprefix("SCALE_")) / 100

            # Do not multiply the requested fixed scale by Windows DPI.
            target_scale = calculate_scaling_limit(1280, 720, requested_scale, 1.0, 1.0, dpi_scaling=1.0)

            target_scale = min(max(0.5, target_scale), 6.0)
            applied_scale = target_scale

        # Keep widget and window scaling synchronized.
        applied_scale = max(0.4, applied_scale)

        if self._window_scale == 0:
            self._window_scale = target_scale

        # Apply both values atomically.
        # The public setters each trigger update_scaling_callbacks_all(), which would otherwise run twice.
        tracker.widget_scaling = applied_scale
        tracker.window_scaling = applied_scale
        tracker.update_scaling_callbacks_all()

    def reload_gui(self, event: Events.GUI.ReloadGUI):
        Events.Fire(Events.Application.StatusUpdate(status=L('status_reloading_gui', 'Reloading GUI...')))

        settings_frame = self.launcher_frame.grab('SettingsFrame')
        if settings_frame:
            Events.Fire(Events.Application.CloseSettings(save=True))

        # Remove existing LauncherFrame widgets tree
        del self.elements[self.launcher_frame._id]
        self.launcher_frame.destroy()

        # Load theme
        if event.reload_theme:
            self.load_theme(Config.Launcher.gui_theme)

        # Create new LauncherFrame
        self.launcher_frame = self.put(LauncherFrame(self))
        self.launcher_frame.grid(row=0, column=0, padx=0, pady=0, sticky='news')

        # Trigger events listened by LauncherFrame to initialize its state
        Events.Fire(Events.Application.Ready())
        Events.Fire(Events.Application.LoadImporter(importer_id=Config.Launcher.active_importer, reload=True))
        Events.Fire(Events.Application.ConfigUpdate())
        Events.Fire(Events.PackageManager.NotifyPackageVersions(detect_installed=True))

        self.launcher_frame.background_image.start_animation()

        # Mouse events can't be processed while GUI is reloading.
        # Catch the window up to the cursor's current position.
        self.update_window_drag_position()

    def handle_close(self, event):
        self.after(event.delay, self.close)

    def close(self):
        Events.Fire(Events.Application.Ready())
        log.debug("Stopping GUI...")
        self.hide()
        self.quit()
        log.debug("GUI stopped")

    def show_messagebox(self, event=None, **kwargs):
        if not self.exists:
            return False

        if event is not None:
            kwargs = vars(event)

        modal = kwargs.pop('modal', False)
        show_settings = False
        settings_frame = None

        if self.launcher_frame is None:
            # Initialize minimal GUI (launcher crashed before LauncherFrame initialization)
            self.minimal_gui = True
            self.load_theme('Default')
            self.apply_config()
            self.center_window()
            self.launcher_frame = self.put(LauncherFrame(self, minimal=True))
            self.launcher_frame.grid(row=0, column=0, padx=0, pady=0, sticky='news')
        else:
            # Hide SettingsFrame if it's open and remember to show it again once message is closed
            settings_frame = self.launcher_frame.grab('SettingsFrame')
            if settings_frame and not settings_frame.is_hidden:
                show_settings = True
                settings_frame.hide()

        self.after(1, lambda: Events.Fire(Events.GUIEvents.PauseAnimations()))

        messagebox = MessageFrame(self.launcher_frame, self.launcher_frame.canvas, **kwargs)

        self.message_frame = self.put(messagebox)
        self.message_frame.show()

        if self.minimal_gui:
            self.show()

        if modal:
            self.wait_window(messagebox)
            self.update_idletasks()
            
            if self.minimal_gui:
                self.hide()

        if self.message_frame is not None:
            self.message_frame = None

        self.after(1, lambda: Events.Fire(Events.GUIEvents.ResumeAnimations()))

        if show_settings and settings_frame.is_hidden:
            settings_frame.show()

        if messagebox.radio_var is not None:
            return messagebox.response, messagebox.radio_var.get()

        if messagebox.selected_options is not None:
            return messagebox.response, messagebox.selected_options

        return messagebox.response

    def report_callback_exception(self, exc, val, tb):
        # raise exc
        if self.message_frame is not None:
            self.message_frame.close()
        self.show_messagebox(Events.Application.ShowError(
            modal=True,
            message=val,
        ))
        Events.Fire(Events.Application.Ready())
        logging.exception(val)

    def _set_scaling(self, new_widget_scaling, new_window_scaling):
        super()._set_scaling(new_widget_scaling, new_window_scaling)
        if new_window_scaling != self._window_scale:
            self._window_scale = new_window_scaling
            # Let CTk finish its geometry/scaling transition first.
            self.after(1, lambda: Events.Fire(Events.GUI.ReloadGUI()))
