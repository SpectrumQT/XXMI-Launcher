import logging

import core.config_manager as Config
import core.event_manager as Events
import gui.vars as Vars
from core.locale_manager import L

from gui.classes.containers import UIFrame
from gui.classes.widgets import UIButton, UILabel

from gui.windows.settings.frames.general_settings_frame import GeneralSettingsFrame
from gui.windows.settings.frames.importer_settings_frame import ModelImporterSettingsFrame
from gui.windows.settings.frames.advanced_settings_frame import AdvancedSettingsFrame
from gui.windows.settings.frames.launcher_settings_frame import LauncherSettingsFrame

log = logging.getLogger(__name__)


class SettingsTabsFrame(UIFrame):
    def __init__(self, master):

        super().__init__(master)

        self.tab_buttons_frame =  self.put(SettingsTabsListFrame(self))
        self.tab_buttons_frame.grid(row=0, column=0, padx=(0, 0), pady=(0, 0), sticky='news')
        self.tab_buttons_frame.grid_propagate(0)

        self.tab_content_frame = self.put(SettingsTabContentFrame(self))
        self.tab_content_frame.grid(row=0, column=1, padx=(0, 0), pady=(0, 0), sticky='news')
        self.tab_content_frame.grid_propagate(0)

        self.tab_content_frame.columnconfigure(0, weight=1)

        self.buttons = {}
        self.tabs = {}
        self.selected_tab = None

        self.add_tab('GENERAL_TAB', str(L('settings_tab_general', 'General')), GeneralSettingsFrame(master=self.tab_content_frame))
        self.add_tab('LAUNCHER_TAB', str(L('settings_tab_launcher', 'Launcher')), LauncherSettingsFrame(master=self.tab_content_frame))
        self.add_tab('IMPORTER_TAB', str(L('settings_tab_importer', 'MI')), ModelImporterSettingsFrame(master=self.tab_content_frame))
        self.add_tab('ADVANCED_TAB', str(L('settings_tab_advanced', 'Advanced')), AdvancedSettingsFrame(master=self.tab_content_frame))

        self.select_tab(self.tabs['GENERAL_TAB'])

        self.trace_save(Vars.Settings.Launcher.active_importer, self.handle_active_importer_update)
        self.trace_save(Vars.Active.Importer.importer_folder, self.handle_importer_folder_update)

        self.show()

    def handle_importer_folder_update(self, var, val, old_val):
        if old_val is None or val == old_val:
            return
        Events.Fire(Events.Application.LoadImporter(importer_id=Config.Launcher.active_importer, reload=True))

    def select_tab(self, tab):
        if self.selected_tab is not None:
            if tab == self.selected_tab:
                return
            else:
                self.selected_tab.label.grid_forget()
                self.selected_tab.frame.grid_forget()
                self.selected_tab.unselect_tab()
                self.buttons[self.selected_tab.guid].set_selected(False)

        self.buttons[tab.guid].set_selected(True)
        tab.label.grid(row=0, column=0, padx=(30, 10), pady=(0, 20), sticky='nw')
        tab.frame.configure(fg_color=self._fg_color)
        tab.frame.grid(row=1, column=0, padx=(10, 10), pady=(10, 10), sticky='news', rowspan=len(self.tabs))
        self.selected_tab = tab

    def add_tab(self, tab_guid, tab_name, tab_frame):
        label = SettingsTabLabel(self.tab_content_frame, tab_name)
        tab = SettingsTab(self, tab_guid, tab_name, tab_frame, label)
        button = SettingsTabButton(self.tab_buttons_frame, tab)
        self.tabs[tab_guid] = tab

        self.tab_buttons_frame.put(button).grid(row=len(self.tabs), column=0, padx=(15, 5), pady=(5, 0), sticky='nw')
        self.tab_content_frame.put(label)
        self.tab_content_frame.put(tab_frame)

        self.buttons[tab_guid] = button

        tab_frame.update()

    def rename_tab(self, tab_guid, tab_name):
        tab = self.tabs[tab_guid]
        tab.rename(tab_name)
        button = self.buttons[tab_guid]
        button.configure(text=tab_name)

    def handle_active_importer_update(self, var, val, old_val):
        self.rename_tab('IMPORTER_TAB', val)


class SettingsTabsListFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            width = 230,
            height = 406,
            master=master)

        self.put(SettingsLabel(self)).grid(row=0, column=0, padx=(30, 10), pady=(0, 15), sticky='nw')


class SettingsLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('settings_title', 'Settings')),
            font=('Microsoft YaHei', 20),
            fg_color='transparent',
            text_color='#888888',
            master=master)


class SettingsTabButton(UIButton):
    def __init__(self, master, tab):
        super().__init__(
            text=tab.name,
            command=self.select_tab,
            width=200,
            height=42,
            anchor='w',
            master=master)
        self._text_label.configure(padx=10)
        self.tab = tab

    def select_tab(self):
        self.tab.select_tab()


class SettingsTabLabel(UILabel):
    def __init__(self, master, tab_name):
        super().__init__(
            text=tab_name,
            master=master)


class SettingsTabContentFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            width = 800,
            height = 406,
            master=master)


class SettingsTab:
    def __init__(self, master, guid, name, frame, label):
        self.container = master
        self.guid = guid
        self.name = name
        self.frame = frame
        self.label = label

    def rename(self, name):
        self.name = name
        self.label.set(name)

    def select_tab(self):
        self.container.select_tab(self)
        self.frame.show()

    def unselect_tab(self):
        self.frame.hide()
