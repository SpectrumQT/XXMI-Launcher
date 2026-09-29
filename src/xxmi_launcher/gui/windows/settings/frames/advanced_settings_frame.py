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

from gui.windows.settings.settings_content_frame import SettingsContentFrame, SettingsSection, SettingsOption, \
    OptionWidget, Condition


class AdvancedSettingsFrame(SettingsContentFrame):
    def __init__(self, master):
        super().__init__(
            master,
            sections=(

                SettingsSection(
                    label_text=L("advanced_settings_pre_launch_section_label", "Run Before Game Launch"),
                    options=(

                        SettingsOption(
                            label_text=L("advanced_settings_pre_launch_command_label", "Pre-Launch Command"),
                            widget=OptionWidget.INPUT_STR,
                            value_variable="Vars.Active.Importer.run_pre_launch",
                            toggle_variable="Vars.Active.Importer.run_pre_launch_enabled",
                            tooltip=L("advanced_settings_run_pre_launch_tooltip", """
                                Windows console command to be executed before game exe launch.
                                Note: If something needs to be done before the game start, do it here.
                            """),
                        ),

                        SettingsOption(
                            label_text=L("advanced_settings_wait_checkbox", "Wait for Command Completion"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Importer.run_pre_launch_wait",
                            tooltip=L("advanced_settings_run_pre_launch_wait_checkbox_tooltip", """
                                Enabled: Wait for (blocking) command to finish its execution before launching the game exe.
                            """),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.run_pre_launch_enabled",),
                                predicate=lambda: bool(Vars.Active.Importer.run_pre_launch_enabled.get()),
                            ),
                        ),

                    ),
                ),

                SettingsSection(
                    label_text=L("advanced_settings_post_launch_section_label", "Run After XXMI DLL Injection"),
                    options=(

                        SettingsOption(
                            label_text=L("advanced_settings_post_load_command_label", "Post-Load Command"),
                            widget=OptionWidget.INPUT_STR,
                            value_variable="Vars.Active.Importer.run_post_load",
                            toggle_variable="Vars.Active.Importer.run_post_load_enabled",
                            tooltip=L("advanced_settings_run_post_load_checkbox_tooltip", """
                                Windows console command to be executed after hooking d3d11.dll to launched game exe.
                                Note: If something needs to be done after 3dmigoto injection, do it here.
                            """),
                        ),

                        SettingsOption(
                            label_text=L("advanced_settings_wait_checkbox", "Wait for Command Completion"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Importer.run_post_load_wait",
                            tooltip=L("advanced_settings_run_post_load_wait_checkbox_tooltip", """
                                Enabled: Wait for (blocking) command to finish its execution before treating the game launch as complete.
                            """),
                            visible_if=Condition(
                                variables=("Vars.Active.Importer.run_post_load_enabled",),
                                predicate=lambda: bool(Vars.Active.Importer.run_post_load_enabled.get()),
                            ),
                        ),

                    ),
                ),

                SettingsSection(
                    label_text=L("advanced_settings_custom_libraries_section_label", "Custom Libraries"),
                    options=(

                        SettingsOption(
                            label_text=L("advanced_settings_inject_libraries_checkbox", "Inject Libraries"),
                            widget=OptionWidget.INPUT_TEXT,
                            value_variable="Vars.Active.Importer.extra_libraries",
                            toggle_variable="Vars.Active.Importer.extra_libraries_enabled",
                            tooltip=L("advanced_settings_inject_libraries_tooltip", """
                                List of additional DLL paths to inject into the game process. 1 path per line.
                                injection will be made via WriteProcessMemory method.
                                Example (inject ReShade dll):
                                `C:\Games\ReShade\ReShade64.dll`
                            """),
                        ),

                        SettingsOption(
                            label_text=L("advanced_settings_unsafe_mode_checkbox", "Unsafe Mode"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Migoto.unsafe_mode",
                            tooltip=L("advanced_settings_unsafe_mode_checkbox_tooltip", """
                                Enabled: Allow 3-rd party 3dmigoto dlls.
                                Disabled: Disallow 3-rd party 3dmigoto dlls.
                                Note: If 3-rd party d3d11.dll does not support running from nested directories, it will fail to load.
                            """),
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