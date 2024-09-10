import subprocess
from pathlib import Path
from customtkinter import filedialog

import core.event_manager as Events
import core.config_manager as Config
import gui.vars as Vars

from gui.classes.containers import UIFrame
from gui.classes.widgets import UILabel, UIButton, UIEntry, UICheckbox


class GeneralSettingsFrame(UIFrame):
    def __init__(self, master):
        super().__init__(master)

        self.grid_columnconfigure((0, 2), weight=1)
        self.grid_columnconfigure(1, weight=100)
        self.grid_rowconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(5, weight=100)

        # Game Folder
        self.put(GameFolderLabel(self)).grid(row=0, column=0, padx=(20, 0), pady=(20, 20), sticky='wn')
        game_folder_error = self.put(GameFolderErrorLabel(self))
        self.put(GameFolderEntry(self, game_folder_error)).grid(row=0, column=1, padx=20, pady=(20, 20), sticky='ewn')
        self.put(ChangeGameFolderButton(self)).grid(row=0, column=2, padx=(0, 20), pady=(20, 20), sticky='n')

        # Launch Options
        self.put(LaunchOptionsLabel(self)).grid(row=1, column=0, padx=20, pady=(20, 20), sticky='w')
        self.put(LaunchOptionsEntry(self)).grid(row=1, column=1, padx=20, pady=(20, 20), sticky='ew', columnspan=2)

        #  Extra
        self.put(AutoCloseCheckbox(self)).grid(row=2, column=1, padx=20, pady=(10, 20), sticky='w', columnspan=2)
        if Vars.Launcher.active_importer.get() == 'WWMI':
            self.put(ApplyTweaksCheckbox(self)).grid(row=3, column=1, padx=20, pady=(10, 20), sticky='w', columnspan=2)
            self.put(OpenEngineIniButton(self)).grid(row=3, column=1, padx=(260, 0), pady=(10, 20), sticky='w', columnspan=2)
            self.put(UnlockFPSCheckbox(self)).grid(row=4, column=1, padx=20, pady=(10, 20), sticky='w', columnspan=2)


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
            self.error_label.grid(row=0, column=1, padx=20, pady=(62, 0), sticky='ews')
            return True
        self.error_label.grid_forget()
        return True

    def get_tooltip(self):
        msg = ''
        if Config.Launcher.active_importer == 'WWMI':
            msg = 'Path to folder with "Client" and "Engine" subfolders and "ZenlessZoneZero.exe".\n'
            msg += 'Usually this folder is named "Wuthering Waves Game" and located inside WuWa installation folder.'
        if Config.Launcher.active_importer == 'ZZMI':
            msg = 'Path to folder with "ZenlessZoneZero.exe".'
        return msg.strip()


class GameFolderErrorLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Folder must contain Client and Engine folders!',
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


class AutoCloseCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Close Launcher When Game Starts',
            variable=Vars.Launcher.auto_close,
            master=master)
        self.set_tooltip(
            'Enabled: Launcher will close itself once the game has started and 3dmigoto injection has been confirmed.\n'
            'Disabled: Launcher will keep itself running.')


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


class UnlockFPSCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Force 120 FPS',
            variable=Vars.Active.Importer.unlock_fps,
            master=master)
        self.set_tooltip(
            'This option allows to set FPS limit to 120 even on not officially supported devices.\n'
            'Enabled: Sets KeyCustomFrameRate to 120 in LocalStorage.db on game start.\n'
            'Disabled: Has no effect on FPS settings, use in-game settings to undo already forced 120 FPS.')
