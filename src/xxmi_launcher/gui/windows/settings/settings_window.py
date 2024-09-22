import logging
import customtkinter

import core.config_manager as Config
import core.event_manager as Events
import gui.vars as Vars

from gui.classes.windows import UIToplevel
from gui.classes.containers import UITabView
from gui.classes.widgets import UIButton

from gui.windows.settings.frames.general_settings_frame import GeneralSettingsFrame
from gui.windows.settings.frames.importer_settings_frame import ModelImporterSettingsFrame
from gui.windows.settings.frames.advanced_settings_frame import AdvancedSettingsFrame

log = logging.getLogger(__name__)


class SettingsWindow(UIToplevel):
    def __init__(self, master):
        super().__init__(master, lock_master=True)

        Vars.Settings.initialize_vars()
        Vars.Settings.load()

        self.cfg.title = 'Settings'
        self.cfg.icon_path = Config.Active.Importer.theme_path / 'window-icon.ico'
        self.cfg.width = 800
        self.cfg.height = 450
        self.cfg.no_titlebar = False

        self.transient(master)

        self.apply_config()

        self.center_window()

        self.put(SettingsTabView(self)).pack(expand=True, fill='both', padx=(10, 10), pady=(0, 10))

        self.put(CancelButton(self)).pack(side=customtkinter.LEFT, padx=(50, 10), pady=(5, 15))

        self.put(ConfirmButton(self)).pack(side=customtkinter.RIGHT, padx=(10, 50), pady=(5, 15))

        self.update()

        self.subscribe(Events.Application.CheckForUpdates, self.save_and_close)
        self.subscribe(Events.Application.Update, self.save_and_close)

        self.trace_save(Vars.Active.Importer.importer_folder, self.handle_importer_folder_update)

        self.after(50, self.open)

    def handle_importer_folder_update(self, var, val, old_val):
        if old_val is None or val == old_val:
            return
        Events.Fire(Events.Application.LoadImporter(importer_id=Config.Launcher.active_importer, reload=True))

    def close(self):
        super().close()

    def save_and_close(self, event=None):
        Vars.Settings.save()
        Config.Config.save()
        self.close()


class CancelButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text='Cancel',
            command=master.close,
            width=240,
            height=36,
            font=('Roboto', 16, 'bold'),
            fg_color='#e5e5e5',
            border_width=1,
            master=master)


class ConfirmButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text='Confirm',
            command=master.save_and_close,
            width=240,
            height=36,
            font=('Roboto', 16, 'bold'),
            fg_color='#666666',
            text_color='#ffffff',
            hover_color='#888888',
            border_width=1,
            master=master)


class SettingsTabView(UITabView):
    def __init__(self, master):
        super().__init__(master, anchor='nw')

        self._segmented_button.configure(font=('Roboto', 18))

        self.general_tab = self.add('General')
        self.put(GeneralSettingsFrame(master=self.general_tab)).pack(expand=True, fill='both')

        self.importer_tab = self.add('_IMPORTER_TAB_')
        self.put(ModelImporterSettingsFrame(self.importer_tab)).pack(expand=True, fill='both')
        self.trace_save(Vars.Settings.Launcher.active_importer, self.handle_active_importer_update)

        self.advanced_tab = self.add('Advanced')
        self.put(AdvancedSettingsFrame(master=self.advanced_tab)).pack(expand=True, fill='both')

    def handle_active_importer_update(self, var, val, old_val):
        self.rename_tab('_IMPORTER_TAB_', val, keep_old_key=True)
