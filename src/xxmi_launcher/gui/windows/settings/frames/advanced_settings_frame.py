import core.event_manager as Events
import core.config_manager as Config
import gui.vars as Vars

from customtkinter import END
from gui.classes.containers import UIFrame
from gui.classes.widgets import UITextbox, UILabel, UIEntry, UICheckbox, UIOptionMenu


class AdvancedSettingsFrame(UIFrame):
    def __init__(self, master):
        super().__init__(master)

        self.grid_columnconfigure((0, 1, 3, 4), weight=1)
        self.grid_columnconfigure(2, weight=100)

        # Update Policy
        self.put(UpdatePolicyLabel(self)).grid(row=0, column=0, padx=20, pady=(10, 10), sticky='w')
        self.put(AutoUpdateCheckbox(self)).grid(row=0, column=1, padx=10, pady=(10, 10), sticky='w')
        self.put(OverwriteIniCheckbox(self)).grid(row=0, column=2, padx=10, pady=(10, 10), sticky='w')

        # Security
        self.put(SecurityLabel(self)).grid(row=0, column=2, padx=(220, 10), pady=(10, 10), sticky='w', columnspan=3)
        self.put(UnsafeModeCheckbox(self)).grid(row=0, column=2, padx=(310, 10), pady=(10, 10), sticky='w', columnspan=3)

        # Pre-Launch Command
        self.put(RunPreLaunchCheckbox(self)).grid(row=3, column=0, padx=(20, 0), pady=(10, 10), sticky='w')
        self.put(RunPreLaunchEntry(self)).grid(row=3, column=1, padx=(10, 125), pady=(10, 10), sticky='ew', columnspan=4)
        self.put(RunPreLaunchWaitCheckbox(self)).grid(row=3, column=4, padx=(10, 20), pady=(10, 10), sticky='w')

        # Custom Launch Command
        self.put(CustomLaunchCheckbox(self)).grid(row=4, column=0, padx=(20, 0), pady=(10, 10), sticky='w')
        self.put(CustomLaunchEntry(self)).grid(row=4, column=1, padx=(10, 125), pady=(10, 10), sticky='ew', columnspan=4)
        self.put(CustomLaunchInjectModeOptionMenu(self)).grid(row=4, column=4, padx=(10, 20), pady=(10, 10), sticky='w')

        # Post-Load Command
        self.put(RunPostLoadCheckbox(self)).grid(row=5, column=0, padx=(20, 0), pady=(10, 10), sticky='w')
        self.put(RunPostLoadEntry(self)).grid(row=5, column=1, padx=(10, 125), pady=(10, 10), sticky='ew', columnspan=4)
        self.put(RunPostLoadWaitCheckbox(self)).grid(row=5, column=4, padx=(10, 20), pady=(10, 10), sticky='w')

        # Extra Libraries Injection
        self.put(InjectLibrariesCheckbox(self)).grid(row=6, column=0, padx=(20, 0), pady=(10, 10), sticky='w')
        self.put(InjectLibrariesTextbox(self)).grid(row=6, column=1, padx=(10, 20), pady=(10, 10), sticky='ew', columnspan=4)


class UpdatePolicyLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Update Policy:',
            font=('Roboto', 16, 'bold'),
            fg_color='transparent',
            master=master)


class AutoUpdateCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Auto Update',
            variable=Vars.Launcher.auto_update,
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        msg = f'Enabled: Launcher and {Config.Launcher.active_importer} updates will be Downloaded and Installed automatically.\n'
        msg += 'Disabled: Use special [▲] button next to [Start] button to Download and Install updates manually.'
        return msg.strip()


class OverwriteIniCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Overwrite d3dx.ini',
            variable=Vars.Active.Importer.overwrite_ini,
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        msg = f'Enabled: {Config.Launcher.active_importer} updates will overwrite existing d3dx.ini to ensure its up-to-date state.\n'
        msg += f'Disabled: {Config.Launcher.active_importer} updates will keep existing d3dx.ini untouched.'
        return msg.strip()


class SecurityLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Security:',
            font=('Roboto', 16, 'bold'),
            fg_color='transparent',
            master=master)


class UnsafeModeCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Unsafe Mode',
            variable=Vars.Active.Migoto.unsafe_mode,
            master=master)
        self.set_tooltip(
            'Enabled: Allow 3-rd party 3dmigoto dlls.\n'
            'Disabled: Disallow 3-rd party 3dmigoto dlls.\n'
            'Note: If 3-rd party d3d11.dll does not support running from nested directories, it will fail to load.')


class RunPreLaunchCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            variable=Vars.Active.Importer.run_pre_launch_enabled,
            text='Run Pre-Launch:',
            font=('Roboto', 16, 'bold'),
            master=master)
        self.set_tooltip(
                         'Enabled: Option will have stated effect.\n'
                         'Disabled: Option will have no effect.',
                         delay=0.5,)


class RunPreLaunchEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.run_pre_launch,
            width=200,
            height=36,
            font=('Arial', 14),
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(
            'Windows console command to be executed before game exe launch.\n'
            'Note: If something needs to be done before the game start, do it here.')

    # def handle_unsafe_mode_update(self, var, val):
    #     if val:
    #         self.configure(state='normal', fg_color='#ffffff')
    #     else:
    #         self.configure(state='disabled', fg_color='#c0c0c0')


class CustomLaunchCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            variable=Vars.Active.Importer.custom_launch_enabled,
            text='Custom Launch:',
            font=('Roboto', 16, 'bold'),
            master=master)
        self.set_tooltip(
                         'Enabled: Option will have stated effect.\n'
                         'Disabled: Option will have no effect.',
                         delay=0.5,)


class CustomLaunchEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.custom_launch,
            width=200,
            height=36,
            font=('Arial', 14),
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        message = ''
        message += 'Windows console command to run when Start button is pressed instead of default game exe launch.\n'
        message += 'Warning! This command also overrides `Launch Options` from General Settings.\n'
        if Config.Launcher.active_importer == 'WWMI':
            message += 'Warning! Make sure to pass `Client -DisableModule=streamline` arguments to Client-Win64-Shipping.exe to force DX11 mode!\n'
        message += 'Note: If you want to start game exe with another custom exe, do it here.\n'
        message += 'Example (equivalent for command internally used by launcher to start GI via FPS unlocker):\n'
        message += r'`start /d "C:\Games\XXMI Launcher\Resources\Packages\GI-FPS-Unlocker" unlockfps_nc.exe`'
        return message


class CustomLaunchInjectModeOptionMenu(UIOptionMenu):
    def __init__(self, master):
        super().__init__(
            values=['Inject', 'Hook'],
            variable=Vars.Active.Importer.custom_launch_inject_mode,
            width=90,
            height=36,
            font=('Arial', 14),
            dropdown_font=('Arial', 14),
            master=master)
        self.set_tooltip('Defines the way of d3d11.dll injection into the game process started via Custom Launch.\n'
                         '* Inject: Use WriteProcessMemory, more reliable but requires direct memory access.\n'
                         '* Hook: Use SetWindowsHookEx, less reliable, but potentially less prominent for anti-cheats.')


class RunPreLaunchWaitCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Wait',
            variable=Vars.Active.Importer.run_pre_launch_wait,
            width=10,
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(
            'Enabled: Wait for (blocking) command to finish its execution before launching the game exe.')

    # def handle_unsafe_mode_update(self, var, val):
    #     if val:
    #         self.configure(state='normal')
    #     else:
    #         self.configure(state='disabled')


class RunPostLoadCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            variable=Vars.Active.Importer.run_post_load_enabled,
            text='Run Post-Load:',
            font=('Roboto', 16, 'bold'),
            master=master)
        self.set_tooltip(
                         'Enabled: Option will have stated effect.\n'
                         'Disabled: Option will have no effect.',
                         delay=0.5,)


class RunPostLoadEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.run_post_load,
            width=120,
            height=36,
            font=('Arial', 14),
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(
            'Windows console command to be executed after hooking d3d11.dll to launched game exe.\n'
            'Note: If something needs to be done after 3dmigoto injection, do it here.')

    # def handle_unsafe_mode_update(self, var, val):
    #     if val:
    #         self.configure(state='normal', fg_color='#ffffff')
    #     else:
    #         self.configure(state='disabled', fg_color='#c0c0c0')


class RunPostLoadWaitCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Wait',
            variable=Vars.Active.Importer.run_post_load_wait,
            width=10,
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(
            'Enabled: Wait for (blocking) command to finish its execution before treating the game launch as complete.')

    # def handle_unsafe_mode_update(self, var, val):
    #     if val:
    #         self.configure(state='normal')
    #     else:
    #         self.configure(state='disabled')


class InjectLibrariesCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            variable=Vars.Active.Importer.extra_libraries_enabled,
            text='Inject Libraries:',
            font=('Roboto', 16, 'bold'),
            master=master)
        self.set_tooltip(
                         'Enabled: Option will have stated effect.\n'
                         'Disabled: Option will have no effect.',
                         delay=0.5,)


class InjectLibrariesTextbox(UITextbox):
    def __init__(self, master):
        super().__init__(
            text_variable=Vars.Active.Importer.extra_libraries,
            height=90,
            undo=True,
            master=master)
        self.set_tooltip(
            'List of additional DLL paths to inject into the game process. 1 path per line.\n'
            'injection will be made via WriteProcessMemory method.\n'
            'Example (inject ReShade dll):\n'
            '`C:\Games\ReShade\ReShade64.dll`')

    def get(self, index1, index2=None):
        return super().get(index1, index2).strip()
