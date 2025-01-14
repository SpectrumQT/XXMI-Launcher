from customtkinter import filedialog, ThemeManager

import core.event_manager as Events
import core.config_manager as Config
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
            text='Shader Hunting:',
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class EnableHuntingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Enable Hunting',
            variable=Vars.Active.Migoto.enable_hunting,
            master=master)
        self.set_tooltip(
            'Enabled: Allows to toggle Hunting Mode via Numpad [0] hotkey.\n'
            '* [d3dx.ini]: hunting = 2\n'
            'Disabled: Hunting Mode is hard disabled.\n'
            '* [d3dx.ini]: hunting = 0')


class DumpShadersCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Dump Shaders',
            variable=Vars.Active.Migoto.dump_shaders,
            master=master)
        self.set_tooltip(
            'Enabled: Hunting Mode [Copy Hash] key also saves selected shader as file in ShaderFixes.\n'
            '* [d3dx.ini]: marking_actions = clipboard hlsl asm regex\n'
            'Disabled: Hunting Mode [Copy Hash] only copies hash of selected shader to clipboard.\n'
            '* [d3dx.ini]: marking_actions = clipboard')


class ErrorHandlingLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Error Handling:',
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
            text='Mute Warnings',
            variable=Vars.Active.Migoto.mute_warnings,
            master=master)
        self.set_tooltip(
            'Enabled: No error warnings or beeps whatsoever. Ignorance is bliss.\n'
            '* [d3dx.ini]: show_warnings = 0\n'
            'Disabled: Ini parser error warnings and beeps on F10 will haunt poor souls.\n'
            '* [d3dx.ini]: show_warnings = 1')


class CallsLoggingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Calls Logging',
            variable=Vars.Active.Migoto.calls_logging,
            master=master)
        self.set_tooltip(
            'Enabled: Log API usage.\n'
            '* [d3dx.ini]: calls = 1\n'
            'Disabled: Do not log calls. Maximum performance.\n'
            '* [d3dx.ini]: calls = 0')


class DebugLoggingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Debug Logging',
            variable=Vars.Active.Migoto.debug_logging,
            master=master)
        self.set_tooltip(
            'Enabled: Super verbose debug logging.\n'
            '* [d3dx.ini]: debug = 1\n'
            'Disabled: No debug logging. Maximum performance.\n'
            '* [d3dx.ini]: debug = 0')


class ImporterFolderLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Importer Folder:',
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)
        self.trace_save(Vars.Settings.Launcher.active_importer, self.handle_active_importer_update)

    def handle_active_importer_update(self, var, val, old_val):
        self.configure(text=f'{val} Folder:')


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
        msg = f'* Absolute: Allows to move {Config.Launcher.active_importer} folder to any location (must start with disc name, i.e. "C:/Games/{Config.Launcher.active_importer}/").' + '\n'
        msg += f'* Relative: Allows to move {Config.Launcher.active_importer} folder to another location INSIDE the Launcher folder (i.e. default "{Config.Launcher.active_importer}/").'
        return msg.strip()


class ChangeImporterFolderButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text='Browse...',
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
            text='Ini Protection:',
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class EnforceRenderingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Enforce Rendering Settings',
            variable=Vars.Active.Migoto.enforce_rendering,
            master=master)
        self.set_tooltip(
            f'Enabled: Ensure {Config.Launcher.active_importer}-compatible [Rendering] section settings.\n'
            f'* [d3dx.ini]: texture_hash = {0 if Config.Launcher.active_importer != "WWMI" else 1}\n'
            f'* [d3dx.ini]: track_texture_updates = {0 if Config.Launcher.active_importer != "WWMI" else 1}\n'
            'Disabled: Settings above will not be forced into d3dx.ini.')
