import subprocess
import webbrowser
import re

from dataclasses import dataclass
from tkinter import Variable
from customtkinter import filedialog
from urllib.parse import urlparse

import core.event_manager as Events
import core.config_manager as Config
import core.path_manager as Paths
import gui.vars as Vars

from core.locale_manager import L, Locale
from core.config.enums import UpdateChannel, ProxyType

from gui.windows.settings.settings_content_frame import SettingsContentFrame, SettingsSection, SettingsOption, OptionWidget, Condition


class LauncherSettingsFrame(SettingsContentFrame):
    def __init__(self, master):
        super().__init__(
            master,
            sections=(

                SettingsSection(
                    label_text=L("launcher_settings_launcher_section_label", "Launcher"),
                    options=(
                        SettingsOption(
                            label_text=L("launcher_settings_auto_close_checkbox", "Close Launcher After Game Start"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Launcher.auto_close",
                            tooltip=L("launcher_settings_auto_close_checkbox_tooltip", """
                                Enabled: Launcher will close itself once the game has started and 3dmigoto injection has been confirmed.
                                Disabled: Launcher will keep itself running.
                            """),
                        ),
                        SettingsOption(
                            label_text=L("launcher_settings_theme_label", "UI Theme"),
                            widget=OptionWidget.DROPDOWN,
                            value_variable="Vars.Launcher.gui_theme",
                            dropdown_values=self.detect_themes,
                            dropdown_command=self.update_theme,
                            tooltip=L("launcher_settings_theme_option_menu_tooltip", """
                                Select launcher GUI theme.
                                Warning! `Default` theme will be overwritten by launcher updates!
                                To make a custom theme:
                                1. Create a duplicate of `Default` folder in `Themes` folder.
                                2. Rename the duplicate in a way you want it to be shown in Settings.
                                3. Edit or replace any images (valid extensions: webp, jpeg, png, jpg).
                            """),
                        ),
                        SettingsOption(
                            label_text=L("launcher_settings_dev_mode_checkbox", "Dev Mode"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Launcher.theme_dev_mode",
                            tooltip=L("launcher_settings_dev_mode_checkbox_tooltip", """
                                Enabled: Launcher will track changes in `custom-tkinter-theme.json` and apply them on the fly.
                                Disabled: Theme changes will not be tracked.
                            """),
                            on_value_update_command=self.toggle_theme_dev_mode,
                        ),

                    ),
                ),
                SettingsSection(
                    label_text=L("launcher_settings_updates_section_label", "Updates"),
                    options=(
                        SettingsOption(
                            label_text=L("launcher_settings_auto_update_checkbox", "Auto Update"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Launcher.auto_update",
                            tooltip=L("launcher_settings_auto_update_checkbox_tooltip", """
                                Enabled: Launcher and {importer} updates will be Downloaded and Installed automatically.
                                Disabled: Use special [▲] button next to [Start] button to Download and Install updates manually.
                            """).format(importer=Config.Launcher.active_importer)
                        ),

                        SettingsOption(
                            label_text=L("launcher_settings_update_channel_label", "Update Channel"),
                            widget=OptionWidget.DROPDOWN,
                            value_variable="Vars.Launcher.update_channel",
                            dropdown_values=UpdateChannel,
                            tooltip=L("launcher_settings_update_channel_option_menu_tooltip", """
                                * **{launcher_settings_update_channel_auto}**: Detect update installation method automatically.
                                * **{launcher_settings_update_channel_msi}**: Use native `.msi` installers to install updates.
                                * **{launcher_settings_update_channel_zip}**: Use portable `.zip` archives to install updates.
                            """),
                        ),

                        SettingsOption(
                            label_text=L("advanced_settings_overwrite_ini_checkbox", "Overwrite d3dx.ini"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Active.Importer.overwrite_ini",
                            tooltip=L("advanced_settings_overwrite_ini_checkbox_tooltip", """
                                * **Enabled:** {importer} updates will overwrite existing `d3dx.ini` to ensure its up-to-date state.
                                * **Disabled:** {importer} updates will keep existing `d3dx.ini` untouched.
                            """).format(importer=Config.Launcher.active_importer),
                        ),
                    ),
                ),
                SettingsSection(
                    label_text=L("launcher_settings_connection_section_label", "Connection"),
                    options=(
                        SettingsOption(
                            label_text=L("launcher_settings_github_token_label", "GitHub Token"),
                            widget=OptionWidget.INPUT_STR,
                            value_variable="Vars.Launcher.github_token",
                            input_button_text=L("launcher_settings_github_token_create_button", "Create..."),
                            input_button_command=lambda: webbrowser.open("https://github.com/settings/tokens"),
                            input_button_tooltip=L("launcher_settings_github_token_create_button_tooltip", "Open **GitHub Personal Access Token** creation webpage."),
                            tooltip=L("launcher_settings_github_token_entry_tooltip", """
                                Your **Personal Access Token** on **GitHub** (i.e. `ghp_f7gy3A4eQ97jfy2983mfZu2Hy93yf2P3d798`).
                                Allows to combat `GitHub API Requests Limit` error that usually happens with public proxies.
                                It is totally free and only requires GitHub registration.
                                To create new token:
                                1. Click `[?]` button to open token creation webpage.
                                2. Use `Generate new token (classic)` button.
                            """),
                        ),

                        SettingsOption(
                            label_text=L("launcher_settings_verify_ssl_checkbox", "Verify SSL"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Launcher.verify_ssl",
                            tooltip=L("launcher_settings_verify_ssl_checkbox_tooltip", """
                                <font color="red">⚠ Disable only if you trust your proxy or whatever else that breaks SSL. ⚠</font>
                                **Enabled**: Validate SLL certificates for GitHub downloads to keep you secure.
                                **Disabled**: Allow insecure connection vulnerable to man-in-middle attacks.
                            """)
                        ),
                    ),
                ),

                SettingsSection(
                    label_text=L("launcher_settings_proxy_section_label", "Proxy"),
                    options=(

                        SettingsOption(
                            label_text=L("launcher_settings_proxy_enable_checkbox", "Use Proxy"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Launcher.proxy.enable",
                            tooltip=L("launcher_settings_proxy_enable_checkbox_tooltip", """
                                Controls how launcher connects to GitHub to download packages.
                                **Enabled**: Use specified proxy server to access Internet.
                                **Disabled**: Use default system Internet connection settings.
                            """),
                        ),

                        SettingsOption(
                            label_text=L("launcher_settings_proxy_type_label", "Type"),
                            widget=OptionWidget.DROPDOWN,
                            value_variable="Vars.Launcher.proxy.type",
                            dropdown_values=ProxyType,
                            tooltip=L("launcher_settings_proxy_type_option_menu_tooltip", """
                                * **{launcher_settings_proxy_type_https}**: Good old proxy protocol. Offers best security.
                                * **{launcher_settings_proxy_type_socks5}**: Newer and less secure, but excels at bypassing firewalls.
                            """),
                            enabled_if=Condition(
                                variables=("Vars.Launcher.proxy.enable",),
                                predicate=lambda: Vars.Launcher.proxy.enable.get(),
                            ),
                        ),

                        SettingsOption(
                            label_text=L("launcher_settings_proxy_dns_checkbox", "Proxy DNS Via SOCKS5"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Launcher.proxy.proxy_dns_via_socks5",
                            tooltip=L("launcher_settings_proxy_dns_checkbox_tooltip", """
                                **Enabled**: Use SOCKS5 proxy connection to route DNS requests.
                                **Disabled**: DNS requests will be routed through your ISP.
                            """),
                            enabled_if=Condition(
                                variables=("Vars.Launcher.proxy.enable", "Vars.Launcher.proxy.type"),
                                predicate=lambda: bool(Vars.Launcher.proxy.enable.get()) and Vars.Launcher.proxy.type.get() == ProxyType.SOCKS5,
                            ),
                        ),

                        SettingsOption(
                            label_text=L("launcher_settings_proxy_host_label", "Host"),
                            widget=OptionWidget.INPUT_STR,
                            value_variable="Vars.Launcher.proxy.host",
                            on_value_update_command=self.post_process_proxy_host,
                            tooltip=L("launcher_settings_proxy_host_entry_tooltip",
                                "Proxy IP address (i.e. `123.12.1.231`) or domain name (i.e. `proxyprovider.com`)."
                            ),
                            enabled_if=Condition(
                                variables=("Vars.Launcher.proxy.enable",),
                                predicate=lambda: bool(Vars.Launcher.proxy.enable.get()),
                            ),
                        ),

                        SettingsOption(
                            label_text=L("launcher_settings_proxy_port_label", "Port"),
                            widget=OptionWidget.INPUT_STR,
                            value_variable="Vars.Launcher.proxy.port",
                            on_value_update_command=self.post_process_proxy_port,
                            tooltip=L("launcher_settings_proxy_port_entry_tooltip", "Proxy port (i.e. `1080`)."),
                            enabled_if=Condition(
                                variables=("Vars.Launcher.proxy.enable",),
                                predicate=lambda: bool(Vars.Launcher.proxy.enable.get()),
                            ),
                        ),

                        SettingsOption(
                            label_text=L("launcher_settings_proxy_credentials_checkbox", "Proxy Requires Password"),
                            widget=OptionWidget.CHECKBOX,
                            value_variable="Vars.Launcher.proxy.use_credentials",
                            tooltip=L("launcher_settings_proxy_credentials_checkbox_tooltip", """
                                **Enabled**: Use specified user name and password for the proxy server authentication.
                                **Disabled**: Do not use any credentials when accessing a proxy server.
                            """),
                            enabled_if=Condition(
                                variables=("Vars.Launcher.proxy.enable",),
                                predicate=lambda: bool(Vars.Launcher.proxy.enable.get()),
                            ),
                        ),

                        SettingsOption(
                            label_text=L("launcher_settings_proxy_user_label", "User"),
                            widget=OptionWidget.INPUT_STR,
                            value_variable="Vars.Launcher.proxy.user",
                            tooltip=L("launcher_settings_proxy_user_entry_tooltip", "User name provided by your proxy service."),
                            visible_if=Condition(
                                variables=("Vars.Launcher.proxy.enable", "Vars.Launcher.proxy.use_credentials"),
                                predicate=lambda: bool(Vars.Launcher.proxy.enable.get()) and bool(Vars.Launcher.proxy.use_credentials.get()),
                            ),
                        ),

                        SettingsOption(
                            label_text=L("launcher_settings_proxy_password_label", "Password"),
                            widget=OptionWidget.INPUT_STR,
                            value_variable="Vars.Launcher.proxy.password",
                            tooltip=L("launcher_settings_proxy_password_entry_tooltip", "Password provided by your proxy service."),
                            visible_if=Condition(
                                variables=("Vars.Launcher.proxy.enable", "Vars.Launcher.proxy.use_credentials"),
                                predicate=lambda: bool(Vars.Launcher.proxy.enable.get()) and bool(Vars.Launcher.proxy.use_credentials.get()),
                            ),
                        ),
                    ),
                ),
            ),
        )

    @staticmethod
    def detect_themes():
        values = ["Default"]
        values.extend([
            path.name
            for path in Paths.App.Themes.iterdir()
            if path.is_dir() and path.name != "Default"
        ])
        return values

    @staticmethod
    def toggle_theme_dev_mode(var: Variable, val: bool):
        Config.Config.Launcher.theme_dev_mode = val
        Events.Fire(Events.GUI.ToggleThemeDevMode(enabled=val))

    def update_theme(self, new_value: str):
        Events.Fire(Events.Application.CloseSettings(save=True))
        Events.Fire(Events.Application.Busy())
        self.after_idle(lambda: Events.Fire(Events.GUI.ReloadGUI(reload_theme=True)))
        self.after_idle(lambda: Events.Fire(Events.Application.OpenSettings(tab_name="LAUNCHER_TAB")))
        self.after_idle(lambda: Events.Fire(Events.Application.Ready()))

    @staticmethod
    def post_process_proxy_host(var, value):
        value = value.strip()

        if not value:
            var.set("")
            return

        scheme = ""
        if "http" not in value:
            if len(re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})").findall(value)) == 1:
                scheme = "tcp://"
            else:
                scheme = "https://"

        result = urlparse(scheme+value)

        if result.hostname is not None:
            var.set(result.hostname)

        if result.port is not None:
            Vars.Launcher.proxy.port.set(result.port)

    @staticmethod
    def post_process_proxy_port(var, value):
        value = value.strip()
        if not value:
            var.set("")
            return
        for part in reversed(value.split(":")):
            if not part:
                continue
            result = re.compile(r"(\d+)").findall(part)
            if len(result) > 0:
                var.set(result[-1])
                return
        var.set("")
