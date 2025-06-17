import subprocess
import webbrowser

from pathlib import Path
from customtkinter import filedialog, ThemeManager
from textwrap import dedent

import core.event_manager as Events
import core.config_manager as Config
import core.path_manager as Paths
import gui.vars as Vars
from core.locale_manager import T, L
from core.application import Application

from gui.classes.containers import UIFrame, UIScrollableFrame
from gui.classes.widgets import UILabel, UIButton, UIEntry, UICheckbox,  UIOptionMenu


class GeneralSettingsFrame(UIScrollableFrame):
    def __init__(self, master):
        super().__init__(master, height=360, corner_radius=0, border_width=0, hide_scrollbar=True)

        self.grid_columnconfigure((0, 2, 3), weight=1)
        self.grid_columnconfigure(1, weight=100)
        self.grid_rowconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(6, weight=100)

        # Call grid manager to workaround customtkinter bug that causes content to overlap with scrollbarAdd commentMore actions
        self.grid()

        # Game Folder
        self.put(GameFolderLabel(self)).grid(row=0, column=0, padx=(20, 0), pady=(0, 30), sticky='w')
        self.put(GameFolderFrame(self)).grid(row=0, column=1, padx=(0, 65), pady=(0, 30), sticky='new', columnspan=3)
        self.put(DetectGameFolderButton(self)).grid(row=0, column=1, padx=(0, 20), pady=(0, 30), sticky='e', columnspan=3)

        # Launch Options
        self.put(LaunchOptionsLabel(self)).grid(row=1, column=0, padx=(20, 0), pady=(0, 30), sticky='w')
        self.put(LaunchOptionsFrame(self)).grid(row=1, column=1, padx=(0, 20), pady=(0, 30), sticky='ew', columnspan=3)

        # Process Priority
        self.put(StartMethodLabel(self)).grid(row=2, column=0, padx=20, pady=(0, 30), sticky='w')
        self.put(ProcessOptionsFrame(self)).grid(row=2, column=1, padx=(0, 20), pady=(0, 30), sticky='w', columnspan=3)

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

        if Vars.Launcher.active_importer.get() == 'WWMI':
            self.put(EngineSettingsLabel(self)).grid(row=5, column=0, padx=20, pady=(0, 20), sticky='w')
            self.put(TextureStreamingFrame(self)).grid(row=5, column=1, padx=(0, 20), pady=(0, 20), sticky='w', columnspan=3)

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


class ProcessOptionsFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            fg_color = 'transparent',
            master=master)

        self.grid_columnconfigure(0, weight=100)

        self.put(StartMethodOptionMenu(self)).grid(row=0, column=0, padx=(0, 10), pady=(0, 0), sticky='w')
        self.put(MigotoInitDelayLabel(self)).grid(row=0, column=1, padx=20, pady=(0, 0), sticky='w')
        self.put(MigotoInitDelayEntry(self)).grid(row=0, column=2, padx=(0, 10), pady=(0, 0), sticky='w')
        self.put(ProcessPriorityLabel(self)).grid(row=0, column=3, padx=20, pady=(0, 0), sticky='e')
        self.put(ProcessPriorityOptionMenu(self)).grid(row=0, column=4, padx=(0, 0), pady=(0, 0), sticky='e')


class AutoConfigFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            fg_color = 'transparent',
            master=master)

        self.grid_columnconfigure(0, weight=100)

        self.put(ConfigureGameCheckbox(self)).grid(row=0, column=0, padx=(0, 10), pady=(0, 0), sticky='w')
        
        if Vars.Launcher.active_importer.get() == 'WWMI':
            self.put(DisableWoundedEffectCheckbox(self)).grid(row=0, column=1, padx=(10, 20), pady=(0, 0), sticky='w')


class EngineSettingsLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_engine_settings_label', 'Engine Settings:')),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)

class TextureStreamingFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            fg_color='transparent',
            master=master)

        self.grid_columnconfigure(0, weight=100)

        self.put(TextureStreamingBoostLabel(self)).grid(row=0, column=0, padx=(0, 0), pady=(0, 0), sticky='w')
        self.put(TextureStreamingBoostEntry(self)).grid(row=0, column=1, padx=(10, 0), pady=(0, 0), sticky='w')
        self.grab(TextureStreamingBoostLabel).set_tooltip(self.grab(TextureStreamingBoostEntry))

        self.put(MeshLODDistanceLabel(self)).grid(row=0, column=2, padx=(30, 0), pady=(0, 0), sticky='w')
        self.put(MeshLODDistanceEntry(self)).grid(row=0, column=3, padx=(10, 0), pady=(0, 0), sticky='w')
        self.grab(MeshLODDistanceLabel).set_tooltip(self.grab(MeshLODDistanceEntry))

        self.put(TextureStreamingPoolSizeLabel(self)).grid(row=1, column=0, padx=(0, 0), pady=(15, 0), sticky='w')
        self.put(TextureStreamingPoolSizeEntry(self)).grid(row=1, column=1, padx=(10, 0), pady=(15, 0), sticky='w')
        self.grab(TextureStreamingPoolSizeLabel).set_tooltip(self.grab(TextureStreamingPoolSizeEntry))
        self.put(TextureStreamingLimitPoolToVramCheckbox(self)).grid(row=1, column=2, padx=(20, 0), pady=(15, 0), sticky='w', columnspan=2)


class GameFolderLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_game_folder_label', 'Game Folder:')),
            font=('Microsoft YaHei', 14),
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
            msg = str(L('general_settings_game_folder_tooltip_wwmi', 'Path to folder with "Wuthering Waves.exe" and "Client" & "Engine" subfolders.\nUsually this folder is named "Wuthering Waves Game" and located inside WuWa installation folder.'))
        if Config.Launcher.active_importer == 'ZZMI':
            msg = str(L('general_settings_game_folder_tooltip_zzmi', 'Path to folder with "ZenlessZoneZero.exe".\n'))
        if Config.Launcher.active_importer == 'SRMI':
            msg = str(L('general_settings_game_folder_tooltip_srmi', 'Path to folder with "StarRail.exe".\nUsually this folder is named "Games" and located inside "DATA" folder of HSR installation folder.'))
        if Config.Launcher.active_importer == 'GIMI':
            msg = str(L('general_settings_game_folder_tooltip_gimi', 'Path to folder with "GenshinImpact.exe" or "YuanShen.exe" (CN).\nUsually this folder is named "Genshin Impact Game" and located inside "DATA" folder of GI installation folder.'))
        return msg.strip()


class GameFolderErrorLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_game_folder_error', 'Failed to detect Game Folder!')),
            font=('Microsoft YaHei', 14, 'bold'),
            text_color='#ff3636',
            fg_color='transparent',
            master=master)

    def _show(self):
        if self.winfo_manager():
            super()._show()


class ChangeGameFolderButton(UIButton):
    def __init__(self, master):
        fg_color = ThemeManager.theme["CTkEntry"].get("fg_color", None)
        super().__init__(
            text=str(L('general_settings_browse_button', 'Browse...')),
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


class DetectGameFolderButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text='⟳',
            command=self.detect_game_folder,
            width = 36,
            height=36,
            font=('Asap', 18),
            master=master)

        self.set_tooltip(str(L('general_settings_detect_game_folder_tooltip', 'Try to automatically detect existing installation folders.')))

    def detect_game_folder(self):
        try:
            game_folder, game_path, game_exe_path = Events.Call(Events.ModelImporter.DetectGameFolder())
            Vars.Active.Importer.game_folder.set(str(game_path))
            Config.Active.Importer.game_folder = str(game_path)
        except:
            pass


class LaunchOptionsButton(UIButton):
    def __init__(self, master):
        fg_color = ThemeManager.theme['CTkEntry'].get('fg_color', None)

        super().__init__(
            text=str(L('general_settings_launch_options_about_button', 'About...')),
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

        return str(L('general_settings_launch_options_about_tooltip', 'Open {engine} command line arguments documentation webpage.\nNote: Game engine is customized by devs and some args may not work.').format(engine=engine))


class LaunchOptionsLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_launch_options_label', 'Launch Options:')),
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
        msg = str(L('general_settings_launch_options_tooltip_base', 'Command line arguments aka Launch Options to start game exe with.\n'))
        if Config.Launcher.active_importer == 'WWMI':
            msg += str(L('general_settings_launch_options_tooltip_wwmi', '* Disable intro: -SkipSplash'))
        return msg.strip()


class StartMethodLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_start_method_label', 'Start Method:')),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class StartMethodOptionMenu(UIOptionMenu):
    def __init__(self, master):
        super().__init__(
            values=['Native', 'Shell', 'Manual'],
            variable=Vars.Active.Importer.process_start_method,
            width=140,
            height=36,
            font=('Arial', 14),
            dropdown_font=('Arial', 14),
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        return dedent(f"""
            **Native**: Create the game process directly. Usually it's the most reliable way.
            **Shell**: Start the game process via system console. Worth to try if you have some issues with Native.
            **Manual**: Skip launching the game on **Start** button press. Wait for user to launch it manually 
     ({Config.Launcher.start_timeout}s timeout).   
             """)

class MigotoInitDelayLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_xxmi_delay_label', 'XXMI Delay:')),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class MigotoInitDelayEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.xxmi_dll_init_delay,
            input_filter='INT',
            width=50,
            height=36,
            font=('Arial', 14),
            master=master)

        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        msg = str(T('general_settings_xxmi_delay_tooltip_base', 
                   'Delay in milliseconds for how long injected XXMI DLL (3dmigoto) must wait before initialization.\n'))
        if Config.Launcher.active_importer == 'WWMI':
            msg += str(T('general_settings_xxmi_delay_tooltip_wwmi', 
                        '<font color="red">⚠ Wuthering Waves crashes on launch with wrong delay! ⚠</font>\n'
                        '<font color="#8B8000">⚠ If default value fails, try to increase or decrease it until WuWa stops crashing. ⚠</font>\n'
                        '## Known values for Wuthering Waves 2.4:\n'
                        '- **500**: Default, works for most users.\n'
                        '- **150**: Minimal known value to work along with ReShade.\n'
                        '- **50**: Minimal known value to work.\n'
                        '- **1000+**: Some users need really huge delays.'))
        else:
            msg += str(T('general_settings_xxmi_delay_tooltip_general', 
                        'If game crashes with no mods, try to increase it. Start with steps of 50 and increase them as you go.'))

        return msg


class ProcessPriorityLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_process_priority_label', 'Process Priority:')),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)

        self.trace_write(Vars.Active.Importer.process_start_method, self.handle_write_process_start_method)

    def handle_write_process_start_method(self, var, val):
        if val == 'Native':
            self.configure(state='normal')
        else:
            self.configure(state='disabled')


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
        self.set_tooltip(str(L('general_settings_process_priority_tooltip',
            'Set process priority for the game exe.\n'
            '**Warning!** **Shell** start method does not support process priority!')))

        self.trace_write(Vars.Active.Importer.process_start_method, self.handle_write_process_start_method)

    def handle_write_process_start_method(self, var, val):
        if val == 'Native':
            self.configure(state='normal')
        else:
            self.configure(state='disabled')


class AutoConfigLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_auto_config_label', 'Auto Config:')),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class ConfigureGameCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_configure_game_checkbox', 'Configure Game Settings')),
            variable=Vars.Active.Importer.configure_game,
            master=master)

        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        msg = ''
        if Config.Launcher.active_importer == 'GIMI':
            msg = str(L('general_settings_configure_game_tooltip_gimi', 
                '**Enabled**: Ensure GIMI-compatible in-game **Graphics Settings** before game start:\n\n'
                '- `Dynamic Character Resolution: Off`\n\n'
                '**Disabled**: In-game settings will not be affected.\n\n'
                '<font color="red">⚠ Mods will not work with wrong settings! ⚠</font>'))
        if Config.Launcher.active_importer == 'WWMI':
            msg = str(L('general_settings_configure_game_tooltip_wwmi',
                '**Enabled**: Ensure WWMI-compatible in-game **Graphics Settings** before game start:\n\n'
                '- `Graphics Quality: Quality`\n\n'
                '**Disabled**: In-game settings will not be affected.\n\n'
                '<font color="red">⚠ Mods will not work with wrong settings! ⚠</font>'))
        if Config.Launcher.active_importer == 'ZZMI':
            msg = str(L('general_settings_configure_game_tooltip_zzmi',
                '**Enabled**: Ensure ZZMI-compatible in-game **Graphics Settings** before game start:\n\n'
                '- `Character Quality: High`\n'
                '- `High-Precision Character Animation: Disabled`\n\n'
                '**Disabled**: In-game settings will not be affected.\n\n'
                '<font color="red">⚠ Mods will not work with wrong settings! ⚠</font>'))
        return msg.strip()

class DisableWoundedEffectCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_disable_wounded_effect_checkbox', 'Disable Wounded Effect')),
            variable=Vars.Active.Importer.disable_wounded_fx,
            master=master)
        self.set_tooltip(str(L('general_settings_disable_wounded_effect_tooltip',
            'Most mods do not support this effect, so textures usually break after few hits taken.\n'
            '**Enabled**: Turn the effect `Off`. Ensures proper rendering of modded textures.\n'
            "**Disabled**: Turn the effect `On`. Select this if you use `Injured Effect Remover` tool."
        )))

        self.trace_write(Vars.Active.Importer.configure_game, self.handle_write_configure_game)

    def handle_write_configure_game(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')

class TextureStreamingBoostLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_texture_boost_label', 'Texture Boost:')),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class TextureStreamingBoostEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.texture_streaming_boost,
            input_filter='FLOAT',
            width=60,
            height=36,
            font=('Arial', 14),
            master=master)

        self.set_tooltip(str(L('general_settings_texture_boost_tooltip', dedent("""
            ## Controls how aggressively higher resolution textures are pushed to VRAM:

            * Start tuning around **30.0** **(default)** for **mid-range PC**.
                ✅ For slow systems tuning can significantly reduce modded textures loading delay.

            * Start tuning around **2.5** for **high end PC**.
                ✅ For fast systems tuning can completely eliminate modded textures loading delay.

            * Set to **0** to disable the boost and stick to the default game engine behavior.

            ⚠️ With low values, try decimals (e.g. `1.1` or `2.5`).

            *Applied to ConsoleVariables → r.Streaming.Boost value in Engine.ini*
        """))))


class TextureStreamingPoolSizeLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_texture_streaming_pool_size_label', 'Texture Pool Size:')),
            font=('Microsoft YaHei', 14),
            fg_color='transparent',
            master=master)


class TextureStreamingPoolSizeEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.texture_streaming_pool_size,
            input_filter='INT',
            width=60,
            height=36,
            font=('Arial', 14),
            master=master)

        self.set_tooltip(str(L('general_settings_texture_streaming_pool_size_tooltip', dedent("""
            ## Controls how much VRAM the game can use for textures:

            * Set to **0** **(default)** for **automatic control** (based on available VRAM).
                ✅ Large enough pool eliminates modded textures loading delay after first load.

            * Set to specific value (e.g. 4096) for precise VRAM management.

            *Applied to ConsoleVariables → r.Streaming.PoolSize value in Engine.ini*
        """))))


class TextureStreamingLimitPoolToVramCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_texture_streaming_limit_pool_checkbox', 'Limit Pool Size To VRAM')),
            variable=Vars.Active.Importer.texture_streaming_limit_to_vram,
            master=master)
        self.set_tooltip(str(L('general_settings_texture_streaming_limit_pool_tooltip', dedent("""
            ## Sets the upper limit for how much VRAM the game can use for textures:

            * **Enabled** **(default)** – Limits texture pool size based on your GPU's available VRAM.
                ✅ Helps prevent crashes or stuttering on low VRAM systems.
                ⚠️ May reduce texture quality or cause pop-ins if too restrictive on high-end GPUs.

            * **Disabled** – Unlocks maximum texture pool size, even if it exceeds your GPU's safe limits.
                ✅ Can improve texture quality and reduce pop-ins on powerful systems.
                ⚠️ Risk of performance drops, stutters, or crashes if VRAM runs out.

            *Applied to ConsoleVariables → r.Streaming.LimitPoolSizeToVRAM value in Engine.ini*
        """))))


class MeshLODDistanceLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_mesh_lod_distance_label', 'Mesh LOD Distance:')),
            font=('Microsoft YaHei', 14),
            fg_color='transparent',
            master=master)


class MeshLODDistanceEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.mesh_lod_distance_scale,
            input_filter='INT',
            width=40,
            height=36,
            font=('Arial', 14),
            master=master)

        self.set_tooltip(str(L('general_settings_mesh_lod_distance_tooltip', dedent("""
            ## Controls how far game replaces full animated meshes with simplified LoDs:

            * Set to **24** **(default)** to force full models as far as the game loads animated objects.
                ✅ With this value mods are applied as far as you can see.
                ⚠️ Risk of performance drops for low-end GPUs.

            * Set to lower value (e.g. `15`) for better performance.
                ✅ Reduce FPS cost by allowing the game to use LoD meshes for distant animated objects.
                ⚠️ LoDs may look wrong due to modded textures being applied to original LoD meshes.

            *Applied to ConsoleVariables → r.Kuro.SkeletalMesh.LODDistanceScale value in Engine.ini*
        """))))


class OpenEngineIniButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_open_engine_ini_button', '🔍 Open Engine.ini')),
            command=self.open_engine_ini,
            width=140,
            height=36,
            font=('Roboto', 14),
            master=master)
        self.set_tooltip(str(L('general_settings_open_engine_ini_tooltip', 'Open Engine.ini in default text editor file for manual tweaking.')))

    def open_engine_ini(self):
        game_folder = Events.Call(Events.ModelImporter.ValidateGameFolder(Config.Active.Importer.game_folder))
        engine_ini = game_folder / 'Client' / 'Saved' / 'Config' / 'WindowsNoEditor' / 'Engine.ini'
        if engine_ini.is_file():
            subprocess.Popen([f'{str(engine_ini)}'], shell=True)
        else:
            raise ValueError(str(L('general_settings_engine_ini_not_found', 'File does not exist: "{}"!')).format(engine_ini))


class TweaksLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_tweaks_label', 'Tweaks:')),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class UnlockFPSCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_unlock_fps_checkbox', 'Force 120 FPS')),
            variable=Vars.Active.Importer.unlock_fps,
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        msg = ''
        if Config.Launcher.active_importer == 'WWMI':
            msg = str(L('general_settings_unlock_fps_tooltip_wwmi',
                'This option allows to set FPS limit to 120 even on not officially supported devices.\n'
                'Please do note that with some hardware game refuses to go 120 FPS even with this tweak.\n'
                '**Enabled**: Sets `CustomFrameRate` to `120` in `LocalStorage.db` on game start.\n'
                '**Disabled**: Has no effect on FPS settings, use in-game settings to undo already forced 120 FPS.'))
        if Config.Launcher.active_importer == 'SRMI':
            msg = str(L('general_settings_unlock_fps_tooltip_srmi',
                'This option allows to set FPS limit to 120.\n'
                '**Enabled**: Updates Graphics Settings Windows Registry key with 120 FPS value on game start.\n'
                '**Disabled**: Has no effect on FPS settings, use in-game settings to undo already forced 120 FPS.\n'
                '**Warning!** Tweak is supported only for the Global HSR client and will not work for CN.\n'
                '*Note: Edits `FPS` value in `HKEY_CURRENT_USER/SOFTWARE/Cognosphere/Star Rail/GraphicsSettings_Model_h2986158309`.*'))
        elif Config.Launcher.active_importer == 'GIMI':
            msg = str(L('general_settings_unlock_fps_tooltip_gimi',
                'This option allows to force 120 FPS mode.\n'
                '**Enabled**: Launch game via `unlockfps_nc.exe` and let it run in background to keep FPS tweak applied.\n'
                '**Disabled**: Launch game via original `.exe` file, has no effect on FPS.\n'
                '*Hint: If FPS Unlocker package is outdated, you can manually update "unlockfps_nc.exe" from original repository.*\n'
                '*Local Path*: `Resources/Packages/GI-FPS-Unlocker/unlockfps_nc.exe`\n'
                '*Original Repository*: `https://github.com/34736384/genshin-fps-unlock`'))
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
        self.set_tooltip(str(L('general_settings_window_mode_tooltip', 'Game window mode when started with FPS Unlocker.')))
        self.trace_write(Vars.Active.Importer.unlock_fps, self.handle_write_unlock_fps)

    def handle_write_unlock_fps(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')


class ApplyTweaksCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_apply_tweaks_checkbox', 'Apply Performance Tweaks')),
            variable=Vars.Active.Importer.apply_perf_tweaks,
            master=master)
        self.set_tooltip(str(L('general_settings_apply_tweaks_tooltip',
            '**Enabled**: Add list of performance tweaks to `[SystemSettings]` section of `Engine.ini` on game start.\n'
            "**Disabled**: Do not add tweaks to `Engine.ini`. Already added ones will have to be removed manually.\n\n"
            'List of tweaks:\n'
            '* r.Streaming.HLODStrategy = 2\n'
            '* r.Streaming.PoolSizeForMeshes = -1\n'
            '* r.XGEShaderCompile = 0\n'
            '* FX.BatchAsync = 1\n'
            '* FX.EarlyScheduleAsync = 1\n'
            '* fx.Niagara.ForceAutoPooling = 1\n'
            '* wp.Runtime.KuroRuntimeStreamingRangeOverallScale = 0.5\n'
            '* tick.AllowAsyncTickCleanup = 1\n'
            '* tick.AllowAsyncTickDispatch = 1')))


class EnableHDR(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=str(L('general_settings_enable_hdr_checkbox', 'Enable HDR')),
            variable=Vars.Active.Importer.enable_hdr,
            master=master)
        self.set_tooltip(str(L('general_settings_enable_hdr_tooltip',
            '**Warning**! Your monitor must support HDR and `Use HDR` must be enabled in Windows Display settings!\n'
            '**Enabled**: Turn HDR On. Creates HDR registry record each time before the game launch.\n'
            '**Disabled**: Turn HDR Off. No extra action required, game auto-removes HDR registry record on launch.')))
