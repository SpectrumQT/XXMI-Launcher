import core.event_manager as Events
import core.config_manager as Config
import gui.vars as Vars
from core.locale_manager import L

from customtkinter import END
from gui.classes.containers import UIFrame
from gui.classes.widgets import UITextbox, UILabel, UIEntry, UICheckbox, UIOptionMenu


class AdvancedSettingsFrame(UIFrame):
    def __init__(self, master):
        super().__init__(master)

        self.grid_columnconfigure((0, 1, 3, 4), weight=1)
        self.grid_columnconfigure(2, weight=100)

        # Update Policy
        self.put(UpdatePolicyLabel(self)).grid(row=0, column=0, padx=20, pady=(0, 25), sticky='w')
        self.put(OverwriteIniCheckbox(self)).grid(row=0, column=1, padx=10, pady=(0, 25), sticky='w')

        # Security
        self.put(SecurityLabel(self)).grid(row=0, column=2, padx=(20, 160), pady=(0, 25), sticky='e', columnspan=3)
        self.put(UnsafeModeCheckbox(self)).grid(row=0, column=2, padx=(10, 20), pady=(0, 25), sticky='e', columnspan=3)

        # Pre-Launch Command
        self.put(RunPreLaunchCheckbox(self)).grid(row=3, column=0, padx=(20, 0), pady=(0, 25), sticky='w')
        self.put(RunPreLaunchEntry(self)).grid(row=3, column=1, padx=(10, 125), pady=(0, 25), sticky='ew', columnspan=4)
        self.put(RunPreLaunchWaitCheckbox(self)).grid(row=3, column=4, padx=(10, 20), pady=(0, 25), sticky='w')
        self.grab(RunPreLaunchCheckbox).set_tooltip(self.grab(RunPreLaunchEntry))

        # Custom Launch Command
        self.put(CustomLaunchCheckbox(self)).grid(row=4, column=0, padx=(20, 0), pady=(0, 25), sticky='w')
        self.put(CustomLaunchEntry(self)).grid(row=4, column=1, padx=(10, 125), pady=(0, 25), sticky='ew', columnspan=4)
        self.put(CustomLaunchInjectModeOptionMenu(self)).grid(row=4, column=4, padx=(10, 20), pady=(0, 25), sticky='w')
        self.grab(CustomLaunchCheckbox).set_tooltip(self.grab(CustomLaunchEntry))

        # Post-Load Command
        self.put(RunPostLoadCheckbox(self)).grid(row=5, column=0, padx=(20, 0), pady=(0, 25), sticky='w')
        self.put(RunPostLoadEntry(self)).grid(row=5, column=1, padx=(10, 125), pady=(0, 25), sticky='ew', columnspan=4)
        self.put(RunPostLoadWaitCheckbox(self)).grid(row=5, column=4, padx=(10, 20), pady=(0, 25), sticky='w')
        self.grab(RunPostLoadCheckbox).set_tooltip(self.grab(RunPostLoadEntry))

        # Extra Libraries Injection
        self.put(InjectLibrariesCheckbox(self)).grid(row=6, column=0, padx=(20, 0), pady=(0, 25), sticky='w')
        self.put(InjectLibrariesTextbox(self)).grid(row=6, column=1, padx=(10, 20), pady=(0, 25), sticky='ew', columnspan=4)
        self.grab(InjectLibrariesCheckbox).set_tooltip(self.grab(InjectLibrariesTextbox))


class UpdatePolicyLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('advanced_settings_update_policy_label', 'Update Policy:')),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class OverwriteIniCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('advanced_settings_overwrite_ini_checkbox', 'Overwrite d3dx.ini')),
            variable=Vars.Active.Importer.overwrite_ini,
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        msg = str(L('advanced_settings_overwrite_ini_tooltip_enabled', 'Enabled: {importer} updates will overwrite existing d3dx.ini to ensure its up-to-date state.').format(importer=Config.Launcher.active_importer)) + '\n'
        msg += str(L('advanced_settings_overwrite_ini_tooltip_disabled', 'Disabled: {importer} updates will keep existing d3dx.ini untouched.').format(importer=Config.Launcher.active_importer))
        return msg.strip()


class SecurityLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('advanced_settings_security_label', 'Security:')),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class UnsafeModeCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('advanced_settings_unsafe_mode_checkbox', 'Unsafe Mode')),
            variable=Vars.Active.Migoto.unsafe_mode,
            master=master)
        self.set_tooltip(str(L('advanced_settings_unsafe_mode_tooltip',
            'Enabled: Allow 3-rd party 3dmigoto dlls.\n'
            'Disabled: Disallow 3-rd party 3dmigoto dlls.\n'
            'Note: If 3-rd party d3d11.dll does not support running from nested directories, it will fail to load.')))


class RunPreLaunchCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            variable=Vars.Active.Importer.run_pre_launch_enabled,
            text=str(L('advanced_settings_run_pre_launch_checkbox', 'Run Pre-Launch:')),
            font=('Microsoft YaHei', 14, 'bold'),
            master=master)
        self.set_tooltip(str(L('advanced_settings_option_toggle_tooltip',
                         'Enabled: Option will have stated effect.\n'
                         'Disabled: Option will have no effect.')),
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
        self.set_tooltip(str(L('advanced_settings_run_pre_launch_tooltip',
            'Windows console command to be executed before game exe launch.\n'
            'Note: If something needs to be done before the game start, do it here.')))

        self.trace_write(Vars.Active.Importer.run_pre_launch_enabled, self.handle_write_run_pre_launch_enabled)

    def handle_write_run_pre_launch_enabled(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')

    # def handle_unsafe_mode_update(self, var, val):
    #     if val:
    #         self.configure(state='normal', fg_color='#ffffff')
    #     else:
    #         self.configure(state='disabled', fg_color='#c0c0c0')


class RunPreLaunchWaitCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('advanced_settings_wait_button', 'Wait')),
            variable=Vars.Active.Importer.run_pre_launch_wait,
            width=10,
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(str(L('advanced_settings_run_pre_launch_wait_tooltip',
            'Enabled: Wait for (blocking) command to finish its execution before launching the game exe.')))

        self.trace_write(Vars.Active.Importer.run_pre_launch_enabled, self.handle_write_run_pre_launch_enabled)

    def handle_write_run_pre_launch_enabled(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')

    # def handle_unsafe_mode_update(self, var, val):
    #     if val:
    #         self.configure(state='normal')
    #     else:
    #         self.configure(state='disabled')


class CustomLaunchCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            variable=Vars.Active.Importer.custom_launch_enabled,
            text=str(L('advanced_settings_custom_launch_checkbox', 'Custom Launch:')),
            font=('Microsoft YaHei', 14, 'bold'),
            master=master)
        self.set_tooltip(str(L('advanced_settings_option_toggle_tooltip',
                         'Enabled: Option will have stated effect.\n'
                         'Disabled: Option will have no effect.')),
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

        self.trace_write(Vars.Active.Importer.custom_launch_enabled, self.handle_write_custom_launch_enabled)

    def handle_write_custom_launch_enabled(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')

    def get_tooltip(self):
        message = ''
        message += str(L('advanced_settings_custom_launch_tooltip_base', 'Windows console command to run when Start button is pressed instead of default game exe launch.\n'))
        message += str(L('advanced_settings_custom_launch_tooltip_hint', 'Hint: If you want to change injection method only, just leave this field empty.\n'))
        message += str(L('advanced_settings_custom_launch_tooltip_warning', 'Warning! This command also overrides `Launch Options` from General Settings.\n'))
        if Config.Launcher.active_importer == 'WWMI':
            message += str(L('advanced_settings_custom_launch_tooltip_wwmi_warning', 'Warning! Make sure to pass `-dx11` argument to Client-Win64-Shipping.exe to force DX11 mode!\n'))
        message += str(L('advanced_settings_custom_launch_tooltip_note', 'Note: If you want to start game exe with another custom exe, do it here.\n'))
        message += str(L('advanced_settings_custom_launch_tooltip_example', 'Example (equivalent for command internally used by launcher to start GI via FPS unlocker):\n'))
        message += r'`start /d "C:\Games\XXMI Launcher\Resources\Packages\GI-FPS-Unlocker" unlockfps_nc.exe`'
        return message


class CustomLaunchInjectModeOptionMenu(UIOptionMenu):
    def __init__(self, master):
        super().__init__(
            values=['Hook', 'Inject', 'Bypass'],
            variable=Vars.Active.Importer.custom_launch_inject_mode,
            width=90,
            height=36,
            font=('Arial', 14),
            dropdown_font=('Arial', 14),
            master=master)
        self.set_tooltip(str(L('advanced_settings_custom_launch_inject_mode_tooltip',
                         'Defines the way of 3dmigoto injection into the game process started via Custom Launch.\n'
                         '* Inject: Use WriteProcessMemory, more reliable but requires direct memory access.\n'
                         '* Hook: Use SetWindowsHookEx, less reliable, but potentially less prominent for anti-cheats.\n'
                         '* Bypass: Skip 3dmigoto injection and process only Inject Libraries field.')))

        self.trace_write(Vars.Active.Importer.custom_launch_enabled, self.handle_write_custom_launch_enabled)

    def handle_write_custom_launch_enabled(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')


class RunPostLoadCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            variable=Vars.Active.Importer.run_post_load_enabled,
            text=str(L('advanced_settings_run_post_load_checkbox', 'Run Post-Load:')),
            font=('Microsoft YaHei', 14, 'bold'),
            master=master)
        self.set_tooltip(str(L('advanced_settings_option_toggle_tooltip',
                         'Enabled: Option will have stated effect.\n'
                         'Disabled: Option will have no effect.')),
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
        self.set_tooltip(str(L('advanced_settings_run_post_load_tooltip',
            'Windows console command to be executed after hooking d3d11.dll to launched game exe.\n'
            'Note: If something needs to be done after 3dmigoto injection, do it here.')))

        self.trace_write(Vars.Active.Importer.run_post_load_enabled, self.handle_write_run_post_load_enabled)

    def handle_write_run_post_load_enabled(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')

    # def handle_unsafe_mode_update(self, var, val):
    #     if val:
    #         self.configure(state='normal', fg_color='#ffffff')
    #     else:
    #         self.configure(state='disabled', fg_color='#c0c0c0')


class RunPostLoadWaitCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('advanced_settings_wait_button', 'Wait')),
            variable=Vars.Active.Importer.run_post_load_wait,
            width=10,
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(str(L('advanced_settings_run_post_load_wait_tooltip',
            'Enabled: Wait for (blocking) command to finish its execution before treating the game launch as complete.')))

        self.trace_write(Vars.Active.Importer.run_post_load_enabled, self.handle_write_run_post_load_enabled)

    def handle_write_run_post_load_enabled(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')

    # def handle_unsafe_mode_update(self, var, val):
    #     if val:
    #         self.configure(state='normal')
    #     else:
    #         self.configure(state='disabled')


class InjectLibrariesCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            variable=Vars.Active.Importer.extra_libraries_enabled,
            text=str(L('advanced_settings_inject_libraries_checkbox', 'Inject Libraries:')),
            font=('Microsoft YaHei', 14, 'bold'),
            master=master)
        self.set_tooltip(str(L('advanced_settings_option_toggle_tooltip',
                         'Enabled: Option will have stated effect.\n'
                         'Disabled: Option will have no effect.')),
                         delay=0.5,)


class InjectLibrariesTextbox(UITextbox):
    def __init__(self, master):
        super().__init__(
            text_variable=Vars.Active.Importer.extra_libraries,
            height=90,
            undo=True,
            master=master)
        self.set_tooltip(str(L('advanced_settings_inject_libraries_tooltip',
            'List of additional DLL paths to inject into the game process. 1 path per line.\n'
            'injection will be made via WriteProcessMemory method.\n'
            'Example (inject ReShade dll):\n'
            r'`C:\Games\ReShade\ReShade64.dll`')))

        self.trace_write(Vars.Active.Importer.extra_libraries_enabled, self.handle_write_extra_libraries_enabled)

    def handle_write_extra_libraries_enabled(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')

    def get(self, index1, index2=None):
        return super().get(index1, index2).strip()
