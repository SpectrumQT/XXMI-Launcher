import logging
import subprocess
import webbrowser

from dataclasses import dataclass
from typing import Callable
from customtkinter import filedialog

import core.event_manager as Events
import core.config_manager as Config
import core.path_manager as Paths
import gui.vars as Vars
from core.game_launcher import Launcher

from core.locale_manager import L, Locale
from core.config.enums import GameLaunch, StartMethod, WindowMode, ProcessPriority, WuWaResourceTier

from gui.windows.settings.settings_content_frame import SettingsContentFrame, SettingsSection, SettingsOption, OptionWidget, Condition

log = logging.getLogger(__name__)


class GeneralSettingsFrame(SettingsContentFrame):

    def __init__(self, master):
        super().__init__(
            master,
            sections=(
                SettingsSection(
                    label_text=L("launcher_settings_language_settings_label", "Launcher Language"),
                    options=(
                        SettingsOption(
                            label_text=L("launcher_settings_language_option_label", "Select Language"),
                            widget=OptionWidget.DROPDOWN,
                            value_variable="Vars.Launcher.locale",
                            dropdown_values={l.name: l.display_name for l in Locale.get_indexed_locales()},
                            dropdown_command=self.update_locale,
                        ),
                    ),
                ),

                SettingsSection(
                    label_text=L("launcher_settings_launch_settings_label", "Launch Settings"),
                    options=(
                        SettingsOption(
                            label_text=L("general_settings_game_launch_label", "Game Launch"),
                            widget=OptionWidget.DROPDOWN,
                            value_variable="Vars.Active.Importer.game_launch",
                            value_validate_command=self.validate_game_launch,
                            dropdown_values=GameLaunch,
                            tooltip=L("general_settings_game_launch_tooltip", """
                                Choose what the **{launcher_start_button}** button does.
                                
                                * **{general_settings_launch_direct}:** Launch the game directly from the detected or configured game folder.
                                * **{general_settings_launch_steam}:** Launch the game through Steam to enable Steam Overlay and playtime tracking.
                                * **{general_settings_launch_epic}:** Launch the game through Epic Games to enable Epic Games overlay and tracking.
                                * **{general_settings_launch_custom}:** Run a custom Windows command to launch the game.
                                * **{general_settings_launch_manual}:** Wait for you to launch the game manually.
                            """),
                        ),
                        SettingsOption(
                            label_text=L("general_settings_game_folder_label", "Game Folder"),
                            widget=OptionWidget.INPUT_STR,
                            value_variable="Vars.Active.Importer.game_folder",
                            value_validate_command=self.validate_game_folder,
                            button_text=L("general_settings_detect_game_folder_button", "🔍 Detect Installations"),
                            button_command=self.detect_game_folder,
                            button_tooltip=L("general_settings_detect_game_folder_button_tooltip",
                                "Try to automatically detect existing installation folders."
                            ),
                            input_button_text=L("settings_browse_path_button", "Browse..."),
                            input_button_command=self.change_game_folder,
                            tooltip=L("general_settings_game_folder_tooltip", """
                                ## Path to the folder containing the game executable
                                * Usually named: {game_folder_names:bold:or_list}.
                                * Contains files: {game_exe_names:bold:or_list}.
                                * Contains folders: {game_folder_children:bold:and_list}.
                            """).format(
                                game_folder_names=Vars.Active.Importer.game_folder_names,
                                game_exe_names=Vars.Active.Importer.game_exe_names,
                                game_folder_children=Vars.Active.Importer.game_folder_children,
                            ),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch",),
                                predicate=lambda: Vars.Active.Importer.game_launch.get() == GameLaunch.DIRECT,
                            ),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_launch_command_label", "Launch Command"),
                            widget=OptionWidget.INPUT_STR,
                            value_variable="Vars.Active.Importer.custom_launch",
                            tooltip=L("advanced_settings_custom_launch_entry_tooltip", """
                                Windows console command to run when Start button is pressed instead of default game exe launch.
                                Hint: If you want to change injection method only, just leave this field empty.
                                Warning! This command also overrides `Launch Options` from General Settings.
                                Note: If you want to start game exe with another custom exe, do it here.
                                Example (equivalent for command internally used by launcher to start GI via FPS unlocker):
                                `start /d "C:\Games\XXMI Launcher\Resources\Packages\GI-FPS-Unlocker" unlockfps_nc.exe`
                            """),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch",),
                                predicate=lambda: Vars.Active.Importer.game_launch.get() == GameLaunch.CUSTOM,
                            ),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_launch_options_checkbox", "Launch Options"),
                            widget=OptionWidget.INPUT_STR,
                            value_variable="Vars.Active.Importer.launch_options",
                            toggle_variable="Vars.Active.Importer.use_launch_options",
                            input_button_text=L("general_settings_launch_options_about_button", "About..."),
                            input_button_command=self.open_docs,
                            input_button_tooltip=L("general_settings_launch_options_about_button_tooltip", """
                                Open {engine} command line arguments documentation webpage.
                                Note: Game engine is customized by devs and some args may not work.
                            """).format(
                                engine="UE4" if Config.Launcher.active_importer == "WWMI" else "Unity"
                            ),
                            tooltip=({
                                "WWMI": L("general_settings_launch_options_entry_tooltip_wwmi", """
                                    **Enabled**: Start game via **Client-Win64-Shipping.exe** with specified command line arguments.
                    
                                    - Disable intro: -SkipSplash
                    
                                    **Disabled (default)**: Start game normally via **Wuthering Waves.exe** (most reliable way).
                                    <font color="red">⚠ Game may crash with this option enabled! ⚠</font>
                                """)
                            }.get(
                                Config.Launcher.active_importer,
                                L("general_settings_launch_options_entry_tooltip_default", """
                                    **Enabled**: Start game exe with specified command line arguments.
                                    **Disabled**: Ignore specified command line arguments and start game exe normally.
                                """)
                            )),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch",),
                                predicate=lambda: Vars.Active.Importer.game_launch.get() in [GameLaunch.DIRECT, GameLaunch.STEAM, GameLaunch.EPIC_GAMES],
                            ),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_start_method_label", "Game Executable Run Method"),
                            widget=OptionWidget.DROPDOWN,
                            value_variable="Vars.Active.Importer.start_method",
                            dropdown_values=StartMethod,
                            tooltip=L("general_settings_start_method_option_menu_tooltip", """
                                * **{general_settings_start_method_native}**: Create the game process directly.
                                * **{general_settings_start_method_shell}**: Start the game process via system console.
                            """),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch",),
                                predicate=lambda: Vars.Active.Importer.game_launch.get() == GameLaunch.DIRECT,
                            ),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_process_priority_label", "Process Priority"),
                            widget=OptionWidget.DROPDOWN,
                            value_variable="Vars.Active.Importer.process_priority",
                            dropdown_values=ProcessPriority,
                            tooltip=L("general_settings_process_priority_option_menu_tooltip", "Set process priority for the game exe."),
                            enabled_if=Condition(
                                variables=("Vars.Active.Importer.start_method",),
                                predicate=lambda: Vars.Active.Importer.start_method.get() == StartMethod.NATIVE,
                            ),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch",),
                                predicate=lambda: Vars.Active.Importer.game_launch.get() == GameLaunch.DIRECT,
                            ),
                        ),

                        SettingsOption(
                            label_text=L("game_process_wait_timeout_label", "Game Process Launch Wait Timeout"),
                            widget=OptionWidget.INPUT_INT,
                            value_variable="Vars.Active.Importer.process_timeout",
                            tooltip=L("game_process_wait_timeout_tooltip", """
                                Controls how long launcher should wait for the game to show its window after launch.
                                Game process will be considered as crashed once timeout is met.
                                Default value is **30**.
                            """),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_configure_platform_launch_options_checkbox",
                                "Configure Launch Options on {platform}"
                            ).format(
                                platform=GameLaunch.STEAM.value
                                # platform=Vars.Active.Importer.game_launch.get().value
                            ),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Importer.configure_platform_launch_options",
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch",),
                                predicate=lambda: Vars.Active.Importer.game_launch.get() == GameLaunch.STEAM,
                            ),
                            tooltip=lambda: L("general_settings_configure_platform_launch_options_checkbox_tooltip", """
                                Auto-set **Launch Options** of **{game}** in **{platform}** library to:
                                ```
                                {launch_options}
                                ```
                                {platform} client will be **restarted** if **Launch Options** are different.
                            """).format(
                                game=Vars.Active.Importer.game.get().value,
                                platform=Vars.Active.Importer.game_launch.get().value,
                                launch_options=lambda: Launcher.build_cmd_args(Vars.Settings, get_value=lambda x: x.get()),
                            ),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_skip_platform_game_launcher_checkbox",
                                "Skip {launcher} Launcher"
                            ).format(
                                launcher="HoYoPlay"
                            ),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Importer.skip_platform_game_launcher",
                            load_if=Condition(
                                predicate=lambda: Vars.Launcher.active_importer.get() in {"ZZMI"},
                            ),
                            enabled_if=Condition(
                                variables=("Vars.Active.Importer.configure_platform_launch_options",),
                                predicate=lambda: Vars.Active.Importer.configure_platform_launch_options.get(),
                            ),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch",),
                                predicate=lambda: Vars.Active.Importer.game_launch.get() == GameLaunch.STEAM,
                            ),
                            tooltip=L("general_settings_skip_platform_game_launcher_checkbox_tooltip", """
                                Make **{platform}** to launch **{game}** process directly, avoiding **{launcher}**.
                                
                                Requires **{general_settings_configure_platform_launch_options_checkbox}** to be enabled.
                            """).format(
                                game=Vars.Active.Importer.game.get().value,
                                platform=Vars.Active.Importer.game_launch.get().value,
                                launcher="HoYoPlay",
                            ),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_game_process_exe_label", "Custom Game Process Executable Name"),
                            widget=OptionWidget.INPUT_STR,
                            value_variable="Vars.Active.Importer.game_process_exe",
                            button_text=L("general_settings_game_process_exe_reset_button", "↻ Reset"),
                            button_command=self.reset_game_process_exe,
                            button_tooltip=L("general_settings_game_process_exe_reset_button_tooltip",
                                "Reset to **{game_exe_name}**"
                            ).format(game_exe_name=Vars.Active.Importer.game_process_exe.get_default()),
                            toggle_variable="Vars.Active.Importer.game_process_exe_enabled",
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch",),
                                predicate=lambda: Vars.Active.Importer.game_launch.get() != GameLaunch.DIRECT,
                            ),
                        ),

                    ),
                ),

                SettingsSection(
                    label_text=L("launcher_settings_game_settings_label", "Game Settings"),
                    options=(

                        SettingsOption(
                            label_text=L("general_settings_wuwa_resource_tier_label", "Client Resource Quality"),
                            widget=OptionWidget.DROPDOWN,
                            value_variable="Vars.Active.Importer.resource_tier",
                            dropdown_values=WuWaResourceTier,
                            load_if=Condition(
                                predicate=lambda: Vars.Launcher.active_importer.get() == "WWMI",
                            ),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch",),
                                predicate=lambda: Vars.Active.Importer.game_launch.get() == GameLaunch.DIRECT,
                            ),
                            tooltip=L("general_settings_wuwa_resource_tier_tooltip", """
                                Controls **[assets quality tier]({page_link})** used by **{game}**.
                                
                                * For **Steam** and **Epic Games** installations select **{default_tier}**.
                                * For **official launcher** installation select **any actually downloaded** tier.
                                 
                                Selection of wrong tier will cause the game to crash on loading.
                            """).format(
                                game=Config.Importers.WWMI.Importer.game.value,
                                page_link=r"https://wutheringwaves.kurogames.com/en/main/news/detail/5513",
                                default_tier=WuWaResourceTier.HD.value,
                            ),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_configure_game_checkbox",
                                "Configure Game Settings For {importer}"
                            ).format(
                                importer=Vars.Launcher.active_importer.get()
                            ),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Importer.configure_game",
                            load_if=Condition(
                                predicate=lambda: Vars.Launcher.active_importer.get() not in {"SRMI", "HIMI", "EFMI"},
                            ),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch",),
                                predicate=lambda: (
                                    Vars.Launcher.active_importer.get() not in {"WWMI", "ZZMI"}
                                    or Vars.Active.Importer.game_launch.get() in [GameLaunch.DIRECT, GameLaunch.STEAM, GameLaunch.EPIC_GAMES]
                                ),
                            ),
                            tooltip=({
                                "GIMI": L("general_settings_configure_game_tooltip_gimi", """
                                    **Enabled**: Ensure GIMI-compatible in-game **Graphics Settings** before game start:
                                    
                                    - `Dynamic Character Resolution: Off`
                                    
                                    **Disabled**: In-game settings will not be affected.
                                    
                                    <font color="red">⚠ Mods will not work with wrong settings! ⚠</font>
                                """),
                                "WWMI": L("general_settings_configure_game_tooltip_wwmi", """
                                    **Enabled**: Ensure WWMI-compatible in-game **Graphics Settings** before game start:
    
                                    - `Graphics Quality: Quality`
    
                                    **Disabled**: In-game settings will not be affected.
    
                                    <font color="red">⚠ Mods will not work with wrong settings! ⚠</font>
                                """),
                                "ZZMI": L("general_settings_configure_game_tooltip_zzmi", """
                                    **Enabled**: Ensure ZZMI-compatible in-game **Graphics Settings** before game start:
                    
                                    - `Character Quality: High`
                                    - `High-Precision Character Animation: Disabled`
                    
                                    **Disabled**: In-game settings will not be affected.
                    
                                    <font color="red">⚠ Mods will not work with wrong settings! ⚠</font>
                                """)
                            }.get(
                                Config.Launcher.active_importer,
                                L("error_no_data_available_short", "N/A")
                            )),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_disable_wounded_effect_checkbox", "Disable Wounded Effect"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Importer.disable_wounded_fx",
                            load_if=Condition(
                                predicate=lambda: Vars.Launcher.active_importer.get() == "WWMI",
                            ),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.configure_game","Vars.Active.Importer.game_launch",),
                                predicate=lambda: (
                                    Vars.Active.Importer.configure_game.get()
                                    and Vars.Active.Importer.game_launch.get() in [GameLaunch.DIRECT, GameLaunch.STEAM, GameLaunch.EPIC_GAMES]
                                ),
                            ),
                            tooltip=L("general_settings_disable_wounded_effect_checkbox_tooltip", """
                                Most mods do not support this effect, so textures usually break after few hits taken.
                                **Enabled**: Turn the effect `Off`. Ensures proper rendering of modded textures.
                                **Disabled**: Turn the effect `On`. Select this if you use `Injured Effect Remover` tool.
                            """),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_mesh_lod_base_fov_label", "Mesh LOD Base FOV"),
                            widget=OptionWidget.INPUT_INT,
                            value_variable="Vars.Active.Importer.mesh_lod_distance_lod_base_fov",
                            load_if=Condition(
                                predicate=lambda: Vars.Launcher.active_importer.get() == "WWMI",
                            ),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.configure_game","Vars.Active.Importer.game_launch",),
                                predicate=lambda: (
                                    Vars.Active.Importer.configure_game.get()
                                    and Vars.Active.Importer.game_launch.get() in [GameLaunch.DIRECT, GameLaunch.STEAM, GameLaunch.EPIC_GAMES]
                                ),
                            ),
                            tooltip=L("general_settings_mesh_lod_base_fov_tooltip", """
                                ## Minimal camera FoV value when full mesh of player character is replaced with simplified LoD:
                    
                                * Default is **165**, which should be enough for the most part of in-game scenes.
                                * The further away the camera is from active character, the bigger the FoV value is.
                            """) + """\n\n<font color="#666666">UserEngine.ini › ConsoleVariables › r.Kuro.SkeletalMesh.DistanceLODBaseFOV</font>""",
                        ),

                        SettingsOption(
                            label_text=({
                                "GIMI": L("general_settings_unlock_fps_checkbox", "Unlock FPS"),
                                "HIMI": L("general_settings_unlock_fps_checkbox", "Unlock FPS"),
                            }.get(
                                Config.Launcher.active_importer,
                                L("general_settings_unlock_fps_checkbox_force", "Force 120 FPS"),
                            )),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Importer.unlock_fps",
                            load_if=Condition(
                                predicate=lambda: Vars.Launcher.active_importer.get() not in {"ZZMI", "EFMI"},
                            ),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch",),
                                predicate=self.show_unlock_fps,
                            ),
                            tooltip=({
                                "GIMI": L("general_settings_unlock_fps_checkbox_tooltip_gimi", """
                                    This option allows to set custom FPS limit.
                                    **Warning!**: To minimize game engine glitches set FPS to 120 / 180 / 240 etc.
                                    **Enabled**: Launch game via `unlockfps_nc.exe` and let it run in background to keep FPS tweak applied.
                                    **Disabled**: Launch game via original `.exe` file, has no effect on FPS.
                                    *Hint: If FPS Unlocker package is outdated, you can manually update "unlockfps_nc.exe" from original repository.*
                                    *Local Path*: `Resources/Packages/GI-FPS-Unlocker/unlockfps_nc.exe`
                                    *Original Repository*: `https://github.com/34736384/genshin-fps-unlock`
                                """),
                                "HIMI": L("general_settings_unlock_fps_checkbox_tooltip_himi", """
                                    This option allows to set custom FPS limit.
                                    **Enabled**: Updates Graphics Settings Windows Registry key with specified FPS value on game start.
                                    **Disabled**: Has no effect on FPS settings, use in-game settings to undo already tweaked FPS.
                                """),
                                "SRMI": L("general_settings_unlock_fps_checkbox_tooltip_srmi", """
                                    This option allows to set FPS limit to 120.
                                    **Enabled**: Updates Graphics Settings Windows Registry key with 120 FPS value on game start.
                                    **Disabled**: Has no effect on FPS settings, use in-game settings to undo already forced 120 FPS.
                                    **Warning!** Tweak is supported only for the Global HSR client and will not work for CN.
                                    *Note: Edits `FPS` value in `HKEY_CURRENT_USER/SOFTWARE/Cognosphere/Star Rail/GraphicsSettings_Model_h2986158309`.*
                                """),
                                "WWMI": L("general_settings_unlock_fps_checkbox_tooltip_wwmi", """
                                    This option allows to set FPS limit to 120 even on not officially supported devices.
                                    Please do note that with some hardware game refuses to go 120 FPS even with this tweak.
                                    **Enabled**: Sets `CustomFrameRate` to `120` in `LocalStorage.db` on game start.
                                    **Disabled**: Has no effect on FPS settings, use in-game settings to undo already forced 120 FPS.
                                """),
                            }.get(
                                Config.Launcher.active_importer,
                                L("error_no_data_available_short", "N/A")
                            )),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_unlock_fps_value_label", "FPS Limit"),
                            widget=OptionWidget.INPUT_INT,
                            value_variable="Vars.Active.Importer.unlock_fps_value",
                            load_if=Condition(
                                predicate=lambda: Vars.Launcher.active_importer.get() in {"GIMI", "HIMI"},
                            ),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch", "Vars.Active.Importer.unlock_fps"),
                                predicate=lambda: self.show_unlock_fps() and Vars.Active.Importer.unlock_fps.get(),
                            ),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_window_mode_option_menu_label", "Window Mode"),
                            widget=OptionWidget.DROPDOWN,
                            value_variable="Vars.Active.Importer.window_mode",
                            dropdown_values=WindowMode,
                            load_if=Condition(
                                predicate=lambda: Vars.Launcher.active_importer.get() == "GIMI",
                            ),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch", "Vars.Active.Importer.unlock_fps"),
                                predicate=lambda: self.show_unlock_fps() and Vars.Active.Importer.unlock_fps.get(),
                            ),
                            tooltip=L("general_settings_window_mode_option_menu_tooltip", "Game window mode when started with FPS Unlocker."),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_enable_hdr_checkbox", "Enable HDR"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Importer.enable_hdr",
                            load_if=Condition(
                                predicate=lambda: Vars.Launcher.active_importer.get() == "GIMI",
                            ),
                            tooltip=L("general_settings_enable_hdr_checkbox_tooltip", """
                                **Warning**! Your monitor must support HDR and `Use HDR` must be enabled in Windows Display settings!
                                **Enabled**: Turn HDR On. Creates HDR registry record each time before the game launch.
                                **Disabled**: Turn HDR Off. No extra action required, game auto-removes HDR registry record on launch.
                            """),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_open_file_label", "Manual Game Config Edit"),
                            widget=OptionWidget.BUTTON,
                            value_variable="Vars.Active.Importer.game_folder",
                            button_text=L("general_settings_open_file_button", "📄 Open {file_name}").format(file_name="Engine.ini"),
                            button_command=self.open_engine_ini,
                            load_if=Condition(
                                predicate=lambda: Vars.Launcher.active_importer.get() == "WWMI",
                            ),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.game_launch",),
                                predicate=lambda: (
                                    Vars.Active.Importer.game_launch.get() in [GameLaunch.DIRECT, GameLaunch.STEAM, GameLaunch.EPIC_GAMES]
                                ),
                            ),
                            tooltip=L("general_settings_open_file_button_tooltip",
                                "Open **{file_name}** in default text editor file for manual tweaking."
                            ).format(file_name="Engine.ini"),
                        ),
                    ),
                ),
            ),
        )

    @staticmethod
    def show_unlock_fps():
        importer = Vars.Launcher.active_importer.get()
        game_launch = Vars.Active.Importer.game_launch.get()

        if importer == "GIMI":
            return game_launch == GameLaunch.DIRECT

        if importer == "WWMI":
            return game_launch in {GameLaunch.DIRECT, GameLaunch.STEAM, GameLaunch.EPIC_GAMES}

        return True

    def update_locale(self, new_value: str):
        Events.Fire(Events.Application.CloseSettings(save=True))
        Events.Fire(Events.Application.Busy())
        Events.Fire(Events.Application.LoadLocale(locale_name=Vars.Launcher.locale.get(), skip_reload=False))
        self.after_idle(lambda: Events.Fire(Events.GUI.ReloadGUI()))
        self.after_idle(lambda: Events.Fire(Events.Application.OpenSettings()))
        self.after_idle(lambda: Events.Fire(Events.Application.Ready()))

    @staticmethod
    def open_engine_ini():
        game_folder = Events.Call(Events.ModelImporter.ValidateGameFolder(Config.Active.Importer.game_folder))
        engine_ini = game_folder / "Client" / "Saved" / "Config" / "WindowsNoEditor" / "Engine.ini"
        if engine_ini.is_file():
            subprocess.Popen([f"{str(engine_ini)}"], shell=True)
        else:
            raise ValueError(L("error_general_settings_file_not_found", "File does not exist: **{file_name}**!").format(file_name=engine_ini))

    @staticmethod
    def open_docs():
        if Config.Launcher.active_importer == "WWMI":
            webbrowser.open("https://dev.epicgames.com/documentation/en-us/unreal-engine/command-line-arguments?application_version=4.27")
        elif Config.Launcher.active_importer in ["GIMI", "SRMI", "ZZMI", "HIMI", "EFMI"]:
            webbrowser.open("https://docs.unity3d.com/Manual/PlayerCommandLineArguments.html")

    @staticmethod
    def change_game_folder():
        game_folder = filedialog.askdirectory(initialdir=Vars.Active.Importer.game_folder.get())
        if game_folder == "":
            return
        Vars.Active.Importer.game_folder.set(game_folder)

    @staticmethod
    def detect_game_folder():
        try:
            game_folder, game_path, game_exe_path = Events.Call(Events.ModelImporter.DetectGameFolder())
            Vars.Active.Importer.game_folder.set(str(game_path))
            Config.Active.Importer.game_folder = str(game_path)
        except:
            pass

    @staticmethod
    def validate_game_launch() -> str | None:
        try:
            Launcher.require_launch(Vars.Active.Importer.game_launch.get())
        except Exception as e:
            return str(e)


    @staticmethod
    def validate_game_folder() -> str | None:
        try:
            game_folder = Vars.Active.Importer.game_folder.get()
            game_path = Events.Call(Events.ModelImporter.ValidateGameFolder(game_folder=game_folder.strip()))
        except Exception as e:
            log.debug(e)
            return str(e)

    @staticmethod
    def reset_game_process_exe():
        Vars.Active.Importer.game_process_exe.set(Vars.Active.Importer.game_process_exe.get_default())
