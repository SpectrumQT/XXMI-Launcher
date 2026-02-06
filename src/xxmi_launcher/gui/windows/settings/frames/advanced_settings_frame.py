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

        # Pre-Launch Command
        self.put(RunPreLaunchCheckbox(self)).grid(row=0, column=0, padx=(20, 0), pady=(0, 25), sticky='w')
        self.put(RunPreLaunchEntry(self)).grid(row=0, column=1, padx=(10, 125), pady=(0, 25), sticky='ew', columnspan=4)
        self.put(RunPreLaunchWaitCheckbox(self)).grid(row=0, column=4, padx=(10, 20), pady=(0, 25), sticky='w')
        self.grab(RunPreLaunchCheckbox).set_tooltip(self.grab(RunPreLaunchEntry))

        # Custom Launch Command
        self.put(CustomLaunchCheckbox(self)).grid(row=1, column=0, padx=(20, 0), pady=(0, 25), sticky='w')
        self.put(CustomLaunchEntry(self)).grid(row=1, column=1, padx=(10, 125), pady=(0, 25), sticky='ew', columnspan=4)
        self.put(CustomLaunchInjectModeOptionMenu(self)).grid(row=1, column=4, padx=(10, 20), pady=(0, 25), sticky='w')
        self.grab(CustomLaunchCheckbox).set_tooltip(self.grab(CustomLaunchEntry))

        # Post-Load Command
        self.put(RunPostLoadCheckbox(self)).grid(row=2, column=0, padx=(20, 0), pady=(0, 25), sticky='w')
        self.put(RunPostLoadEntry(self)).grid(row=2, column=1, padx=(10, 125), pady=(0, 25), sticky='ew', columnspan=4)
        self.put(RunPostLoadWaitCheckbox(self)).grid(row=2, column=4, padx=(10, 20), pady=(0, 25), sticky='w')
        self.grab(RunPostLoadCheckbox).set_tooltip(self.grab(RunPostLoadEntry))

        # Extra Libraries Injection
        self.put(InjectLibrariesCheckbox(self)).grid(row=3, column=0, padx=(20, 0), pady=(0, 25), sticky='w')
        self.put(InjectLibrariesTextbox(self)).grid(row=3, column=1, padx=(10, 20), pady=(0, 25), sticky='ew', columnspan=4)
        self.grab(InjectLibrariesCheckbox).set_tooltip(self.grab(InjectLibrariesTextbox))

        # Security
        self.put(SecurityLabel(self)).grid(row=4, column=0, padx=(20, 0), pady=(0, 0), sticky='w')
        self.put(UnsafeModeFrame(self)).grid(row=4, column=1, padx=(10, 10), pady=(0, 0), sticky='w', columnspan=3)


class UnsafeModeFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            fg_color='transparent',
            master=master)

        self.grid_columnconfigure(0, weight=100)
        self.put(UnsafeModeCheckbox(self)).grid(row=0, column=0, padx=(0, 0), pady=(0, 0), sticky='ew')


class SecurityLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('advanced_settings_security_label', 'Security:'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class UnsafeModeCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=L('advanced_settings_unsafe_mode_checkbox', 'Unsafe Mode'),
            variable=Vars.Active.Migoto.unsafe_mode,
            master=master)
        self.set_tooltip(L('advanced_settings_unsafe_mode_checkbox_tooltip', """
            Enabled: Allow 3-rd party 3dmigoto dlls.
            Disabled: Disallow 3-rd party 3dmigoto dlls.
            Note: If 3-rd party d3d11.dll does not support running from nested directories, it will fail to load.
        """))

class RunPreLaunchCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            variable=Vars.Active.Importer.run_pre_launch_enabled,
            text=L('advanced_settings_run_pre_launch_checkbox', 'Run Pre-Launch:'),
            font=('Microsoft YaHei', 14, 'bold'),
            master=master)
        self.set_tooltip(L('advanced_settings_option_checkbox_tooltip', """
            Enabled: Option will have stated effect.
            Disabled: Option will have no effect.
        """), delay=0.5)


class RunPreLaunchEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.run_pre_launch,
            width=200,
            height=36,
            font=('Arial', 14),
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(L('advanced_settings_run_pre_launch_tooltip', """
            Windows console command to be executed before game exe launch.
            Note: If something needs to be done before the game start, do it here.
        """))

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
            text=L('advanced_settings_wait_checkbox', 'Wait'),
            variable=Vars.Active.Importer.run_pre_launch_wait,
            width=10,
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(L('advanced_settings_run_pre_launch_wait_checkbox_tooltip', """
            Enabled: Wait for (blocking) command to finish its execution before launching the game exe.
        """))
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
            text=L('advanced_settings_custom_launch_checkbox', 'Custom Launch:'),
            font=('Microsoft YaHei', 14, 'bold'),
            master=master)
        self.set_tooltip(L('advanced_settings_option_checkbox_tooltip', """
            Enabled: Option will have stated effect.
            Disabled: Option will have no effect.
        """), delay=0.5)


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
        return L('advanced_settings_custom_launch_entry_tooltip', """
            Windows console command to run when Start button is pressed instead of default game exe launch.
            Hint: If you want to change injection method only, just leave this field empty.
            Warning! This command also overrides `Launch Options` from General Settings.
            Note: If you want to start game exe with another custom exe, do it here.
            Example (equivalent for command internally used by launcher to start GI via FPS unlocker):
            `start /d "C:\Games\XXMI Launcher\Resources\Packages\GI-FPS-Unlocker" unlockfps_nc.exe`
        """)


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
        self.set_tooltip(L('advanced_settings_custom_launch_inject_mode_option_menu_tooltip', """
            Defines the way of 3dmigoto injection into the game process started via Custom Launch.
            * Inject: Use WriteProcessMemory, more reliable but requires direct memory access.
            * Hook: Use SetWindowsHookEx, less reliable, but potentially less prominent for anti-cheats.
            * Bypass: Skip 3dmigoto injection and process only Inject Libraries field.
        """))

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
            text=L('advanced_settings_run_post_load_checkbox', 'Run Post-Load:'),
            font=('Microsoft YaHei', 14, 'bold'),
            master=master)
        self.set_tooltip(L('advanced_settings_option_checkbox_tooltip', """
            Enabled: Option will have stated effect.
            Disabled: Option will have no effect.
        """), delay=0.5)


class RunPostLoadEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.run_post_load,
            width=120,
            height=36,
            font=('Arial', 14),
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(L('advanced_settings_run_post_load_checkbox_tooltip', """
            Windows console command to be executed after hooking d3d11.dll to launched game exe.
            Note: If something needs to be done after 3dmigoto injection, do it here.
        """))
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
            text=L('advanced_settings_wait_checkbox', 'Wait'),
            variable=Vars.Active.Importer.run_post_load_wait,
            width=10,
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(L('advanced_settings_run_post_load_wait_checkbox_tooltip', """
            Enabled: Wait for (blocking) command to finish its execution before treating the game launch as complete.
        """))
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
            text=L('advanced_settings_inject_libraries_checkbox', 'Inject Libraries:'),
            font=('Microsoft YaHei', 14, 'bold'),
            master=master)
        self.set_tooltip(L('advanced_settings_option_checkbox_tooltip', """
            Enabled: Option will have stated effect.
            Disabled: Option will have no effect.
        """), delay=0.5)


class InjectLibrariesTextbox(UITextbox):
    def __init__(self, master):
        super().__init__(
            text_variable=Vars.Active.Importer.extra_libraries,
            height=90,
            undo=True,
            master=master)
        self.set_tooltip(L('advanced_settings_inject_libraries_tooltip', """
            List of additional DLL paths to inject into the game process. 1 path per line.
            injection will be made via WriteProcessMemory method.
            Example (inject ReShade dll):
            `C:\Games\ReShade\ReShade64.dll`
        """))

        self.trace_write(Vars.Active.Importer.extra_libraries_enabled, self.handle_write_extra_libraries_enabled)

    def handle_write_extra_libraries_enabled(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')

    def get(self, index1, index2=None):
        return super().get(index1, index2).strip()
