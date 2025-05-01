import subprocess
import webbrowser

from pathlib import Path
from customtkinter import filedialog, ThemeManager
from textwrap import dedent

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
        self.put(GameFolderLabel(self)).grid(row=0, column=0, padx=(20, 0), pady=(0, 30), sticky='w')
        self.put(GameFolderFrame(self)).grid(row=0, column=1, padx=(0, 20), pady=(0, 30), sticky='new', columnspan=3)

        # Launch Options
        self.put(LaunchOptionsLabel(self)).grid(row=1, column=0, padx=(20, 0), pady=(0, 30), sticky='w')
        self.put(LaunchOptionsFrame(self)).grid(row=1, column=1, padx=(0, 20), pady=(0, 30), sticky='ew', columnspan=3)

        # Process Priority
        self.put(ProcessPriorityLabel(self)).grid(row=2, column=0, padx=20, pady=(0, 30), sticky='w')
        self.put(ProcessPriorityOptionMenu(self)).grid(row=2, column=1, padx=(0, 10), pady=(0, 30), sticky='w')

        # Auto Config
        if Vars.Launcher.active_importer.get() != 'SRMI':
            self.put(AutoConfigLabel(self)).grid(row=3, column=0, padx=(20, 0), pady=(0, 30), sticky='w')
            self.put(AutoConfigFrame(self)).grid(row=3, column=1, padx=(0, 20), pady=(0, 30), sticky='w', columnspan=3)

        if Vars.Launcher.active_importer.get() != 'ZZMI':
            
            # Tweaks
            self.put(TweaksLabel(self)).grid(row=4, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
    
            tweaks_frame = UIFrame(self, fg_color=master._fg_color)
            tweaks_frame.grid(row=4, column=1, padx=(0, 0), pady=(0, 30), sticky='we', columnspan=3)
            tweaks_frame.put(UnlockFPSCheckbox(tweaks_frame)).grid(row=0, column=0, padx=(0, 10), pady=(0, 0), sticky='w')
    
            # Window mode for GI FPS Unlocker
            if Vars.Launcher.active_importer.get() == 'GIMI':
                tweaks_frame.put(UnlockFPSWindowOptionMenu(tweaks_frame)).grid(row=0, column=1, padx=(20, 10), pady=(0, 0), sticky='w')
                tweaks_frame.put(EnableHDR(tweaks_frame)).grid(row=0, column=2, padx=(60, 10), pady=(0, 0), sticky='w')
    
            #  Performance Tweaks
            if Vars.Launcher.active_importer.get() == 'WWMI':
                tweaks_frame.put(ApplyTweaksCheckbox(tweaks_frame)).grid(row=0, column=1, padx=(20, 10), pady=(0, 0), sticky='w')
                tweaks_frame.put(OpenEngineIniButton(tweaks_frame)).grid(row=0, column=2, padx=(10, 20), pady=(0, 0), sticky='e')


class GameFolderFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            border_color = ThemeManager.theme["CTkEntry"].get("border_color", None),
            border_width = ThemeManager.theme["CTkEntry"].get("border_width", None),
            fg_color = ThemeManager.theme["CTkEntry"].get("fg_color", None),
            master=master)

        self.grid_columnconfigure(0, weight=100)

        game_folder_error = master.put(GameFolderErrorLabel(master))

        self.put(GameFolderEntry(self, game_folder_error)).grid(row=0, column=0, padx=(4, 0), pady=(2, 0), sticky='new')
        self.put(ChangeGameFolderButton(self)).grid(row=0, column=1, padx=(0, 4), pady=(2, 2), sticky='ne')


class LaunchOptionsFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            border_color = ThemeManager.theme["CTkEntry"].get("border_color", None),
            border_width = ThemeManager.theme["CTkEntry"].get("border_width", None),
            fg_color = ThemeManager.theme["CTkEntry"].get("fg_color", None),
            master=master)

        self.grid_columnconfigure(0, weight=100)

        self.put(LaunchOptionsEntry(self)).grid(row=0, column=0, padx=(4, 0), pady=(2, 2), sticky='ew')
        self.put(LaunchOptionsButton(self)).grid(row=0, column=1, padx=(0, 4), pady=(2, 2), sticky='e')


class AutoConfigFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            fg_color = 'transparent',
            master=master)

        self.grid_columnconfigure(0, weight=100)

        self.put(ConfigureGameCheckbox(self)).grid(row=0, column=0, padx=(0, 10), pady=(0, 0), sticky='w')
        
        if Vars.Launcher.active_importer.get() == 'WWMI':
            self.put(DisableWoundedEffectCheckbox(self)).grid(row=0, column=1, padx=(10, 20), pady=(0, 0), sticky='w')


class GameFolderLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Game Folder:',
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class GameFolderEntry(UIEntry):
    def __init__(self, master, error_label: UILabel):
        super().__init__(
            textvariable=Vars.Active.Importer.game_folder,
            width=200,
            height=32,
            border_width=0,
            font=('Arial', 14),
            master=master)
        self.normal_border_color = self._border_color
        self.error_label = error_label
        self.configure(validate='all', validatecommand=(master.register(self.validate_game_folder), '%P'))
        self.set_tooltip(self.get_tooltip)
        self.validate_game_folder(Vars.Active.Importer.game_folder.get())

    def validate_game_folder(self, game_folder):
        try:
            game_path = Events.Call(Events.ModelImporter.ValidateGameFolder(game_folder=game_folder.strip()))
        except Exception as e:
            self.error_label.configure(text=str(e))
            self.error_label.grid(row=0, column=1, padx=(0, 15), pady=(36, 0), sticky='nwe')
            self.master.configure(border_color='#db3434')
            return True
        self.master.configure(border_color=self.normal_border_color)
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
            font=('Microsoft YaHei', 14, 'bold'),
            text_color='#ff3636',
            fg_color='transparent',
            master=master)


class ChangeGameFolderButton(UIButton):
    def __init__(self, master):
        fg_color = ThemeManager.theme["CTkEntry"].get("fg_color", None)
        super().__init__(
            text='Browse...',
            command=self.change_game_folder,
            auto_width=True,
            padx=6,
            height=32,
            border_width=0,
            font=('Roboto', 14),
            fg_color=fg_color,
            hover_color=fg_color,
            text_color=["#000000", "#aaaaaa"],
            text_color_hovered=["#000000", "#ffffff"],
            master=master)

    def change_game_folder(self):
        game_folder = filedialog.askdirectory(initialdir=Vars.Active.Importer.game_folder.get())
        if game_folder == '':
            return
        Vars.Active.Importer.game_folder.set(game_folder)


class LaunchOptionsButton(UIButton):
    def __init__(self, master):
        fg_color = ThemeManager.theme['CTkEntry'].get('fg_color', None)

        super().__init__(
            text='About...',
            command=self.open_docs,
            auto_width=True,
            padx=6,
            height=32,
            border_width=0,
            font=('Roboto', 14),
            fg_color=fg_color,
            hover_color=fg_color,
            text_color=['#000000', '#aaaaaa'],
            text_color_hovered=['#000000', '#ffffff'],
            master=master)

        self.set_tooltip(self.get_tooltip)

    def open_docs(self):
        if Config.Launcher.active_importer == 'WWMI':
            webbrowser.open('https://dev.epicgames.com/documentation/en-us/unreal-engine/command-line-arguments?application_version=4.27')
        elif Config.Launcher.active_importer in ['GIMI', 'SRMI', 'ZZMI']:
            webbrowser.open('https://docs.unity3d.com/Manual/PlayerCommandLineArguments.html')

    def get_tooltip(self):
        if Config.Launcher.active_importer == 'WWMI':
            engine = 'UE4'
        elif Config.Launcher.active_importer in ['GIMI', 'SRMI', 'ZZMI']:
            engine = 'Unity'
        else:
            raise ValueError(f'Game engine is unknown!')

        return (
            f'Open {engine} command line arguments documentation webpage.\n'
            f'Note: Game engine is customized by devs and some args may not work.')


class LaunchOptionsLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Launch Options:',
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class LaunchOptionsEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.launch_options,
            width=100,
            height=32,
            border_width=0,
            font=('Arial', 14),
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        msg = 'Command line arguments aka Launch Options to start game exe with.\n'
        if Config.Launcher.active_importer == 'WWMI':
            msg += '* Disable intro: -SkipSplash'
        return msg.strip()


class ProcessPriorityLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Process Priority:',
            font=('Microsoft YaHei', 14, 'bold'),
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


class AutoConfigLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text='Auto Config:',
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class ConfigureGameCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Configure Game Settings',
            variable=Vars.Active.Importer.configure_game,
            master=master)

        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        msg = ''
        if Config.Launcher.active_importer == 'GIMI':
            msg = dedent("""
                **Enabled**: Ensure GIMI-compatible in-game **Graphics Settings** before game start:

                - `Dynamic Character Resolution: Off`

                **Disabled**: In-game settings will not be affected.

                <font color="red">⚠ Mods will not work with wrong settings! ⚠</font>
            """)
        if Config.Launcher.active_importer == 'WWMI':
            msg = dedent("""
                **Enabled**: Ensure WWMI-compatible in-game **Graphics Settings** before game start:

                - `Graphics Quality: Quality`

                **Disabled**: In-game settings will not be affected.

                <font color="red">⚠ Mods will not work with wrong settings! ⚠</font>
            """)
        if Config.Launcher.active_importer == 'ZZMI':
            msg = dedent("""
                **Enabled**: Ensure ZZMI-compatible in-game **Graphics Settings** before game start:

                - `Character Quality: High`
                - `High-Precision Character Animation: Disabled`

                **Disabled**: In-game settings will not be affected.

                <font color="red">⚠ Mods will not work with wrong settings! ⚠</font>
            """)
        return msg.strip()


class OpenEngineIniButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text='🔍 Open Engine.ini',
            command=self.open_engine_ini,
            width=140,
            height=36,
            font=('Roboto', 14),
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
            font=('Microsoft YaHei', 14, 'bold'),
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
            msg += 'Please do note that with some hardware game refuses to go 120 FPS even with this tweak.\n'
            msg += '**Enabled**: Sets `CustomFrameRate` to `120` in `LocalStorage.db` on game start.\n'
            msg += '**Disabled**: Has no effect on FPS settings, use in-game settings to undo already forced 120 FPS.'
        if Config.Launcher.active_importer == 'SRMI':
            msg = 'This option allows to set FPS limit to 120.\n'
            msg += '**Enabled**: Updates Graphics Settings Windows Registry key with 120 FPS value on game start.\n'
            msg += '**Disabled**: Has no effect on FPS settings, use in-game settings to undo already forced 120 FPS.\n'
            msg += '**Warning!** Tweak is supported only for the Global HSR client and will not work for CN.\n'
            msg += '*Note: Edits `FPS` value in `HKEY_CURRENT_USER/SOFTWARE/Cognosphere/Star Rail/GraphicsSettings_Model_h2986158309`.*'
        elif Config.Launcher.active_importer == 'GIMI':
            msg = 'This option allows to force 120 FPS mode.\n'
            msg += '**Enabled**: Launch game via `unlockfps_nc.exe` and let it run in background to keep FPS tweak applied.\n'
            msg += '**Disabled**: Launch game via original `.exe` file, has no effect on FPS.\n'
            msg += '*Hint: If FPS Unlocker package is outdated, you can manually update "unlockfps_nc.exe" from original repository.*\n'
            msg += '*Local Path*: `Resources/Packages/GI-FPS-Unlocker/unlockfps_nc.exe`\n'
            msg += '*Original Repository*: `https://github.com/34736384/genshin-fps-unlock`'
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
            '**Enabled**: Add list of performance tweaks to `[SystemSettings]` section of `Engine.ini` on game start.\n'
            "**Disabled**: Do not add tweaks to `Engine.ini`. Already added ones will have to be removed manually.\n\n"
            'List of tweaks:\n'
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
            '**Warning**! Your monitor must support HDR and `Use HDR` must be enabled in Windows Display settings!\n'
            '**Enabled**: Turn HDR On. Creates HDR registry record each time before the game launch.\n'
            '**Disabled**: Turn HDR Off. No extra action required, game auto-removes HDR registry record on launch.')


class DisableWoundedEffectCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='Disable Wounded Effect',
            variable=Vars.Active.Importer.disable_wounded_fx,
            master=master)
        self.set_tooltip(
            'Most mods do not support this effect, so textures usually break after few hits taken.\n'
            '**Enabled**: Turn the effect `Off`. Ensures proper rendering of modded textures.\n'
            "**Disabled**: Turn the effect `On`. Select this if you use `Injured Effect Remover` tool."
        )

        self.trace_write(Vars.Active.Importer.configure_game, self.handle_write_configure_game)

    def handle_write_configure_game(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')
