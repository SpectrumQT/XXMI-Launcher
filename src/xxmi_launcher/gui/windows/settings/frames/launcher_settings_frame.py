from pathlib import Path
from textwrap import dedent

import core.event_manager as Events
import core.config_manager as Config
import core.path_manager as Paths
import gui.vars as Vars

from gui.classes.containers import UIFrame
from gui.classes.widgets import UILabel, UIButton, UIEntry, UICheckbox,  UIOptionMenu


class LauncherSettingsFrame(UIFrame):
    def __init__(self, master):
        super().__init__(master)

        # Auto close
        self.put(LauncherLabel(self)).grid(row=0, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
        self.put(AutoCloseCheckbox(self)).grid(row=0, column=1, padx=(10, 10), pady=(0, 30), sticky='w', columnspan=3)

        # Update Policy
        self.put(UpdatePolicyLabel(self)).grid(row=1, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
        self.put(AutoUpdateCheckbox(self)).grid(row=1, column=1, padx=10, pady=(0, 30), sticky='w')

        # Theme
        self.put(ThemeLabel(self)).grid(row=2, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
        self.put(LauncherThemeOptionMenu(self)).grid(row=2, column=1, padx=(10, 10), pady=(0, 30), sticky='w')
        self.put(ApplyThemeButton(self)).grid(row=2, column=2, padx=(10, 20), pady=(0, 30), sticky='w')
        self.put(EnableDevMode(self)).grid(row=2, column=3, padx=(60, 20), pady=(0, 30), sticky='w', columnspan=2)


class LauncherLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Start Behavior:',
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class AutoCloseCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Close Launcher After Game Start',
            variable=Vars.Launcher.auto_close,
            master=master)
        self.set_tooltip(
            'Enabled: Launcher will close itself once the game has started and 3dmigoto injection has been confirmed.\n'
            'Disabled: Launcher will keep itself running.')


class UpdatePolicyLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Update Policy:',
            font=('Microsoft YaHei', 14, 'bold'),
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


class ThemeLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='UI Theme:',
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class LauncherThemeOptionMenu(UIOptionMenu):
    def __init__(self, master):
        super().__init__(
            values=['Default'],
            variable=Vars.Launcher.gui_theme,
            width=150,
            height=36,
            font=('Arial', 14),
            dropdown_font=('Arial', 14),
            master=master)
        self.set_tooltip('Select launcher GUI theme.\n'
                         'Warning! `Default` theme will be overwritten by launcher updates!\n'
                         'To make a custom theme:\n'
                         '1. Create a duplicate of `Default` folder in `Themes` folder.\n'
                         '2. Rename the duplicate in a way you want it to be shown in Settings.\n'
                         '3. Edit or replace any images (valid extensions: webp, jpeg, png, jpg).')

    def update_values(self):
        values = ['Default']
        for path in Paths.App.Themes.iterdir():
            if path.is_dir() and path.name != 'Default':
                values.append(path.name)
        self.configure(values=values)

    def _open_dropdown_menu(self):
        self.update_values()
        super()._open_dropdown_menu()


class ApplyThemeButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text='⟲ Apply',
            command=self.apply_theme,
            width=100,
            height=36,
            font=('Roboto', 14),
            master=master)

        self.trace_write(Vars.Launcher.gui_theme, self.handle_write_gui_theme)

        self.hide()

    def apply_theme(self):
        Events.Fire(Events.Application.CloseSettings(save=True))
        Events.Fire(Events.Application.Restart(delay=0))

    def handle_write_gui_theme(self, var, val):
        if val != Config.Config.active_theme:
            self.show()
        else:
            self.hide()


class EnableDevMode(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Dev Mode',
            variable=Vars.Launcher.theme_dev_mode,
            master=master)
        self.set_tooltip(
            'Enabled: Launcher will track changes in `custom-tkinter-theme.json` and apply them on the fly.\n'
            'Disabled: Theme changes will not be tracked.')

        self.trace_write(Vars.Launcher.theme_dev_mode, self.handle_write_theme_dev_mode)

    def handle_write_theme_dev_mode(self, var, val):
        Config.Config.Launcher.theme_dev_mode = val
        Events.Fire(Events.GUI.ToggleThemeDevMode(enabled=val))
