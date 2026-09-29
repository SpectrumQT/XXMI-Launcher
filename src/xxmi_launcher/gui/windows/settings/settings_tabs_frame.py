import logging

import core.config_manager as Config
import core.event_manager as Events
import gui.vars as Vars

from dataclasses import dataclass

from core.locale_manager import L, LocaleString

from gui.classes.containers import UIFrame
from gui.classes.widgets import UIButton, UILabel

from gui.windows.settings.settings_content_frame import SettingsContentFrame
from gui.windows.settings.frames.general_settings_frame import GeneralSettingsFrame
from gui.windows.settings.frames.importer_settings_frame import ModelImporterSettingsFrame
from gui.windows.settings.frames.advanced_settings_frame import AdvancedSettingsFrame
from gui.windows.settings.frames.launcher_settings_frame import LauncherSettingsFrame

log = logging.getLogger(__name__)


@dataclass
class SettingsTabDesc:
    guid: str
    name: LocaleString | str
    frame_type: type[SettingsContentFrame]


class SettingsTabsFrame(UIFrame):

    def __init__(self, master, default_tab='GENERAL_TAB'):

        super().__init__(master)

        tabs = [
            SettingsTabDesc(
                guid = 'GENERAL_TAB',
                name = L('settings_tab_general', 'General'),
                frame_type = GeneralSettingsFrame,
            ),
            SettingsTabDesc(
                guid = 'LAUNCHER_TAB',
                name = L('settings_tab_launcher', 'Launcher'),
                frame_type = LauncherSettingsFrame,
            ),
            SettingsTabDesc(
                guid = 'IMPORTER_TAB',
                name = Vars.Settings.Launcher.active_importer.get(),
                frame_type = ModelImporterSettingsFrame,
            ),
            SettingsTabDesc(
                guid = 'ADVANCED_TAB',
                name = L('settings_tab_advanced', 'Advanced'),
                frame_type = AdvancedSettingsFrame,
            ),
        ]

        self.buttons = {}
        self.tabs: dict[str, SettingsTabDesc] = {}
        self.selected_tab_guid: str | None = None
        self.loading_frame = None

        self.tab_buttons_frame =  self.put(SettingsTabsListFrame(self))
        self.tab_buttons_frame.grid(row=0, column=0, padx=(0, 0), pady=(0, 0), sticky='news')
        self.tab_buttons_frame.grid_propagate(0)

        self.tab_content_frame = self.put(SettingsTabContentFrame(self))
        self.tab_content_frame.grid(row=0, column=1, padx=(0, 0), pady=(0, 0), sticky='news')
        self.tab_content_frame.grid_propagate(0)

        self.tab_content_frame.columnconfigure(0, weight=100)

        for tab_desc in tabs:
            self._register_tab(tab_desc)

        self.select_tab(default_tab)

        self.trace_save(Vars.Active.Importer.importer_folder, self.handle_importer_folder_update)

        self.show()

    def _register_tab(self, tab_desc: SettingsTabDesc):
        self.tabs[tab_desc.guid] = tab_desc

        button = SettingsTabButton(self.tab_buttons_frame, tab_desc)
        self.buttons[tab_desc.guid] = button
        self.tab_buttons_frame.put(button).grid(row=len(self.tabs), column=0, padx=(15, 5), pady=(5, 0), sticky='nw')

    def select_tab(self, tab_guid: str):

        self.buttons[tab_guid].set_selected(True)

        if self.selected_tab_guid is not None:
            if tab_guid == self.selected_tab_guid:
                return
            else:
                self.buttons[self.selected_tab_guid].set_selected(False)
                selected_tab_desc = self.tabs[self.selected_tab_guid]
                selected_tab_frame = self.tab_content_frame.grab(selected_tab_desc.frame_type)
                selected_tab_frame.grid_forget()

        self.selected_tab_guid = tab_guid

        # Show loading placeholder
        tab_desc = self.tabs[tab_guid]
        tab_frame = self.tab_content_frame.grab(tab_desc.frame_type)
        not_loaded = tab_frame is None
        if not_loaded:
            self.loading_frame = UIFrame(
                self.tab_content_frame,
                width=700,
                height=506,
                fg_color=self._fg_color,
            )
            self.loading_frame.grid_propagate(False)
            self.loading_frame.grid(row=1, column=0, padx=(10, 10), pady=(0, 10), sticky='news', rowspan=len(self.tabs))
            self.loading_frame.put(
                SettingsTabContentLoadingLabel(master=self.loading_frame)
            ).place(relx=0.5, rely=0.46, anchor="center")

        self.after_idle(self.select_tab_async, tab_guid)

    def select_tab_async(self, tab_guid: str):
        tab_desc = self.tabs[tab_guid]
        tab_frame = self.tab_content_frame.grab(tab_desc.frame_type)

        if tab_frame is None:
            # Keep loading_frame visible.
            tab_frame = self.tab_content_frame.put(
                tab_desc.frame_type(self.tab_content_frame)
            )

            tab_frame.configure(fg_color=self._fg_color)

            # Give the new frame an explicit size while it is hidden.
            tab_frame.configure(width=664, height=506)

            # Don't grid it yet.
            # Set up everything that affects layout before rendering.
            tab_frame._scrollbar.grid(row=1, column=1, sticky="nsew", pady=5)

            # Render completely while the frame is NOT mapped.
            tab_frame.render_sections()

            # Finish all currently pending geometry calculations.
            tab_frame.update_idletasks()

            # Only now reveal the finished frame.
            tab_frame.grid(row=1, column=0, padx=(10, 10), pady=(0, 10), sticky="news", rowspan=len(self.tabs))

            # Make sure the final geometry is settled before exposing it.
            tab_frame.update_idletasks()

            if self.loading_frame is not None:
                self.loading_frame.grid_remove()
                self.loading_frame.destroy()
                self.loading_frame = None

        else:
            tab_frame.grid(row=1, column=0, padx=(10, 10), pady=(0, 10), sticky="news", rowspan=len(self.tabs))

    def handle_importer_folder_update(self, var, val, old_val):
        if old_val is None or val == old_val:
            return
        Events.Fire(Events.Application.LoadImporter(importer_id=Config.Launcher.active_importer, reload=True))


class SettingsTabContentLoadingLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            master=master,
            text=L('settings_tab_loading_label', 'Loading...'),
        )


class SettingsTabsListFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            master=master,
            width = 230,
            height = 506,
        )

        self.put(SettingsLabel(self)).grid(row=0, column=0, padx=(30, 10), pady=(0, 15), sticky='nw')


class SettingsLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            master=master,
            text=L('settings_title', 'Settings'),
            font=('Microsoft YaHei', 20),
            fg_color='transparent',
            text_color='#888888',
        )


class SettingsTabButton(UIButton):
    def __init__(self, master, tab_desc: SettingsTabDesc):
        super().__init__(
            master=master,
            text=tab_desc.name,
            command=self.select_tab,
            width=200,
            height=42,
            anchor='w',
        )
        self._text_label.configure(padx=10)
        self.tab_guid = tab_desc.guid

    def select_tab(self):
        self.master.master.select_tab(self.tab_guid)


class SettingsTabContentFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            master=master,
            width = 700,
            height = 506,
        )
