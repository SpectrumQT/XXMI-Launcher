from customtkinter import filedialog, ThemeManager

import core.event_manager as Events
import core.config_manager as Config
import gui.vars as Vars
from core.locale_manager import L

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
            text=str(L('importer_settings_shader_hunting_label', 'Shader Hunting:')),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class EnableHuntingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('importer_settings_enable_hunting_checkbox', 'Enable Hunting')),
            variable=Vars.Active.Migoto.enable_hunting,
            master=master)
        self.set_tooltip(str(L('importer_settings_enable_hunting_tooltip',
            'Enabled: Allows to toggle Hunting Mode via Numpad [0] hotkey.\n'
            '* [d3dx.ini]: hunting = 2\n'
            'Disabled: Hunting Mode is hard disabled.\n'
            '* [d3dx.ini]: hunting = 0')))


class DumpShadersCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('importer_settings_dump_shaders_checkbox', 'Dump Shaders')),
            variable=Vars.Active.Migoto.dump_shaders,
            master=master)
        self.set_tooltip(str(L('importer_settings_dump_shaders_tooltip',
            'Enabled: Hunting Mode [Copy Hash] key also saves selected shader as file in ShaderFixes.\n'
            '* [d3dx.ini]: marking_actions = clipboard hlsl asm regex\n'
            'Disabled: Hunting Mode [Copy Hash] only copies hash of selected shader to clipboard.\n'
            '* [d3dx.ini]: marking_actions = clipboard')))


class ErrorHandlingLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('importer_settings_error_handling_label', 'Error Handling:')),
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
            text=str(L('importer_settings_mute_warnings_checkbox', 'Mute Warnings')),
            variable=Vars.Active.Migoto.mute_warnings,
            master=master)
        self.set_tooltip(str(L('importer_settings_mute_warnings_tooltip',
            'Enabled: No error warnings or beeps whatsoever. Ignorance is bliss.\n'
            '* [d3dx.ini]: show_warnings = 0\n'
            'Disabled: Ini parser error warnings and beeps on F10 will haunt poor souls.\n'
            '* [d3dx.ini]: show_warnings = 1')))


class CallsLoggingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('importer_settings_calls_logging_checkbox', 'Calls Logging')),
            variable=Vars.Active.Migoto.calls_logging,
            master=master)
        self.set_tooltip(str(L('importer_settings_calls_logging_tooltip',
            'Enabled: Log API usage.\n'
            '* [d3dx.ini]: calls = 1\n'
            'Disabled: Do not log calls. Maximum performance.\n'
            '* [d3dx.ini]: calls = 0')))


class DebugLoggingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('importer_settings_debug_logging_checkbox', 'Debug Logging')),
            variable=Vars.Active.Migoto.debug_logging,
            master=master)
        self.set_tooltip(str(L('importer_settings_debug_logging_tooltip',
            'Enabled: Super verbose debug logging.\n'
            '* [d3dx.ini]: debug = 1\n'
            'Disabled: No debug logging. Maximum performance.\n'
            '* [d3dx.ini]: debug = 0')))


class ImporterFolderLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('importer_settings_importer_folder_label', 'Importer Folder:')),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)
        self.trace_save(Vars.Settings.Launcher.active_importer, self.handle_active_importer_update)

    def handle_active_importer_update(self, var, val, old_val):
        self.configure(text=str(L('importer_settings_importer_folder_label_dynamic', '{importer} Folder:').format(importer=val)))


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
        msg = str(L('importer_settings_importer_folder_tooltip_base', 'path to folder containing `Mods` folder, `d3dx.ini` and other {importer} resources.').format(importer=Config.Launcher.active_importer)) + '\n'
        msg += str(L('importer_settings_importer_folder_tooltip_absolute', '**Absolute**: Set any arbitrary folder, i.e. `C:/Games/{importer}/`.').format(importer=Config.Launcher.active_importer)) + '\n'
        msg += str(L('importer_settings_importer_folder_tooltip_relative', '**Relative**: Set any folder **inside** the Launcher folder, i.e. `{importer}/` (default).').format(importer=Config.Launcher.active_importer))
        return msg.strip()


class ChangeImporterFolderButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text=str(L('importer_settings_browse_button', 'Browse...')),
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
            text=str(L('importer_settings_ini_protection_label', 'Ini Protection:')),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class EnforceRenderingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('importer_settings_enforce_rendering_checkbox', 'Enforce Rendering Settings')),
            variable=Vars.Active.Migoto.enforce_rendering,
            master=master)
        texture_hash_value = 0 if Config.Launcher.active_importer != "WWMI" else 1
        track_texture_updates_value = 0 if Config.Launcher.active_importer != "WWMI" else 1
        self.set_tooltip(str(L('importer_settings_enforce_rendering_tooltip',
            'Enabled: Ensure {importer}-compatible [Rendering] section settings.\n'
            '* [d3dx.ini]: texture_hash = {texture_hash}\n'
            '* [d3dx.ini]: track_texture_updates = {track_texture_updates}\n'
            'Disabled: Settings above will not be forced into d3dx.ini.').format(
                importer=Config.Launcher.active_importer,
                texture_hash=texture_hash_value,
                track_texture_updates=track_texture_updates_value
            )))
