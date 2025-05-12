import core.event_manager as Events
import core.config_manager as Config
import core.i18n_manager as I18n
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
            text=I18n._('settings.advanced.update_policy'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class OverwriteIniCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.advanced.overwrite_d3dx'),
            variable=Vars.Active.Importer.overwrite_ini,
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        return I18n._('tooltip.overwrite_d3dx').format(
            importer=Config.Launcher.active_importer
        )


class SecurityLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.advanced.security'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class UnsafeModeCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.advanced.unsafe_mode'),
            variable=Vars.Active.Migoto.unsafe_mode,
            master=master)
        self.set_tooltip(I18n._('tooltip.unsafe_mode'))


class RunPreLaunchCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            variable=Vars.Active.Importer.run_pre_launch_enabled,
            text=I18n._('settings.advanced.run_pre_launch'),
            font=('Microsoft YaHei', 14, 'bold'),
            master=master)
        self.set_tooltip(I18n._('tooltip.option_enabled_effect'), delay=0.5)


class RunPreLaunchEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.run_pre_launch,
            width=200,
            height=36,
            font=('Arial', 14),
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(I18n._('tooltip.run_pre_launch'))

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
            text=I18n._('settings.advanced.wait'),
            variable=Vars.Active.Importer.run_pre_launch_wait,
            width=10,
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(I18n._('tooltip.wait_for_command'))

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
            text=I18n._('settings.advanced.custom_launch'),
            font=('Microsoft YaHei', 14, 'bold'),
            master=master)
        self.set_tooltip(I18n._('tooltip.option_enabled_effect'), delay=0.5)


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
        message = I18n._('tooltip.custom_launch')
        if Config.Launcher.active_importer == 'WWMI':
            message += I18n._('tooltip.custom_launch_wwmi')
        message += I18n._('tooltip.custom_launch_example')
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
        self.set_tooltip(I18n._('tooltip.custom_launch_inject_mode'))

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
            text=I18n._('settings.advanced.run_post_load'),
            font=('Microsoft YaHei', 14, 'bold'),
            master=master)
        self.set_tooltip(I18n._('tooltip.option_enabled_effect'), delay=0.5)


class RunPostLoadEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.run_post_load,
            width=120,
            height=36,
            font=('Arial', 14),
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(I18n._('tooltip.run_post_load'))

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
            text=I18n._('settings.advanced.wait'),
            variable=Vars.Active.Importer.run_post_load_wait,
            width=10,
            master=master)
        # self.trace_write(Vars.Active.Migoto.unsafe_mode, self.handle_unsafe_mode_update)
        self.set_tooltip(I18n._('tooltip.wait_post_command'))

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
            text=I18n._('settings.advanced.inject_libraries'),
            font=('Microsoft YaHei', 14, 'bold'),
            master=master)
        self.set_tooltip(I18n._('tooltip.option_enabled_effect'), delay=0.5)


class InjectLibrariesTextbox(UITextbox):
    def __init__(self, master):
        super().__init__(
            text_variable=Vars.Active.Importer.extra_libraries,
            height=90,
            undo=True,
            master=master)
        self.set_tooltip(I18n._('tooltip.inject_libraries'))

        self.trace_write(Vars.Active.Importer.extra_libraries_enabled, self.handle_write_extra_libraries_enabled)

    def handle_write_extra_libraries_enabled(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')

    def get(self, index1, index2=None):
        return super().get(index1, index2).strip()
