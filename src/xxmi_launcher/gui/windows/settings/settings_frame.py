import logging

import core.config_manager as Config
import core.event_manager as Events
import gui.vars as Vars

from gui.classes.containers import UIFrame
from gui.classes.widgets import UIImageButton


class SettingsFrame(UIFrame):
    def __init__(self, master, canvas):
        super().__init__(master=master, canvas=canvas)

        self.settings_frame = None

        self.set_background_image(
            width=940,
            height=560,
            x=master.master.cfg.width/2,
            y=master.master.cfg.height/2,
            anchor='c',
            fg_color='#1f2024',
            border_color='gray',
            border_radius=20,
            border_width=1,
            brightness=1.0,
            opacity=1.0,
            dim_opacity=0.5,
            secondary_fill_color="#24252a",
            split=0.25,
            split_direction="vertical",
        )

        self.background_image.bind('<Button-1>', self._handle_button_press)

        self.close_button = self.put(CloseButton(self))

        self.hide()

        self.subscribe(Events.Application.CloseSettings, self.handle_close_settings)

    def open_settings(self, tab_name='', wait_window=False):
        if self.settings_frame is not None:
            return
        Vars.Settings.initialize_vars()
        Vars.Settings.load()
        # self.grid(row=0, column=0, padx=(125), pady=(175,140), sticky='nsew')
        self.place(x=175, y=122)

        from gui.windows.settings.settings_tabs_frame import SettingsTabsFrame
        if not tab_name:
            self.settings_frame = self.put(SettingsTabsFrame(self))
        else:
            self.settings_frame = self.put(SettingsTabsFrame(self, default_tab=tab_name))
        self.settings_frame.grid(row=0, column=0, sticky='news')
        self.settings_frame.show()
        self.show()

    def save_and_close(self, event=None):
        Vars.Settings.save()
        Config.Manager.save()
        self.hide()
        self._reset_frame()

    def handle_close_settings(self, event=None):
        if event.save:
            self.save_and_close()
        else:
            self.hide()
            self._reset_frame()

    def _show(self):
        super()._show()
        self.close_button.show()

    def _reset_frame(self):
        self.place_forget()
        if self.close_button is not None:
            self.close_button.hide()
        if self.settings_frame is not None:
            self.settings_frame.grid_forget()
            self.update_idletasks()
            self.settings_frame.destroy()
        self.elements = {}

        self.settings_frame = None

    def _hide(self):
        super()._hide()
        self.close_button.hide()

    def _handle_button_press(self, event):
        self.winfo_toplevel().begin_window_drag(event)


class CloseButton(UIImageButton):
    def __init__(self, master):
        super().__init__(
            x=1085,
            y=105,
            width=18,
            height=18,
            button_image_path='button-system-close.png',
            button_normal_opacity=0.8,
            button_hover_opacity=1,
            button_selected_opacity=1,
            bg_image_path='button-system-background.png',
            bg_width=24,
            bg_height=24,
            bg_normal_opacity=0,
            bg_hover_opacity=0.1,
            bg_selected_opacity=0.2,
            command=self.close,
            master=master)
        self.set_tooltip(f'Close', delay=0.1)

    def close(self):
        Events.Fire(Events.Application.CloseSettings(save=True))