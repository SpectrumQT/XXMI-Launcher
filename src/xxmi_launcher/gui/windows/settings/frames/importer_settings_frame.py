import subprocess
import webbrowser
import re

from dataclasses import dataclass
from customtkinter import filedialog
from urllib.parse import urlparse

import core.event_manager as Events
import core.config_manager as Config
import core.path_manager as Paths
import gui.vars as Vars

from core.locale_manager import L, Locale

from core.config.enums import InjectMode, InputDisableMode, LogLevel

from gui.windows.settings.settings_content_frame import SettingsContentFrame, SettingsSection, SettingsOption, OptionWidget, Condition


class ModelImporterSettingsFrame(SettingsContentFrame):
    def __init__(self, master):
        super().__init__(
            master,
            sections=(

                SettingsSection(
                    label_text=L("importer_settings_startup_section_label", "Startup"),
                    options=(

                        SettingsOption(
                            label_text=L("importer_settings_importer_folder_label_dynamic", "{importer} Folder").format(importer=Config.Launcher.active_importer),
                            widget=OptionWidget.INPUT_STR,
                            value_variable="Vars.Active.Importer.importer_folder",
                            input_button_text=L("settings_browse_path_button", "Browse..."),
                            input_button_command=self.change_importer_folder,
                            tooltip=L("importer_settings_importer_folder_entry_tooltip", """
                                Path to folder containing **Mods** folder, **d3dx.ini** and other **{importer}** resources.
                    
                                * **Absolute**: Set any arbitrary folder, e.g. `C:/Games/{importer}/`.
                                * **Relative**: Set any folder **inside** the Launcher folder, i.e. `{importer}/` (default).
                            """).format(importer=Config.Launcher.active_importer),
                        ),

                        SettingsOption(
                            label_text=L("importer_settings_inject_mode_label", "XXMI DLL Injection Mode"),
                            widget=OptionWidget.DROPDOWN,
                            value_variable="Vars.Active.Importer.xxmi_dll_inject_mode",
                            dropdown_values=InjectMode,
                            tooltip=L("advanced_settings_custom_launch_inject_mode_option_menu_tooltip", """
                                Defines the way of **XXMI DLL** injection into the game process.
                                
                                * **{general_settings_inject_mode_direct}:** Use `WriteProcessMemory`, more reliable but requires direct memory access.
                                * **{general_settings_inject_mode_hook}:** Use `SetWindowsHookEx`, less reliable, but potentially less prominent for anti-cheats.
                                * **{general_settings_inject_mode_skip}:** Skip **XXMI DLL** injection.
                            """),
                        ),

                        SettingsOption(
                            label_text=L("general_settings_xxmi_delay_label", "XXMI DLL Initialization Delay"),
                            widget=OptionWidget.INPUT_INT,
                            value_variable="Vars.Active.Importer.xxmi_dll_init_delay",
                            tooltip=L("general_settings_xxmi_delay_entry_tooltip_base", """
                                Delay in milliseconds for how long injected XXMI DLL (3dmigoto) must wait before initialization.
                                {tooltip_footer}
                            """).format(
                                tooltip_footer=({
                                    "WWMI": L("general_settings_xxmi_delay_entry_tooltip_footer_wwmi", """
                                        <font color="red">⚠ Wuthering Waves crashes on launch with wrong delay! ⚠</font>
                                        <font color="#8B8000">⚠ If default value fails, try to increase or decrease it until WuWa stops crashing. ⚠</font>
                                        ## Known values for Wuthering Waves 2.4:
                                        - **500**: Default, works for most users.
                                        - **150**: Minimal known value to work along with ReShade.
                                        - **50**: Minimal known value to work.
                                        - **1000+**: Some users need really huge delays.
                                    """),
                                }.get(
                                    Config.Launcher.active_importer,
                                    L("general_settings_xxmi_delay_entry_tooltip_footer_general", """
                                        If game crashes with no mods, try to increase it. Start with steps of 50 and increase them as you go.
                                    """),
                                ) + '\n\n<font color="#666666">d3dx.ini › [System] › dll_initialization_delay</font>'),
                            ),
                        ),

                        SettingsOption(
                            label_text=L("importer_settings_ini_protection_label", "Config Protection"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Migoto.clear_unknown_settings",
                            tooltip=L("importer_settings_enforce_rendering_checkbox_tooltip", """
                                * **Enabled:** Ensure **{importer}**-compatible `d3dx.ini` settings.
                                * **Disabled:** Required settings will not be applied to `d3dx.ini`.
                            """).format(
                                importer=Config.Launcher.active_importer,
                                texture_hash=0 if Config.Launcher.active_importer != "WWMI" else 1,
                                track_texture_updates=0 if Config.Launcher.active_importer != "WWMI" else 1
                            ),
                        ),

                    ),
                ),

                SettingsSection(
                    label_text=L("importer_settings_usability_section_label", "Usability"),
                    options=(

                        SettingsOption(
                            label_text=L("importer_settings_mute_warnings_checkbox", "Mute Warnings"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Migoto.mute_warnings",
                            tooltip=L("importer_settings_mute_warnings_checkbox_tooltip", """
                                Enable display of mod error warnings and beeping sound.
                    
                                * **Enabled:** No error warnings or beeps whatsoever. Ignorance is bliss.
                                * **Disabled:** Mod error warnings and beeps on **F10** will haunt poor souls.
                            """) + '\n\n<font color="#666666">d3dx.ini › [Logging] › show_warnings</font>',
                        ),

                        SettingsOption(
                            label_text=L("importer_settings_clear_unknown_settings_checkbox", "Clear Unknown Mod Settings"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Migoto.clear_unknown_settings",
                            tooltip=L("importer_settings_clear_unknown_settings_tooltip", """
                                Controls clean-up of mod settings when the mods that defined them are no longer present.
                    
                                * **Enabled:** Clear unknown settings after **second** reload since mods removal.
                                * **Disabled:** Do not clear unknown settings, keep them in **d3dx_user.ini** forever.
                            """) + '\n\n<font color="#666666">d3dx.ini › [System] › clear_unknown_settings</font>',
                        ),

                    ),
                ),

                SettingsSection(
                    label_text=L("launcher_settings_input_section_label", "Input"),
                    options=(

                        SettingsOption(
                            label_text=L("importer_settings_input_checkbox", "Enable By Default"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Migoto.input",
                            tooltip=L("importer_settings_input_checkbox_tooltip", """
                                Initial input state when game starts.
                    
                                * **Enabled:** All input is enabled.
                                * **Disabled:** Input is disabled according to **{importer_settings_input_disable_mode_label}**.
                            """) + '\n\n<font color="#666666">d3dx.ini › [Input] › input</font>',
                        ),

                        SettingsOption(
                            label_text=L("importer_settings_input_disable_mode_label", "Input Disabling Mode"),
                            widget=OptionWidget.DROPDOWN,
                            value_variable="Vars.Active.Migoto.input_disable_mode",
                            dropdown_values=InputDisableMode,
                            tooltip=L("importer_settings_input_disable_mode_option_menu_tooltip", """
                                Determines which input is disabled when **{launcher_settings_input_section_label}** is **Disabled**.
                    
                                * **{importer_settings_input_disable_mode_mods}**: Disable input defined by mods.
                                * **{importer_settings_input_disable_mode_all}**: Disable all input except the **Toggle Input** hotkey (**CTRL+ALT+SHIFT+END**).
                            """) + '\n\n<font color="#666666">d3dx.ini › [Input] › input_disable_mode</font>',
                        ),

                    ),
                ),

                SettingsSection(
                    label_text=L("launcher_settings_hunting_section_label", "Shader Hunting"),
                    options=(

                        SettingsOption(
                            label_text=L("importer_settings_enable_hunting_checkbox", "Enable Hunting"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Migoto.enable_hunting",
                            tooltip=L("importer_settings_enable_hunting_checkbox_tooltip", """
                                * **Enabled:** Allows to toggle **Hunting Mode** via Numpad [0] hotkey.
                                * **Disabled:** **Hunting Mode** is hard disabled.
                            """) + '\n\n<font color="#666666">d3dx.ini › [Hunting] › hunting</font>',
                        ),

                        SettingsOption(
                            label_text=L("importer_settings_dump_shaders_checkbox", "Dump Shaders"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Migoto.dump_shaders",
                            tooltip=L("importer_settings_dump_shaders_checkbox_tooltip", """
                                * **Enabled:** Hunting Mode [Copy Hash] key also saves selected shader as file in **ShaderFixes**.
                                * **Disabled:** Hunting Mode [Copy Hash] only copies hash of selected shader to clipboard.
                            """) + '\n\n<font color="#666666">d3dx.ini › [Hunting] › marking_actions</font>',
                        ),

                    ),
                ),

                SettingsSection(
                    label_text=L("launcher_settings_logging_section_label", "Logging"),
                    options=(

                        SettingsOption(
                            label_text=L("launcher_settings_log_verbosity_label", "Log File Output Verbosity"),
                            widget=OptionWidget.DROPDOWN,
                            value_variable="Vars.Active.Migoto.log_level",
                            dropdown_values=LogLevel,
                            tooltip=L("importer_settings_log_level_option_menu_tooltip", """
                                Controls how verbose **d3d11_log.txt** file is.
                                
                                * **{importer_settings_log_level_disabled}**: Log nothing.
                                * **{importer_settings_log_level_warning}**: Log warnings and overlay messages.
                                * **{importer_settings_log_level_info}**: Also log API usage calls.
                                * **{importer_settings_log_level_debug}**: Also log super verbose massive debug output.
                            """) + '\n\n<font color="#666666">d3dx.ini › [Logging] › log_level</font>',
                        ),

                    ),
                ),

            ),
        )

    @staticmethod
    def change_importer_folder():
        importer_folder = filedialog.askdirectory(initialdir=Vars.Active.Importer.importer_folder.get())
        if importer_folder == "":
            return
        Vars.Active.Importer.importer_folder.set(importer_folder)