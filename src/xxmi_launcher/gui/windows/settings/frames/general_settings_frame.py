import subprocess
from pathlib import Path
from customtkinter import filedialog

import core.event_manager as Events
import core.config_manager as Config
import core.path_manager as Paths
import gui.vars as Vars

from gui.classes.containers import UIFrame
from gui.classes.widgets import UILabel, UIButton, UIEntry, UICheckbox,  UIOptionMenu


class GeneralSettingsFrame(UIFrame):
    def __init__(self, master):
        super().__init__(master)

        self.grid_columnconfigure((0, 2, 3), weight=1)
        self.grid_columnconfigure(1, weight=100)
        self.grid_rowconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(6, weight=100)

        # Game Folder
        self.put(GameFolderLabel(self)).grid(row=0, column=0, padx=(20, 0), pady=(10, 10), sticky='wn')
        game_folder_error = self.put(GameFolderErrorLabel(self))
        self.put(GameFolderEntry(self, game_folder_error)).grid(row=0, column=1, padx=(10, 100), pady=(10, 10), sticky='ewn', columnspan=3)
        self.put(ChangeGameFolderButton(self)).grid(row=0, column=3, padx=(0, 20), pady=(10, 10), sticky='en')

        # Launch Options
        self.put(LaunchOptionsLabel(self)).grid(row=1, column=0, padx=(20, 10), pady=(10, 10), sticky='w')
        self.put(LaunchOptionsEntry(self)).grid(row=1, column=1, padx=(10, 20), pady=(10, 10), sticky='ew', columnspan=3)

        # Process Priority
        self.put(ProcessPriorityLabel(self)).grid(row=2, column=0, padx=20, pady=(10, 10), sticky='ew')
        self.put(ProcessPriorityOptionMenu(self)).grid(row=2, column=1, padx=(10, 10), pady=(10, 10), sticky='w')

        # Force 120 FPS
        if Vars.Launcher.active_importer.get() in ['WWMI', 'SRMI', 'GIMI']:
            self.put(TweaksLabel(self)).grid(row=3, column=0, padx=(20, 10), pady=(10, 10), sticky='w')
            self.put(UnlockFPSCheckbox(self)).grid(row=3, column=1, padx=(10, 10), pady=(10, 10), sticky='w')
            # Window mode for GI FPS Unlocker
            if Vars.Launcher.active_importer.get() == 'GIMI':
                self.put(UnlockFPSWindowOptionMenu(self)).grid(row=3, column=1, padx=(150, 10), pady=(10, 10), sticky='w', columnspan=3)
                self.put(EnableHDR(self)).grid(row=3, column=1, padx=(330, 10), pady=(10, 10), sticky='w', columnspan=3)
                self.put(DisableDCR(self)).grid(row=3, column=1, padx=(460, 10), pady=(10, 10), sticky='w', columnspan=3)
            #  Performance Tweaks
            if Vars.Launcher.active_importer.get() == 'WWMI':
                self.put(ApplyTweaksCheckbox(self)).grid(row=3, column=2, padx=(20, 10), pady=(10, 10), sticky='w')
                self.put(OpenEngineIniButton(self)).grid(row=3, column=3, padx=(10, 20), pady=(10, 10), sticky='e')

        # Auto close
        self.put(LauncherLabel(self)).grid(row=4, column=0, padx=(20, 10), pady=(10, 10), sticky='w')
        self.put(AutoCloseCheckbox(self)).grid(row=4, column=1, padx=(10, 10), pady=(10, 10), sticky='w', columnspan=3)

        # Theme
        self.put(ThemeLabel(self)).grid(row=4, column=1, padx=(240, 10), pady=(10, 10), sticky='w', columnspan=3)
        self.put(LauncherThemeOptionMenu(self)).grid(row=4, column=1, padx=(310, 10), pady=(10, 10), sticky='w', columnspan=3)
        self.put(ApplyThemeButton(self)).grid(row=4, column=1, padx=(0, 20), pady=(10, 10), sticky='e', columnspan=3)


class GameFolderLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Game Folder:',
            font=('Roboto', 16, 'bold'),
            fg_color='transparent',
            master=master)


class GameFolderEntry(UIEntry):
    def __init__(self, master, error_label: UILabel):
        super().__init__(
            textvariable=Vars.Active.Importer.game_folder,
            width=200,
            height=36,
            font=('Arial', 14),
            master=master)
        self.error_label = error_label
        self.configure(validate='all', validatecommand=(master.register(self.validate_game_folder), '%P'))
        self.set_tooltip(self.get_tooltip)
        self.validate_game_folder(Vars.Active.Importer.game_folder.get())

    def validate_game_folder(self, game_folder):
        try:
            game_path = Events.Call(Events.ModelImporter.ValidateGameFolder(game_folder=game_folder))
        except Exception as e:
            self.error_label.configure(text=str(e))
            self.error_label.grid(row=0, column=1, padx=20, pady=(52, 0), sticky='ews', columnspan=2)
            return True
        self.error_label.grid_forget()
        return True

    def get_tooltip(self):
        msg = ''
        if Config.Launcher.active_importer == 'WWMI':
            msg = 'Path to folder with "Wuthering Waves.exe" and "Client" & "Engine" subfolders.\n'
            msg += 'Usually this folder is named "Wuthering Waves Game" and located inside WuWa installation folder.'
        if Config.Launcher.active_importer == 'ZZMI':
            msg = 'Path to folder with "ZenlessZoneZero.exe".\n'
        if Config.Launcher.active_importer == 'SRMI':
            msg = 'Path to folder with "StarRail.exe".\n'
            msg += 'Usually this folder is named "Games" and located inside "DATA" folder of HSR installation folder.'
        if Config.Launcher.active_importer == 'GIMI':
            msg = 'Path to folder with "GenshinImpact.exe" or "YuanShen.exe" (CN).\n'
            msg += 'Usually this folder is named "Genshin Impact Game" and located inside "DATA" folder of GI installation folder.'
        return msg.strip()


class GameFolderErrorLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Failed to detect Game Folder!',
            font=('Roboto', 16, 'bold'),
            text_color='red',
            fg_color='transparent',
            master=master)


class ChangeGameFolderButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text='Change',
            command=self.change_game_folder,
            width=70,
            height=36,
            font=('Roboto', 14),
            fg_color='#eeeeee',
            text_color='#000000',
            hover_color='#ffffff',
            border_width=1,
            master=master)

    def change_game_folder(self):
        game_folder = filedialog.askdirectory(initialdir=Vars.Active.Importer.game_folder.get())
        if game_folder == '':
            return
        Vars.Active.Importer.game_folder.set(game_folder)


class ProcessPriorityLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Process Priority:',
            font=('Roboto', 16, 'bold'),
            fg_color='transparent',
            master=master)


class ProcessPriorityOptionMenu(UIOptionMenu):
    def __init__(self, master):
        super().__init__(
            values=['Low', 'Below Normal', 'Normal', 'Above Normal', 'High', 'Realtime'],
            variable=Vars.Active.Importer.process_priority,
            width=140,
            height=36,
            font=('Arial', 14),
            dropdown_font=('Arial', 14),
            master=master)
        self.set_tooltip('Set process priority for the game exe.')


class LaunchOptionsLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Launch Options:',
            font=('Roboto', 16, 'bold'),
            fg_color='transparent',
            master=master)


class LaunchOptionsEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.launch_options,
            width=100,
            height=36,
            font=('Arial', 14),
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        msg = 'Command line arguments aka Launch Options to start game exe with.\n'
        if Config.Launcher.active_importer == 'WWMI':
            msg += '* Disable intro: -SkipSplash'
        return msg.strip()


class OpenEngineIniButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text='Open Engine.ini',
            command=self.open_engine_ini,
            width=120,
            height=36,
            font=('Roboto', 14),
            fg_color='#eeeeee',
            text_color='#000000',
            hover_color='#ffffff',
            border_width=1,
            master=master)
        self.set_tooltip(f'Open Engine.ini in default text editor file for manual tweaking.')

    def open_engine_ini(self):
        game_folder_path = Path(Vars.Active.Importer.game_folder.get())
        if 'Wuthering Waves Game' not in str(game_folder_path):
            game_folder_path = game_folder_path / 'Wuthering Waves Game'
        if not game_folder_path.is_dir():
            raise ValueError(f'Game folder does not exist: "{game_folder_path}"!')
        engine_ini = game_folder_path / 'Client' / 'Saved' / 'Config' / 'WindowsNoEditor' / 'Engine.ini'
        if engine_ini.is_file():
            subprocess.Popen([f'{str(engine_ini)}'], shell=True)
        else:
            raise ValueError(f'File does not exist: "{engine_ini}"!')


class TweaksLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Tweaks:',
            font=('Roboto', 16, 'bold'),
            fg_color='transparent',
            master=master)


class UnlockFPSCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Force 120 FPS',
            variable=Vars.Active.Importer.unlock_fps,
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        msg = ''
        if Config.Launcher.active_importer == 'WWMI':
            msg = 'This option allows to set FPS limit to 120 even on not officially supported devices.\n'
            msg += '* Enabled: Sets KeyCustomFrameRate to 120 in LocalStorage.db on game start.\n'
            msg += '* Disabled: Has no effect on FPS settings, use in-game settings to undo already forced 120 FPS.'
        if Config.Launcher.active_importer == 'SRMI':
            msg = 'This option allows to set FPS limit to 120.\n'
            msg += '* Enabled: Updates Graphics Settings Windows Registry key with 120 FPS value on game start.\n'
            msg += '* Disabled: Has no effect on FPS settings, use in-game settings to undo already forced 120 FPS.\n'
            msg += 'Note: Edits "FPS" value in "HKEY_CURRENT_USER\SOFTWARE\Cognosphere\Star Rail\GraphicsSettings_Model_h2986158309".'
        if Config.Launcher.active_importer == 'GIMI':
            msg = 'This option allows to force 120 FPS mode.\n'
            msg += '* Enabled: Launch game via "unlockfps_nc.exe" and let it run in background to continuously apply FPS limit tweak.\n'
            msg += '* Disabled: Launch game via original "GenshinImpact.exe" or "YuanShen.exe" (CN), has no effect on FPS.\n'
            msg += 'Hint: If FPS Unlocker package is outdated, you can manually update "unlockfps_nc.exe" from original repository.\n'
            msg += '* Local Path: Resources/Packages/GI-FPS-Unlocker/unlockfps_nc.exe\n'
            msg += '* Original Repository: https://github.com/34736384/genshin-fps-unlock'
        return msg.strip()


class UnlockFPSWindowOptionMenu(UIOptionMenu):
    def __init__(self, master):
        super().__init__(
            values=['Windowed', 'Borderless', 'Fullscreen', 'Exclusive Fullscreen'],
            variable=Vars.Active.Importer.window_mode,
            width=140,
            height=36,
            font=('Arial', 14),
            dropdown_font=('Arial', 14),
            master=master)
        self.set_tooltip('Game window mode when started with FPS Unlocker.')
        self.trace_write(Vars.Active.Importer.unlock_fps, self.handle_write_unlock_fps)

    def handle_write_unlock_fps(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')


class ApplyTweaksCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Apply Performance Tweaks',
            variable=Vars.Active.Importer.apply_perf_tweaks,
            master=master)
        self.set_tooltip(
            'Enabled: Set of performance-tweaking settings will be added to [SystemSettings] section of Engine.ini on game start.\n'
            "Disabled: Settings will no longer be set on game start, but existing ones won't be removed from Engine.ini.\n\n"
            'List of tweeaks:\n'
            '* r.Streaming.HLODStrategy = 2\n'
            '* r.Streaming.LimitPoolSizeToVRAM = 1\n'
            '* r.Streaming.PoolSizeForMeshes = -1\n'
            '* r.XGEShaderCompile = 0\n'
            '* FX.BatchAsync = 1\n'
            '* FX.EarlyScheduleAsync = 1\n'
            '* fx.Niagara.ForceAutoPooling = 1\n'
            '* wp.Runtime.KuroRuntimeStreamingRangeOverallScale = 0.5\n'
            '* tick.AllowAsyncTickCleanup = 1\n'
            '* tick.AllowAsyncTickDispatch = 1'
        )


class EnableHDR(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Enable HDR',
            variable=Vars.Active.Importer.enable_hdr,
            master=master)
        self.set_tooltip(
            'Warning! Your monitor must support HDR and `Use HDR` must be enabled in Windows Display settings!\n'
            'Enabled: Turn HDR On. Launcher will create HDR registry record each time before the game launch.\n'
            'Disabled: Turn HDR Off. No extra action required, game auto-removes HDR registry record on launch.')


class DisableDCR(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Disable DCR',
            variable=Vars.Active.Importer.disable_dcr,
            master=master)
        self.set_tooltip(
            'Warning! GIMI model mods are *NOT* compatible with Dynamic Character Resolution Graphics Setting!\n'
            'Enabled: Turn Off DCR, allowing all kinds of character mods to work.\n'
            'Disabled: DCR setting will not be affected (use in-game Graphics Settings to enable it again).')


class LauncherLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Launcher:',
            font=('Roboto', 16, 'bold'),
            fg_color='transparent',
            master=master)


class AutoCloseCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Close After Game Start',
            variable=Vars.Launcher.auto_close,
            master=master)
        self.set_tooltip(
            'Enabled: Launcher will close itself once the game has started and 3dmigoto injection has been confirmed.\n'
            'Disabled: Launcher will keep itself running.')


class ThemeLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Theme:',
            font=('Roboto', 16, 'bold'),
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
            text='Apply',
            command=self.apply_theme,
            width=100,
            height=36,
            font=('Roboto', 14),
            fg_color='#eeeeee',
            text_color='#000000',
            hover_color='#ffffff',
            border_width=1,
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
