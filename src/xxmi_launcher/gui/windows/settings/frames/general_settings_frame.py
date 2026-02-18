import subprocess
import webbrowser

from customtkinter import filedialog, ThemeManager

import core.event_manager as Events
import core.config_manager as Config
import core.path_manager as Paths
import gui.vars as Vars

from core.locale_manager import L, Locale
from core.application import Application

from gui.classes.containers import UIFrame, UIScrollableFrame
from gui.classes.widgets import UILabel, UIButton, UIEntry, UICheckbox,  UIOptionMenu


class GeneralSettingsFrame(UIScrollableFrame):
    def __init__(self, master, fix_grid=False):
        super().__init__(master, height=410, corner_radius=0, border_width=0, hide_scrollbar=True, fix_grid=fix_grid)
        self._scrollbar_hidden_color = master._fg_color

        self.grid_columnconfigure((0, 2, 3), weight=1)
        self.grid_columnconfigure(1, weight=100)
        self.grid_rowconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(6, weight=100)

        # Language
        self.put(LanguageLabel(self)).grid(row=0, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
        self.put(LanguageOptionMenu(self)).grid(row=0, column=1, padx=(0, 10), pady=(0, 30), sticky='w', columnspan=3)

        # Game Folder
        self.put(GameFolderLabel(self)).grid(row=1, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
        self.put(GameFolderFrame(self)).grid(row=1, column=1, padx=(0, 65), pady=(0, 30), sticky='new', columnspan=3)
        self.put(DetectGameFolderButton(self)).grid(row=1, column=1, padx=(0, 20), pady=(0, 30), sticky='e', columnspan=3)

        # Launch Options
        self.put(LaunchOptionsLabel(self)).grid(row=2, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
        self.put(LaunchOptionsFrame(self)).grid(row=2, column=1, padx=(0, 20), pady=(0, 30), sticky='ew', columnspan=3)

        # Process Priority
        self.put(StartMethodLabel(self)).grid(row=3, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
        self.put(ProcessOptionsFrame(self)).grid(row=3, column=1, padx=(0, 20), pady=(0, 30), sticky='w', columnspan=3)

        # Auto Config
        if Vars.Launcher.active_importer.get() not in ['SRMI', 'HIMI', 'EFMI']:
            self.put(AutoConfigLabel(self)).grid(row=4, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
            self.put(AutoConfigFrame(self)).grid(row=4, column=1, padx=(0, 20), pady=(0, 30), sticky='w', columnspan=3)

        if Vars.Launcher.active_importer.get() not in ['ZZMI', 'EFMI']:
            
            # Tweaks
            self.put(TweaksLabel(self)).grid(row=5, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
    
            tweaks_frame = UIFrame(self, fg_color=master._fg_color)
            tweaks_frame.grid(row=5, column=1, padx=(0, 0), pady=(0, 30), sticky='we', columnspan=3)
            tweaks_frame.put(UnlockFPSCheckbox(tweaks_frame)).grid(row=0, column=0, padx=(0, 10), pady=(0, 0), sticky='w')
    
            # Window mode for GI FPS Unlocker
            if Vars.Launcher.active_importer.get() == 'GIMI':
                tweaks_frame.put(UnlockFPSValueEntry(tweaks_frame)).grid(row=0, column=1, padx=(0, 10), pady=(0, 0), sticky='w')
                tweaks_frame.grab(UnlockFPSValueEntry).set_tooltip(tweaks_frame.grab(UnlockFPSCheckbox))
                tweaks_frame.put(UnlockFPSWindowOptionMenu(tweaks_frame)).grid(row=0, column=2, padx=(20, 10), pady=(0, 0), sticky='w')
                tweaks_frame.put(EnableHDR(tweaks_frame)).grid(row=0, column=3, padx=(60, 10), pady=(0, 0), sticky='w')

            elif Vars.Launcher.active_importer.get() == 'HIMI':
                tweaks_frame.put(UnlockFPSValueEntry(tweaks_frame)).grid(row=0, column=1, padx=(0, 10), pady=(0, 0), sticky='w')
                tweaks_frame.grab(UnlockFPSValueEntry).set_tooltip(tweaks_frame.grab(UnlockFPSCheckbox))

            #  Performance Tweaks
            if Vars.Launcher.active_importer.get() == 'WWMI':
                tweaks_frame.put(ApplyTweaksCheckbox(tweaks_frame)).grid(row=0, column=1, padx=(20, 10), pady=(0, 0), sticky='w')
                tweaks_frame.put(OpenGameConfigButton(tweaks_frame)).grid(row=0, column=2, padx=(10, 20), pady=(0, 0), sticky='e')

        if Vars.Launcher.active_importer.get() == 'WWMI':
            self.put(EngineSettingsLabel(self)).grid(row=6, column=0, padx=(20, 10), pady=(0, 20), sticky='w')
            self.put(TextureStreamingFrame(self)).grid(row=6, column=1, padx=(0, 20), pady=(0, 20), sticky='w', columnspan=3)


class LanguageLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('launcher_settings_language_label', 'Language:'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class LanguageOptionMenu(UIOptionMenu):
    def __init__(self, master):
        super().__init__(
            width=120,
            height=36,
            font=('Arial', 14),
            dropdown_font=('Arial', 14),
            values={l.name: l.display_name for l in Locale.get_indexed_locales()},
            variable=Vars.Launcher.locale,
            command=self.handle_language_change,
            master=master)

    def handle_language_change(self, value):
        Events.Fire(Events.Application.LoadLocale(locale_name=Vars.Launcher.locale.get(), skip_reload=False))
        Events.Fire(Events.Application.CloseSettings(save=True))
        Events.Fire(Events.GUI.ReloadGUI())
        Events.Fire(Events.Application.Busy())
        Events.Fire(Events.Application.OpenSettings())
        Events.Fire(Events.Application.Ready())


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
            fg_color='transparent',
            master=master)

        self.grid_columnconfigure(1, weight=100)

        self.put(LaunchOptionsCheckbox(self)).grid(row=0, column=0, padx=(0, 0), pady=(0, 0), sticky='w')
        self.put(LaunchOptionsEntryFrame(self)).grid(row=0, column=1, padx=(0, 0), pady=(0, 0), sticky='ew')
        self.grab(LaunchOptionsCheckbox).set_tooltip(self.grab(LaunchOptionsEntryFrame).grab(LaunchOptionsEntry))


class LaunchOptionsEntryFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            border_color = ThemeManager.theme["CTkEntry"].get("border_color", None),
            border_width = ThemeManager.theme["CTkEntry"].get("border_width", None),
            fg_color = ThemeManager.theme["CTkEntry"].get("fg_color", None),
            master=master)

        self.grid_columnconfigure(0, weight=100)

        self.put(LaunchOptionsEntry(self)).grid(row=0, column=0, padx=(4, 0), pady=(2, 2), sticky='ew')
        self.put(LaunchOptionsButton(self)).grid(row=0, column=1, padx=(0, 4), pady=(2, 2), sticky='e')

        self.trace_write(Vars.Active.Importer.use_launch_options, self.handle_write_use_launch_options)

    def handle_write_use_launch_options(self, var, val):
        if val:
            self.configure(
                fg_color = ThemeManager.theme['CTkEntry'].get('fg_color', None),
                border_color = ThemeManager.theme["CTkEntry"].get("border_color", None))
        else:
            self.configure(
                fg_color = ThemeManager.theme['CTkEntry'].get('fg_color_disabled', None),
                border_color = ThemeManager.theme["CTkEntry"].get("border_color_disabled", None))


class ProcessOptionsFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            fg_color = 'transparent',
            master=master)

        self.grid_columnconfigure(0, weight=100)

        self.put(StartMethodOptionMenu(self)).grid(row=0, column=0, padx=(0, 10), pady=(0, 0), sticky='w')

        self.put(ProcessPriorityLabel(self)).grid(row=0, column=1, padx=20, pady=(0, 0), sticky='w')
        self.put(ProcessPriorityOptionMenu(self)).grid(row=0, column=2, padx=(0, 10), pady=(0, 0), sticky='w')

        self.put(TimeoutLabel(self)).grid(row=0, column=3, padx=20, pady=0, sticky='e')
        self.put(TimeoutEntry(self)).grid(row=0, column=4, padx=(0, 0), pady=0, sticky='e')
        self.grab(TimeoutLabel).set_tooltip(self.grab(TimeoutEntry))


class AutoConfigFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            fg_color = 'transparent',
            master=master)

        self.grid_columnconfigure(0, weight=100)

        self.put(ConfigureGameCheckbox(self)).grid(row=0, column=0, padx=(0, 10), pady=(0, 0), sticky='w')
        
        if Vars.Launcher.active_importer.get() == 'WWMI':
            self.put(ForceUltraHighLodBias(self)).grid(row=0, column=1, padx=(10, 20), pady=(0, 0), sticky='w')
            self.put(DisableWoundedEffectCheckbox(self)).grid(row=0, column=2, padx=(10, 20), pady=(0, 0), sticky='w')


class EngineSettingsLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_engine_settings_label', 'Engine Settings:'),
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

        self.put(MeshLODDistanceOffsetLabel(self)).grid(row=0, column=2, padx=(30, 0), pady=(0, 0), sticky='w')
        self.put(MeshLODDistanceOffsetEntry(self)).grid(row=0, column=3, padx=(10, 0), pady=(0, 0), sticky='w')
        self.grab(MeshLODDistanceOffsetLabel).set_tooltip(self.grab(MeshLODDistanceOffsetEntry))

        self.put(TextureStreamingMinBoostLabel(self)).grid(row=1, column=0, padx=(0, 0), pady=(15, 0), sticky='w')
        self.put(TextureStreamingMinBoostEntry(self)).grid(row=1, column=1, padx=(10, 0), pady=(15, 0), sticky='w')
        self.grab(TextureStreamingMinBoostLabel).set_tooltip(self.grab(TextureStreamingMinBoostEntry))

        self.put(TextureStreamingUseAllMipsCheckbox(self)).grid(row=1, column=2, padx=(30, 0), pady=(15, 0), sticky='w', columnspan=2)

        self.put(TextureStreamingPoolSizeLabel(self)).grid(row=2, column=0, padx=(0, 0), pady=(10, 0), sticky='w', rowspan=2)
        self.put(TextureStreamingPoolSizeEntry(self)).grid(row=2, column=1, padx=(10, 0), pady=(10, 0), sticky='w', rowspan=2)
        self.grab(TextureStreamingPoolSizeLabel).set_tooltip(self.grab(TextureStreamingPoolSizeEntry))
        self.put(TextureStreamingLimitPoolToVramCheckbox(self)).grid(row=2, column=2, padx=(30, 0), pady=(15, 0), sticky='w', columnspan=2)
        self.put(TextureStreamingFixedPoolSizeCheckbox(self)).grid(row=3, column=2, padx=(30, 0), pady=(15, 0), sticky='w', columnspan=2)


class GameFolderLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_game_folder_label', 'Game Folder:'),
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
        return L('general_settings_game_folder_tooltip', """
            ## Path to the folder containing the game executable
            * Usually named: {game_folder_names:bold:or_list}.
            * Contains files: {game_exe_names:bold:or_list}.
            * Contains folders: {game_folder_children:bold:and_list}.
        """).format(
            game_folder_names=Vars.Active.Importer.game_folder_names,
            game_exe_names=Vars.Active.Importer.game_exe_names,
            game_folder_children=Vars.Active.Importer.game_folder_children,
        )


class GameFolderErrorLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_game_folder_error_label', 'Failed to detect Game Folder!'),
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
            text=L('settings_browse_path_button', 'Browse...'),
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

        self.set_tooltip(L('general_settings_detect_game_folder_button_tooltip', 'Try to automatically detect existing installation folders.'))

    def detect_game_folder(self):
        try:
            game_folder, game_path, game_exe_path = Events.Call(Events.ModelImporter.DetectGameFolder())
            Vars.Active.Importer.game_folder.set(str(game_path))
            Config.Active.Importer.game_folder = str(game_path)
        except:
            pass


class LaunchOptionsLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_launch_options_label', 'Launch Options:'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class LaunchOptionsCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text='',
            font=('Microsoft YaHei', 14, 'bold'),
            variable=Vars.Active.Importer.use_launch_options,
            width=36,
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
        self.trace_write(Vars.Active.Importer.use_launch_options, self.handle_write_use_launch_options)

    def get_tooltip(self):
        if Config.Launcher.active_importer == 'WWMI':
            return L('general_settings_launch_options_entry_tooltip_wwmi', """
                **Enabled**: Start game via **Client-Win64-Shipping.exe** with specified command line arguments.
                
                - Disable intro: -SkipSplash
                
                **Disabled (default)**: Start game normally via **Wuthering Waves.exe** (most reliable way).
                <font color="red">⚠ Game may crash with this option enabled! ⚠</font>
            """)
        else:
            return L('general_settings_launch_options_entry_tooltip_default', """
                **Enabled**: Start game exe with specified command line arguments.
                **Disabled**: Ignore specified command line arguments and start game exe normally.
            """)

    def handle_write_use_launch_options(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')


class LaunchOptionsButton(UIButton):
    def __init__(self, master):
        fg_color = ThemeManager.theme['CTkEntry'].get('fg_color', None)

        super().__init__(
            text=L('general_settings_launch_options_about_button', 'About...'),
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

        self.trace_write(Vars.Active.Importer.use_launch_options, self.handle_write_use_launch_options)

    def handle_write_use_launch_options(self, var, val):
        if val:
            self.configure(
                fg_color=ThemeManager.theme['CTkEntry'].get('fg_color', None),
                hover_color=ThemeManager.theme['CTkEntry'].get('fg_color', None),
                text_color=['#000000', '#aaaaaa'],
            )
        else:
            self.configure(
                fg_color=ThemeManager.theme['CTkEntry'].get('fg_color_disabled', None),
                hover_color=ThemeManager.theme['CTkEntry'].get('fg_color_disabled', None),
                text_color=['#000000', '#666666'],
            )

    def open_docs(self):
        if Config.Launcher.active_importer == 'WWMI':
            webbrowser.open('https://dev.epicgames.com/documentation/en-us/unreal-engine/command-line-arguments?application_version=4.27')
        elif Config.Launcher.active_importer in ['GIMI', 'SRMI', 'ZZMI', 'HIMI', 'EFMI']:
            webbrowser.open('https://docs.unity3d.com/Manual/PlayerCommandLineArguments.html')

    def get_tooltip(self):
        if Config.Launcher.active_importer == 'WWMI':
            engine = 'UE4'
        elif Config.Launcher.active_importer in ['GIMI', 'SRMI', 'ZZMI', 'HIMI', 'EFMI']:
            engine = 'Unity'
        else:
            raise ValueError(f'Game engine is unknown!')

        return L('general_settings_launch_options_about_button_tooltip', """
            Open {engine} command line arguments documentation webpage.
            Note: Game engine is customized by devs and some args may not work.
        """).format(engine=engine)


class StartMethodLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_start_method_label', 'Start Method:'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class StartMethodOptionMenu(UIOptionMenu):
    def __init__(self, master):
        super().__init__(
            values={
                'Native': L('general_settings_start_method_native', 'Native'),
                'Shell': L('general_settings_start_method_shell', 'Shell'),
                'Manual': L('general_settings_start_method_manual', 'Manual'),
            },
            variable=Vars.Active.Importer.process_start_method,
            width=140,
            height=36,
            font=('Arial', 14),
            dropdown_font=('Arial', 14),
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        return L('general_settings_start_method_option_menu_tooltip', """
            **Native**: Create the game process directly. Usually it's the most reliable way.
            **Shell**: Start the game process via system console. Worth to try if you have some issues with Native.
            **Manual**: Skip launching the game on **Start** button press. Wait for user to launch it manually ({timeout}s timeout).
        """).format(timeout=Config.Active.Importer.process_timeout)


class TimeoutLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('launcher_settings_timeout_label', 'Timeout:'),
            font=('Microsoft YaHei', 14),
            fg_color='transparent',
            master=master)


class TimeoutEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.process_timeout,
            input_filter='INT',
            width=40,
            height=36,
            font=('Arial', 14),
            master=master)
        self.set_tooltip(L('launcher_settings_timeout_entry_tooltip', """
            Controls how long launcher should wait for the game to show its window after launch.
            Game process will be considered as crashed once timeout is met.
            Default value is **30**.
        """))

        self.trace_write(Vars.Active.Importer.process_timeout, self.handle_write_start_timeout)

    def handle_write_start_timeout(self, var, val):
        if val <= 0:
            Vars.Active.Importer.process_timeout.set(30)
            self.icursor('end')


class ProcessPriorityLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_process_priority_label', 'Process Priority:'),
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
            values={
                'Low': L('general_settings_process_priority_low', 'Low'),
                'Below Normal': L('general_settings_process_priority_below_normal', 'Below Normal'),
                'Normal': L('general_settings_process_priority_normal', 'Normal'),
                'Above Normal': L('general_settings_process_priority_above_normal', 'Above Normal'),
                'High': L('general_settings_process_priority_high', 'High'),
                'Realtime': L('general_settings_process_priority_realtime', 'Realtime'),
            },
            variable=Vars.Active.Importer.process_priority,
            width=140,
            height=36,
            font=('Arial', 14),
            dropdown_font=('Arial', 14),
            master=master)
        self.set_tooltip(L('general_settings_process_priority_option_menu_tooltip', """
            Set process priority for the game exe.
        """))

        self.trace_write(Vars.Active.Importer.process_start_method, self.handle_write_process_start_method)

    def handle_write_process_start_method(self, var, val):
        if val == 'Native':
            self.configure(state='normal')
        else:
            self.configure(state='disabled')


class AutoConfigLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_auto_config_label', 'Auto Config:'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class ConfigureGameCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_configure_game_checkbox', 'Configure Game Settings'),
            variable=Vars.Active.Importer.configure_game,
            master=master)

        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        if Config.Launcher.active_importer == 'GIMI':
            return L('general_settings_configure_game_tooltip_gimi', """
                **Enabled**: Ensure GIMI-compatible in-game **Graphics Settings** before game start:

                - `Dynamic Character Resolution: Off`

                **Disabled**: In-game settings will not be affected.

                <font color="red">⚠ Mods will not work with wrong settings! ⚠</font>
            """)
        elif Config.Launcher.active_importer == 'WWMI':
            return L('general_settings_configure_game_tooltip_wwmi', """
                **Enabled**: Ensure WWMI-compatible in-game **Graphics Settings** before game start:

                - `Graphics Quality: Quality`

                **Disabled**: In-game settings will not be affected.

                <font color="red">⚠ Mods will not work with wrong settings! ⚠</font>
            """)
        elif Config.Launcher.active_importer == 'ZZMI':
            return L('general_settings_configure_game_tooltip_zzmi', """
                **Enabled**: Ensure ZZMI-compatible in-game **Graphics Settings** before game start:

                - `Character Quality: High`
                - `High-Precision Character Animation: Disabled`

                **Disabled**: In-game settings will not be affected.

                <font color="red">⚠ Mods will not work with wrong settings! ⚠</font>
            """)
        else:
            return L('error_no_data_available_short', 'N/A')


class ForceUltraHighLodBias(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_force_ultra_high_lod_bias_label', 'Max LOD Bias'),
            variable=Vars.Active.Importer.force_max_lod_bias,
            master=master)
        self.set_tooltip(L('general_settings_force_ultra_high_lod_bias_tooltip', """
            **Enabled**: Set **LOD Bias** to **Ultra High** to force full resolution LOD textures.
            **Disabled**: Keep **LOD Bias** setting untouched. Select this if **Use All Mips** is enabled below.
        """))

        self.trace_write(Vars.Active.Importer.configure_game, self.handle_write_configure_game)

    def handle_write_configure_game(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')


class DisableWoundedEffectCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_disable_wounded_effect_checkbox', 'Disable Wounded Effect'),
            variable=Vars.Active.Importer.disable_wounded_fx,
            master=master)
        self.set_tooltip(L('general_settings_disable_wounded_effect_checkbox_tooltip', """
            Most mods do not support this effect, so textures usually break after few hits taken.
            **Enabled**: Turn the effect `Off`. Ensures proper rendering of modded textures.
            **Disabled**: Turn the effect `On`. Select this if you use `Injured Effect Remover` tool.
        """))

        self.trace_write(Vars.Active.Importer.configure_game, self.handle_write_configure_game)

    def handle_write_configure_game(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')


# class MeshLODDistanceLabel(UILabel):
#     def __init__(self, master):
#         super().__init__(
#             text=L('general_settings_mesh_lod_distance_label', 'Mesh LOD Distance:'),
#             font=('Microsoft YaHei', 14),
#             fg_color='transparent',
#             master=master)
#
#
# class MeshLODDistanceEntry(UIEntry):
#     def __init__(self, master):
#         super().__init__(
#             textvariable=Vars.Active.Importer.mesh_lod_distance_scale,
#             input_filter='FLOAT',
#             width=40,
#             height=36,
#             font=('Arial', 14),
#             master=master)
#
#         self.set_tooltip(L('general_settings_mesh_lod_distance_entry_tooltip', """
#             ## Controls how far game replaces full animated meshes with simplified LoDs:
#
#             * Set to **1** **(default)** to force full models as far as the game loads animated objects.
#                 - ✅ With this value mods are applied as far as you can see.
#                 - ⚡ Risk of performance drops for low-end GPUs.
#
#             * Set to lower value (e.g. `15`) for better performance.
#                 - ✅ Reduce FPS cost by allowing the game to use LoD meshes for distant animated objects.
#                 - ⚡ LoDs may look wrong due to modded textures being applied to original LoD meshes.
#
#             *Applied to CVars=r.Kuro.SkeletalMesh.LODDistanceScale value in all sections of DeviceProfiles.ini*
#         """))


class MeshLODDistanceOffsetLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_mesh_lod_offset_label', 'Mesh LOD Offset:'),
            font=('Microsoft YaHei', 14),
            fg_color='transparent',
            master=master)


class MeshLODDistanceOffsetEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.mesh_lod_distance_offset,
            input_filter='INT',
            width=40,
            height=36,
            font=('Arial', 14),
            master=master)

        self.set_tooltip(L('general_settings_mesh_lod_offset_tooltip', """
            ## Controls LoD meshes deploying behavior (when full animated models are replaced with simplified ones):
            
            * Default is **-10**, known range where full mesh remains always loaded is from **-1** to **-12** (depending on PC).
            * Mods are currently created for full meshes and cannot (easily) be applied to LoDs.
                
            *Applied to CVars=r.Kuro.SkeletalMesh.LODDistanceScaleDeviceOffset value in all sections of DeviceProfiles.ini*
        """))


class TextureStreamingBoostLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_texture_boost_label', 'Texture Boost:'),
            font=('Microsoft YaHei', 14),
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

        self.set_tooltip(L('general_settings_texture_boost_entry_tooltip', """
            ## Controls how aggressively higher-resolution textures are pushed to VRAM:
            
            Serves as a multiplier to streaming priorities configured for textures.
            
            * If modded textures are not loading, try increasing it to **25** or **30**.
                - ⚡ Too high values may increase VRAM usage and can cause stuttering if the pool is small.

            This value may require fine tuning to minimize modded textures loading delay:
            
            * Start tuning with **20.0** **(default)**.
                - ✅ This baseline value should work for most PCs.
            
            * If modded textures are loading fine, gradually decrease until small textures (like eyes) start breaking.
                - ✅ A value just above this “breaking point” typically gives minimal texture loading delay while staying VRAM-friendly.
            
            *Applied to CVars=r.Streaming.Boost value in all sections of DeviceProfiles.ini*
        """))


class TextureStreamingMinBoostLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_texture_min_boost_label', 'Minimal Boost:'),
            font=('Microsoft YaHei', 14),
            fg_color='transparent',
            master=master)


class TextureStreamingMinBoostEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.texture_streaming_min_boost,
            input_filter='FLOAT',
            width=60,
            height=36,
            font=('Arial', 14),
            master=master)

        self.set_tooltip(L('general_settings_texture_min_boost_entry_tooltip', """
            ## Defines a minimum streaming priority for textures:
            
            Values above **0** **(default)** set a priority floor that texture streaming priorities cannot go below.

            - ⚡ Use only if modded textures aren't loading regardless configured **Texture Boost** value.
            - ⚡ Same as with **Texture Boost**, always look for small textures (like eyes) when tuning the value.
            
            *Applied to CVars=r.Streaming.MinBoost value in all sections of DeviceProfiles.ini*
        """))


class TextureStreamingUseAllMipsCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_use_all_mips_label', 'Use All Mips'),
            variable=Vars.Active.Importer.texture_streaming_use_all_mips,
            master=master)
        self.set_tooltip(L('general_settings_use_all_mips_tooltip', """
            ## Controls whether texture resolution limits are applied:
            
            * **Enabled** **(default)**: Disable resolution restrictions from LOD Bias.
                - ✅ Allows to load full resolution textures at cost of higher VRAM usage.
                - ⚡ If it has no effect or consumes too much VRAM, try to enable **Max LOD Bias** instead.
            
            * **Disabled**: Enable resolution restrictions from LOD Bias.
                - ⚡ Modded textures won't load if disabled without Max (Ultra High) LOD Bias enabled.
                
            *Applied to CVars=r.Streaming.UseAllMips value in all sections of DeviceProfiles.ini*
        """))


class TextureStreamingPoolSizeLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_texture_streaming_pool_size_label', 'Texture Pool Size:'),
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

        self.set_tooltip(L('general_settings_texture_streaming_pool_size_entry_tooltip', """
            ## Controls how much VRAM the game can use for textures:

            * Set to **0** **(default)** for **automatic control** (based on available VRAM).
            * Set to specific value (e.g. 4096) for precise VRAM management.

            *Applied to CVars=r.Streaming.PoolSize value in all sections of DeviceProfiles.ini*
        """))


class TextureStreamingLimitPoolToVramCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_texture_streaming_limit_pool_checkbox', 'Limit Pool Size To VRAM'),
            variable=Vars.Active.Importer.texture_streaming_limit_to_vram,
            master=master)
        self.set_tooltip(L('general_settings_texture_streaming_limit_pool_checkbox_tooltip', """
            ## Sets the upper limit for how much VRAM the game can use for textures:

            * **Enabled** **(default)** – Limits texture pool size based on your GPU's available VRAM.
                - ✅ Helps prevent crashes or stuttering on low VRAM systems.
                - ⚡ May reduce texture quality or cause pop-ins if too restrictive on high-end GPUs.

            * **Disabled** – Unlocks maximum texture pool size, even if it exceeds your GPU's safe limits.
                - ✅ Can improve texture quality and reduce pop-ins on powerful systems.
                - ⚡ Risk of performance drops, stutters, or crashes if VRAM runs out.

            *Applied to CVars=r.Streaming.LimitPoolSizeToVRAM value in all sections of DeviceProfiles.ini*
        """))


class TextureStreamingFixedPoolSizeCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_texture_streaming_fixed_pool_size_checkbox', 'Use Fixed Pool Size'),
            variable=Vars.Active.Importer.texture_streaming_fixed_pool_size,
            master=master)
        self.set_tooltip(L('general_settings_texture_streaming_fixed_pool_size_checkbox_tooltip', """
            ## Controls automatic pool size grow/shrink capabilities:
            
            * **Enabled** **(default)** – Locks texture pool size to value calculated on game start.
                - ✅ Eliminates modded textures loading delay by minimizing texture mip levels pop in/out.
                - ⚡ Pool size is locked on game start, low end GPU users may want to close as much apps as possible.

            * **Disabled** – Allows game engine to dynamically resize pool.
                - ✅ Provides more freedom to both engine (allows mips streaming) and user (no need to close apps).
                - ⚡ Introduces short delay to modded textures loading unless **Texture Boost** values is perfectly tuned.

            *Applied to CVars=r.Streaming.UseFixedPoolSize value in all sections of DeviceProfiles.ini*
        """))


class OpenGameConfigButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_open_file_button', '🔍 Open {file_name}').format(file_name='Engine.ini'),
            command=self.open_engine_ini,
            width=140,
            height=36,
            font=('Roboto', 14),
            auto_width=True,
            master=master)
        self.set_tooltip(L('general_settings_open_file_button_tooltip', 'Open **{file_name}** in default text editor file for manual tweaking.').format(file_name='DeviceProfiles.ini'))

    def open_engine_ini(self):
        game_folder = Events.Call(Events.ModelImporter.ValidateGameFolder(Config.Active.Importer.game_folder))
        engine_ini = game_folder / 'Client' / 'Saved' / 'Config' / 'WindowsNoEditor' / 'Engine.ini'
        if engine_ini.is_file():
            subprocess.Popen([f'{str(engine_ini)}'], shell=True)
        else:
            raise ValueError(L('error_general_settings_file_not_found', 'File does not exist: **{file_name}**!').format(file_name=engine_ini))


class TweaksLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_tweaks_label', 'Tweaks:'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class UnlockFPSCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_unlock_fps_checkbox_force', 'Force 120 FPS'),
            variable=Vars.Active.Importer.unlock_fps,
            master=master)
        if Config.Launcher.active_importer in ['GIMI', 'HIMI']:
            self.configure(text=L('general_settings_unlock_fps_checkbox', 'Unlock FPS:'))
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        if Config.Launcher.active_importer == 'WWMI':
            return L('general_settings_unlock_fps_checkbox_tooltip_wwmi', """
                This option allows to set FPS limit to 120 even on not officially supported devices.
                Please do note that with some hardware game refuses to go 120 FPS even with this tweak.
                **Enabled**: Sets `CustomFrameRate` to `120` in `LocalStorage.db` on game start.
                **Disabled**: Has no effect on FPS settings, use in-game settings to undo already forced 120 FPS.
            """)
        elif Config.Launcher.active_importer == 'SRMI':
            return L('general_settings_unlock_fps_checkbox_tooltip_srmi', """
                This option allows to set FPS limit to 120.
                **Enabled**: Updates Graphics Settings Windows Registry key with 120 FPS value on game start.
                **Disabled**: Has no effect on FPS settings, use in-game settings to undo already forced 120 FPS.
                **Warning!** Tweak is supported only for the Global HSR client and will not work for CN.
                *Note: Edits `FPS` value in `HKEY_CURRENT_USER/SOFTWARE/Cognosphere/Star Rail/GraphicsSettings_Model_h2986158309`.*
            """)
        elif Config.Launcher.active_importer == 'GIMI':
            return L('general_settings_unlock_fps_checkbox_tooltip_gimi', """
                This option allows to set custom FPS limit.
                **Warning!**: To minimize game engine glitches set FPS to 120 / 180 / 240 etc.
                **Enabled**: Launch game via `unlockfps_nc.exe` and let it run in background to keep FPS tweak applied.
                **Disabled**: Launch game via original `.exe` file, has no effect on FPS.
                *Hint: If FPS Unlocker package is outdated, you can manually update "unlockfps_nc.exe" from original repository.*
                *Local Path*: `Resources/Packages/GI-FPS-Unlocker/unlockfps_nc.exe`
                *Original Repository*: `https://github.com/34736384/genshin-fps-unlock`
            """)
        elif Config.Launcher.active_importer == 'HIMI':
            return L('general_settings_unlock_fps_checkbox_tooltip_himi', """
                This option allows to set custom FPS limit.
                **Enabled**: Updates Graphics Settings Windows Registry key with specified FPS value on game start.
                **Disabled**: Has no effect on FPS settings, use in-game settings to undo already tweaked FPS.
            """)
        else:
            return L('error_no_data_available_short', 'N/A')

class UnlockFPSValueEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.unlock_fps_value,
            input_filter='INT',
            width=50,
            height=36,
            font=('Arial', 14),
            master=master)

        self.trace_write(Vars.Active.Importer.unlock_fps, self.handle_write_unlock_fps)

    def handle_write_unlock_fps(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')


class UnlockFPSWindowOptionMenu(UIOptionMenu):
    def __init__(self, master):
        super().__init__(
            values={
                'Windowed': L('general_settings_window_mode_windowed', 'Windowed'),
                'Borderless': L('general_settings_window_mode_borderless', 'Borderless'),
                'Fullscreen': L('general_settings_window_mode_fullscreen', 'Fullscreen'),
                'Exclusive Fullscreen': L('general_settings_window_mode_exclusive_fullscreen', 'Exclusive Fullscreen'),
            },
            variable=Vars.Active.Importer.window_mode,
            width=140,
            height=36,
            font=('Arial', 14),
            dropdown_font=('Arial', 14),
            master=master)
        self.set_tooltip(L('general_settings_window_mode_option_menu_tooltip', 'Game window mode when started with FPS Unlocker.'))
        self.trace_write(Vars.Active.Importer.unlock_fps, self.handle_write_unlock_fps)

    def handle_write_unlock_fps(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')


class ApplyTweaksCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_apply_tweaks_checkbox', 'Apply Performance Tweaks'),
            variable=Vars.Active.Importer.apply_perf_tweaks,
            master=master)
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        tweaks = ''
        for section, options in Vars.Active.Importer.perf_tweaks.items():
            tweaks += f'[{section}]' + '\n'
            tweaks += '\n'.join([f'{k} = {v}' for k, v in options.items()])
        return L('general_settings_apply_tweaks_checkbox_tooltip', """
            **Enabled**: Add list of performance tweaks to `[SystemSettings]` section of `Engine.ini` on game start.
            **Disabled**: Do not add tweaks to `Engine.ini`. Already added ones will have to be removed manually.
            
            List of tweaks:
            {tweaks}
        """).format(tweaks=tweaks)


class EnableHDR(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=L('general_settings_enable_hdr_checkbox', 'Enable HDR'),
            variable=Vars.Active.Importer.enable_hdr,
            master=master)
        self.set_tooltip(L('general_settings_enable_hdr_checkbox_tooltip', """
            **Warning**! Your monitor must support HDR and `Use HDR` must be enabled in Windows Display settings!
            **Enabled**: Turn HDR On. Creates HDR registry record each time before the game launch.
            **Disabled**: Turn HDR Off. No extra action required, game auto-removes HDR registry record on launch.
        """))
