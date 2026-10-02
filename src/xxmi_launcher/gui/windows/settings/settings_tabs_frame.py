import logging
import time

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

        self._initial_tab_guid = default_tab
        self._initial_tab_loaded = False
        self._preload_start_job = None
        self._preload_job = None
        self._preload_queue: list[str] = []
        self._preloading = False
        self._preload_pause_until = 0.0
        self._loading_tabs: set[str] = set()  # Exists, but is not fully rendered yet.
        self._ready_tabs: set[str] = set()  # Fully rendered and safe to display immediately.

        self.tab_buttons_frame = self.put(SettingsTabsListFrame(self))
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

    def _on_scroll_activity(self):
        # Keep background preloading paused while the user is scrolling.
        #
        # Every wheel event extends this timeout, so touchpad scrolling
        # naturally keeps the preloader paused until scrolling stops.
        self._preload_pause_until = time.monotonic() + 0.25

    def _register_tab(self, tab_desc: SettingsTabDesc):
        self.tabs[tab_desc.guid] = tab_desc

        button = SettingsTabButton(self.tab_buttons_frame, tab_desc)
        self.buttons[tab_desc.guid] = button
        self.tab_buttons_frame.put(button).grid(row=len(self.tabs), column=0, padx=(15, 5), pady=(5, 0), sticky='nw')

    def select_tab(self, tab_guid: str):
        self.buttons[tab_guid].set_selected(True)
        self.update_idletasks()

        if tab_guid in self._preload_queue:
            self._preload_queue.remove(tab_guid)

        if self.selected_tab_guid is not None:
            if tab_guid == self.selected_tab_guid:
                return

            previous_guid = self.selected_tab_guid
            self.buttons[previous_guid].set_selected(False)

            previous_desc = self.tabs[previous_guid]
            previous_frame = self.tab_content_frame.grab(previous_desc.frame_type)

            if previous_frame is not None:
                previous_frame.grid_forget()

        self.selected_tab_guid = tab_guid

        # A tab that is not fully ready needs the loading overlay.
        if tab_guid not in self._ready_tabs:
            self._show_loading_frame()

        self.after_idle(self.select_tab_async, tab_guid)

    def select_tab_async(self, tab_guid: str):
        tab_desc = self.tabs[tab_guid]
        tab_frame = self.tab_content_frame.grab(tab_desc.frame_type)

        # Tab hasn't been created yet.
        if tab_frame is None:
            tab_frame = self.tab_content_frame.put(tab_desc.frame_type(self.tab_content_frame))

            # Give the new frame an explicit size while it is hidden.
            tab_frame.configure(fg_color=self._fg_color, width=664, height=506)

            # Don't grid it yet.
            # Set up everything that affects layout before rendering.
            tab_frame._scrollbar.grid(row=1, column=1, sticky="nsew", pady=5)

            # Render completely while the frame is NOT mapped.
            self._loading_tabs.add(tab_guid)

            tab_frame.render_sections_async(
                done_callback=lambda guid=tab_guid: self._tab_load_finished(guid)
            )

            return

        # Tab exists but is still being constructed in the background.
        if tab_guid in self._loading_tabs:
            return

        # Tab has completed background rendering.
        if tab_guid in self._ready_tabs:
            self._reveal_ready_tab(tab_guid)

    def _tab_load_finished(self, tab_guid: str):
        self._loading_tabs.discard(tab_guid)
        self._ready_tabs.add(tab_guid)

        tab_frame = self.tab_content_frame.grab(self.tabs[tab_guid].frame_type)

        if tab_frame is not None:
            tab_frame.update_idletasks()

        if self.selected_tab_guid == tab_guid:
            self.after_idle(self._reveal_ready_tab, tab_guid)

        if not self._initial_tab_loaded and tab_guid == self._initial_tab_guid:
            self._initial_tab_loaded = True
            if not self._preloading:
                self._preload_start_job = self.after(150, self._start_preloading)
        elif self.selected_tab_guid != tab_guid:
            self._schedule_preload()

    def _show_loading_frame(self):
        if self.loading_frame is not None:
            return

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

        self.loading_frame.update_idletasks()

    def _hide_loading_frame(self):
        if self.loading_frame is None:
            return

        self.loading_frame.grid_remove()
        self.loading_frame.destroy()
        self.loading_frame = None

    def _start_preloading(self):
        self._preload_start_job = None

        if self._preloading:
            return

        self._preloading = True
        self._preload_queue = [
            guid
            for guid in reversed(self.tabs)
            if guid != self.selected_tab_guid and guid not in self._ready_tabs
        ]

        self._schedule_preload()

    def _schedule_preload(self, delay=1):
        if not self._preloading or self._preload_job is not None:
            return

        self._preload_job = self.after(delay, self._preload_next)

    def _preload_next(self):
        self._preload_job = None

        if not self._preloading:
            return

        if not self._preload_queue:
            self._preloading = False
            return

        if time.monotonic() < self._preload_pause_until:
            self._schedule_preload()
            return

        tab_guid = self._preload_queue.pop(0)
        tab_desc = self.tabs[tab_guid]
        tab_frame = self.tab_content_frame.grab(tab_desc.frame_type)

        if tab_frame is not None:
            self._schedule_preload()
            return

        tab_frame = self.tab_content_frame.put(tab_desc.frame_type(self.tab_content_frame))
        tab_frame.configure(fg_color=self._fg_color, width=664, height=506)
        tab_frame._scrollbar.grid(row=1, column=1, sticky="nsew", pady=5)

        # This frame is not ready until render_sections_async() calls its completion callback.
        self._loading_tabs.add(tab_guid)

        tab_frame.render_sections_async(
            done_callback=lambda guid=tab_guid: self._tab_load_finished(guid)
        )

    def _reveal_ready_tab(self, tab_guid: str):
        if self.selected_tab_guid != tab_guid or tab_guid not in self._ready_tabs:
            return

        tab_frame = self.tab_content_frame.grab(self.tabs[tab_guid].frame_type)

        if tab_frame is None:
            return

        # Remove the loading frame first, then reveal the already
        # completely constructed tab in the same callback.
        self._hide_loading_frame()

        tab_frame.grid(row=1, column=0, padx=(10, 10), pady=(0, 10), sticky="news", rowspan=len(self.tabs))

        # Keep this tab permanently marked as ready.
        self._schedule_preload()

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
