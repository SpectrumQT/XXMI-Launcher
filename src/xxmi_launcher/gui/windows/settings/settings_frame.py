import logging

import core.config_manager as Config
import core.event_manager as Events
import core.i18n_manager as I18n
import gui.vars as Vars

from gui.classes.containers import UIFrame
from gui.classes.widgets import UIImageButton


class SettingsFrame(UIFrame):
    def __init__(self, master, canvas):
        super().__init__(master=master, canvas=canvas)

        self.settings_frame = None

        self.set_background_image(image_path='background-image.png', width=master.master.cfg.width,
                                  height=master.master.cfg.height, x=0, y=0, anchor='nw', brightness=1.0, opacity=1)

        self._offset_x = 0
        self._offset_y = 0
        self.background_image.bind('<Button-1>', self._handle_button_press)
        self.background_image.bind('<B1-Motion>', self._handle_mouse_move)

        self.close_button = self.put(CloseButton(self))

        self.hide()

        self.subscribe(
            Events.Application.OpenSettings,
            lambda event: self.open_settings(wait_window=event.wait_window))
        self.subscribe(Events.Application.CloseSettings, self.handle_close_settings)

    def open_settings(self, wait_window=False):
        if self.settings_frame is not None:
            return
        Vars.Settings.initialize_vars()
        Vars.Settings.load()
        # self.grid(row=0, column=0, padx=(125), pady=(175,140), sticky='nsew')
        self.place(x=124, y=167)

        from gui.windows.settings.settings_tabs_frame import SettingsTabsFrame
        self.settings_frame = self.put(SettingsTabsFrame(self))
        self.settings_frame.grid(row=0, column=0, sticky='news')
        self.settings_frame.show()
        self.show()

    def save_and_close(self, event=None):
        Vars.Settings.save()
        Config.Config.save()
        self.hide()

    def handle_close_settings(self, event=None):
        if event.save:
            self.save_and_close()
        else:
            self.hide()

    def _show(self):
        super()._show()
        self.close_button.show()

    def _hide(self):
        super()._hide()
        self.place_forget()
        if self.settings_frame is not None:
            self.settings_frame.grid_forget()
            self.settings_frame.destroy()
        self.elements = {}

        self.settings_frame = None
        if self.close_button is not None:
            self.close_button.hide()

    def _handle_button_press(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _handle_mouse_move(self, event):
        Events.Fire(Events.Application.MoveWindow(offset_x=self._offset_x, offset_y=self._offset_y))


class CloseButton(UIImageButton):
    def __init__(self, master):
        super().__init__(
            x=1135,
            y=155,
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
        self.set_tooltip(I18n._('buttons.close'), delay=0.1)

    def close(self):
        self.master.save_and_close()