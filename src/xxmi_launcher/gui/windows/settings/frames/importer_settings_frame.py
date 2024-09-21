from customtkinter import filedialog

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
        self.put(ImporterFolderLabel(self)).grid(row=0, column=0, padx=(20, 0), pady=(20, 20), sticky='w')
        self.put(ImporterFolderEntry(self)).grid(row=0, column=1, padx=10, pady=(20, 20), columnspan=4, sticky='ew')
        self.put(ChangeImporterFolderButton(self)).grid(row=0, column=5, padx=(0, 20), pady=(20, 20), sticky='e')

        # Error Handling
        self.put(ErrorHandlingLabel(self)).grid(row=1, column=0, padx=(20, 10), pady=(20, 20), sticky='w')
        self.put(MuteWarningsCheckbox(self)).grid(row=1, column=1, padx=10, pady=(20, 20), sticky='w')
        self.put(DebugLoggingCheckbox(self)).grid(row=1, column=3, padx=10, pady=(20, 20), sticky='w')

        # Shader Hunting
        self.put(ShaderHuntingLabel(self)).grid(row=2, column=0, padx=(20, 10), pady=(20, 20), sticky='w')
        self.put(EnableHuntingCheckbox(self)).grid(row=2, column=1, padx=10, pady=(20, 20), sticky='w')
        self.put(DumpShadersCheckbox(self)).grid(row=2, column=3, padx=10, pady=(20, 20), sticky='w')


class ShaderHuntingLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Shader Hunting:',
            font=('Roboto', 16, 'bold'),
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
            font=('Roboto', 16, 'bold'),
            fg_color='transparent',
            master=master)


class MuteWarningsCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Mute Warnings',
            variable=Vars.Active.Migoto.mute_warnings,
            master=master)
        self.set_tooltip(
            'Enabled: No error warnings or beeps whatsoever. Ignorance is bliss.\n'
            '* [d3dx.ini]: mute_warnings = 1\n'
            'Disabled: Ini parser error warnings and beeps on F10 will haunt poor souls.\n'
            '* [d3dx.ini]: mute_warnings = 0')


class DebugLoggingCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Debug Logging',
            variable=Vars.Active.Migoto.debug_logging,
            master=master)
        self.set_tooltip(
            'Enabled: Extensive verbose logging for crash debugging. Causes massive slow down.\n'
            'Disabled: No logging whatsoever. Maximum performance.')


class ImporterFolderLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Importer Folder:',
            font=('Roboto', 16, 'bold'),
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
            height=36,
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
            text='Change',
            command=self.change_importer_folder,
            width=70,
            height=36,
            font=('Roboto', 14),
            fg_color='#eeeeee',
            text_color='#000000',
            hover_color='#ffffff',
            border_width=1,
            master=master)

    def change_importer_folder(self):
        importer_folder = filedialog.askdirectory(initialdir=Vars.Active.Importer.importer_folder.get())
        if importer_folder == '':
            return
        Vars.Active.Importer.importer_folder.set(importer_folder)
