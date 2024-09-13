import core.event_manager as Events
import core.config_manager as Config
import gui.vars as Vars

from customtkinter import END
from gui.classes.containers import UIFrame
from gui.classes.widgets import UITextbox, UILabel, UIEntry, UICheckbox


class AdvancedSettingsFrame(UIFrame):
    def __init__(self, master):
        super().__init__(master)

        self.grid_columnconfigure((0, 1, 3), weight=1)
        self.grid_columnconfigure(2, weight=100)

        # Update Policy
        self.put(UpdatePolicyLabel(self)).grid(row=0, column=0, padx=20, pady=(10, 10), sticky='w')
        self.put(AutoUpdateCheckbox(self)).grid(row=0, column=1, padx=20, pady=(10, 10), sticky='w')
        self.put(OverwriteIniCheckbox(self)).grid(row=0, column=2, padx=20, pady=(10, 10), sticky='w', columnspan=2)

        # Security
        self.put(SecurityLabel(self)).grid(row=2, column=0, padx=20, pady=(10, 10), sticky='w')
        self.put(UnsafeModeCheckbox(self)).grid(row=2, column=1, padx=20, pady=(10, 10), sticky='w', columnspan=3)

        # Pre-Launch Command
        self.put(RunPreLaunchLabel(self)).grid(row=3, column=0, padx=(20, 0), pady=(10, 10), sticky='w')
        self.put(RunPreLaunchEntry(self)).grid(row=3, column=1, padx=20, pady=(10, 10), sticky='ew', columnspan=2)
        self.put(RunPreLaunchWaitCheckbox(self)).grid(row=3, column=3, padx=20, pady=(10, 10), sticky='w')

        # Post-Load Command
        self.put(RunPostLoadLabel(self)).grid(row=4, column=0, padx=(20, 0), pady=(10, 10), sticky='w')
        self.put(RunPostLoadEntry(self)).grid(row=4, column=1, padx=20, pady=(10, 10), sticky='ew', columnspan=2)
        self.put(RunPostLoadWaitCheckbox(self)).grid(row=4, column=3, padx=20, pady=(10, 10), sticky='w')

        # Extra Libraries Injection
        self.put(InjectLibrariesLabel(self)).grid(row=5, column=0, padx=(20, 0), pady=(10, 10), sticky='w')
        self.put(InjectLibrariesTextbox(self)).grid(row=5, column=1, padx=20, pady=(10, 10), sticky='ew', columnspan=2)


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


class RunPreLaunchLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Run Pre-Launch:',
            font=('Roboto', 16, 'bold'),
            fg_color='transparent',
            master=master)


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
            'FYI: If something needs to be done before the game start, do it here.')

    # def handle_unsafe_mode_update(self, var, val):
    #     if val:
    #         self.configure(state='normal', fg_color='#ffffff')
    #     else:
    #         self.configure(state='disabled', fg_color='#c0c0c0')


class RunPreLaunchWaitCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Wait For Finish',
            variable=Vars.Active.Importer.run_pre_launch_wait,
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(
            'Enabled: Wait for (blocking) command to finish its execution before launching the game exe.')

    # def handle_unsafe_mode_update(self, var, val):
    #     if val:
    #         self.configure(state='normal')
    #     else:
    #         self.configure(state='disabled')


class RunPostLoadLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Run Post-Load:',
            font=('Roboto', 16, 'bold'),
            fg_color='transparent',
            master=master)


class RunPostLoadEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.run_post_load,
            width=100,
            height=36,
            font=('Arial', 14),
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(
            'Windows console command to be executed after hooking d3d11.dll to launched game exe.\n'
            'FYI: If something needs to be done after 3dmigoto injection, do it here.')

    # def handle_unsafe_mode_update(self, var, val):
    #     if val:
    #         self.configure(state='normal', fg_color='#ffffff')
    #     else:
    #         self.configure(state='disabled', fg_color='#c0c0c0')


class RunPostLoadWaitCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Wait For Finish',
            variable=Vars.Active.Importer.run_post_load_wait,
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(
            'Enabled: Wait for (blocking) command to finish its execution before treating the game launch as complete.')

    # def handle_unsafe_mode_update(self, var, val):
    #     if val:
    #         self.configure(state='normal')
    #     else:
    #         self.configure(state='disabled')


class InjectLibrariesLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Inject Libraries:',
            font=('Roboto', 16, 'bold'),
            fg_color='transparent',
            master=master)


class InjectLibrariesTextbox(UITextbox):
    def __init__(self, master):
        super().__init__(
            text_variable=Vars.Active.Importer.extra_libraries,
            height=80,
            undo=True,
            master=master)
        self.set_tooltip(
            'List of additional DLL paths to inject into the game process. 1 path per line.')

