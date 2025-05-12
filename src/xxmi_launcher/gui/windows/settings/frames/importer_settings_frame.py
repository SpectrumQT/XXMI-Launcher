from customtkinter import filedialog, ThemeManager

import core.event_manager as Events
import core.config_manager as Config
import core.i18n_manager as I18n
import gui.vars as Vars

from gui.classes.containers import UIFrame
from gui.classes.widgets import UIButton, UILabel, UIEntry, UICheckbox


class ModelImporterSettingsFrame(UIFrame):
    def __init__(self, master):
        super().__init__(master)

        self.grid_columnconfigure((0, 1, 2, 3, 5), weight=1)
        self.grid_columnconfigure(4, weight=100)

        # Importer Folder
        self.put(ImporterFolderLabel(self)).grid(row=0, column=0, padx=(20, 0), pady=(0, 30), sticky='w')
        self.put(ImporterFolderFrame(self)).grid(row=0, column=1, padx=(0, 20), pady=(0, 30), sticky='new', columnspan=4)

        # Error Handling
        self.put(ErrorHandlingLabel(self)).grid(row=1, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
        self.put(MuteWarningsCheckbox(self)).grid(row=1, column=1, padx=10, pady=(0, 30), sticky='w')
        self.put(CallsLoggingCheckbox(self)).grid(row=1, column=2, padx=10, pady=(0, 30), sticky='w')
        self.put(DebugLoggingCheckbox(self)).grid(row=1, column=3, padx=10, pady=(0, 30), sticky='w')

        # Shader Hunting
        self.put(ShaderHuntingLabel(self)).grid(row=2, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
        self.put(EnableHuntingCheckbox(self)).grid(row=2, column=1, padx=10, pady=(0, 30), sticky='w')
        self.put(DumpShadersCheckbox(self)).grid(row=2, column=2, padx=10, pady=(0, 30), sticky='w')

        # Fail-Safe
        self.put(FailSafeLabel(self)).grid(row=3, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
        self.put(EnforceRenderingCheckbox(self)).grid(row=3, column=1, padx=10, pady=(0, 30), sticky='w', columnspan=2)


class ShaderHuntingLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.importer.shader_hunting'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class EnableHuntingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.importer.enable_hunting'),
            variable=Vars.Active.Migoto.enable_hunting,
            master=master)
        self.set_tooltip(I18n._('tooltip.enable_hunting'))


class DumpShadersCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.importer.dump_shaders'),
            variable=Vars.Active.Migoto.dump_shaders,
            master=master)
        self.set_tooltip(I18n._('tooltip.dump_shaders'))


class ErrorHandlingLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.importer.error_handling'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class ImporterFolderFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            border_color = ThemeManager.theme["CTkEntry"].get("border_color", None),
            border_width = ThemeManager.theme["CTkEntry"].get("border_width", None),
            fg_color = ThemeManager.theme["CTkEntry"].get("fg_color", None),
            master=master)

        self.grid_columnconfigure(0, weight=100)

        self.put(ImporterFolderEntry(self)).grid(row=0, column=0, padx=(4, 2), pady=(2, 0), sticky='new')
        self.put(ChangeImporterFolderButton(self)).grid(row=0, column=1, padx=(0, 4), pady=(2, 2), sticky='ne')


class MuteWarningsCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.importer.mute_warnings'),
            variable=Vars.Active.Migoto.mute_warnings,
            master=master)
        self.set_tooltip(I18n._('tooltip.mute_warnings'))


class CallsLoggingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.importer.calls_logging'),
            variable=Vars.Active.Migoto.calls_logging,
            master=master)
        self.set_tooltip(I18n._('tooltip.calls_logging'))


class DebugLoggingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.importer.debug_logging'),
            variable=Vars.Active.Migoto.debug_logging,
            master=master)
        self.set_tooltip(I18n._('tooltip.debug_logging'))


class ImporterFolderLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.importer.importer_folder'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)
        self.trace_save(Vars.Settings.Launcher.active_importer, self.handle_active_importer_update)

    def handle_active_importer_update(self, var, val, old_val):
        self.configure(text=f'{val} {I18n._("settings.importer.folder")}')


class ImporterFolderEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.importer_folder,
            width=200,
            height=32,
            border_width=0,
            font=('Arial', 14),
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        return I18n._('tooltip.importer_folder').format(
            importer=Config.Launcher.active_importer
        )


class ChangeImporterFolderButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text=I18n._('buttons.browse'),
            command=self.change_importer_folder,
            width=80,
            height=32,
            font=('Roboto', 14),
            border_width=0,
            master=master)
        fg_color = ThemeManager.theme["CTkEntry"].get("fg_color", None)
        self.configure(
            fg_color=fg_color,
            hover_color=fg_color,
            text_color=["#000000", "#aaaaaa"],
            text_color_hovered=["#000000", "#ffffff"],
        )

    def change_importer_folder(self):
        importer_folder = filedialog.askdirectory(initialdir=Vars.Active.Importer.importer_folder.get())
        if importer_folder == '':
            return
        Vars.Active.Importer.importer_folder.set(importer_folder)


class FailSafeLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.importer.ini_protection'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class EnforceRenderingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.importer.enforce_rendering'),
            variable=Vars.Active.Migoto.enforce_rendering,
            master=master)
        self.set_tooltip(I18n._('tooltip.enforce_rendering').format(
            importer=Config.Launcher.active_importer,
            texture_hash=0 if Config.Launcher.active_importer != "WWMI" else 1,
            track_texture_updates=0 if Config.Launcher.active_importer != "WWMI" else 1
        ))
