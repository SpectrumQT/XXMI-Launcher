from typing import Any, Self
from enum import Enum

from core.locale_manager import L


class ConfigEnum(Enum):
    @classmethod
    def from_config(cls, value: str) -> Self:
        return cls[value]

    def to_config(self) -> str:
        return self.name


class GameLaunch(ConfigEnum):
    DIRECT = L("general_settings_launch_direct", "Direct")
    STEAM = L("general_settings_launch_steam", "Steam")
    EPIC_GAMES = L("general_settings_launch_epic", "Epic Games")
    CUSTOM = L("general_settings_launch_custom", "Custom")
    MANUAL = L("general_settings_launch_manual", "Manual")


class StartMethod(ConfigEnum):
    NATIVE = L("general_settings_start_method_native", "Native")
    SHELL = L("general_settings_start_method_shell", "Shell")


class ProcessStartMethodLegacy(ConfigEnum):
    OPTION_REMOVED = "OPTION_REMOVED"
    NATIVE = "NATIVE"
    SHELL = "SHELL"
    MANUAL = "MANUAL"


class WindowMode(ConfigEnum):
    WINDOWED = L("general_settings_window_mode_windowed", "Windowed")
    BORDERLESS = L("general_settings_window_mode_borderless", "Borderless")
    FULLSCREEN = L("general_settings_window_mode_fullscreen", "Fullscreen")
    EXCLUSIVE_FULLSCREEN = L("general_settings_window_mode_exclusive_fullscreen", "Exclusive Fullscreen")


class ProcessPriority(ConfigEnum):
    LOW = L("general_settings_process_priority_low", "Low")
    BELOW_NORMAL = L("general_settings_process_priority_below_normal", "Below Normal")
    NORMAL = L("general_settings_process_priority_normal", "Normal")
    ABOVE_NORMAL = L("general_settings_process_priority_above_normal", "Above Normal")
    HIGH = L("general_settings_process_priority_high", "High")
    REALTIME = L("general_settings_process_priority_realtime", "Realtime")


class InjectMode(ConfigEnum):
    DIRECT = L("general_settings_inject_mode_direct", "Direct")
    HOOK = L("general_settings_inject_mode_hook", "Hook")
    SKIP = L("general_settings_inject_mode_skip", "Skip")


class InjectModeLegacy(ConfigEnum):
    OPTION_REMOVED = "OPTION_REMOVED"
    INJECT = "INJECT"
    HOOK = "HOOK"
    BYPASS = "BYPASS"


class UpdateChannel(ConfigEnum):
    AUTO = L("launcher_settings_update_channel_auto", "Auto")
    MSI = L("launcher_settings_update_channel_msi", "MSI")
    ZIP = L("launcher_settings_update_channel_zip", "ZIP")


class ProxyType(ConfigEnum):
    HTTPS = L("launcher_settings_proxy_type_https", "HTTPS")
    SOCKS5 = L("launcher_settings_proxy_type_socks5", "SOCKS5")


class InputDisableMode(ConfigEnum):
    MODS = L("importer_settings_input_disable_mode_mods", "Mods")
    ALL = L("importer_settings_input_disable_mode_all", "All")


class LogLevel(ConfigEnum):
    DISABLED = L("importer_settings_log_level_disabled", "Disabled")
    WARNING = L("importer_settings_log_level_warning", "Warning")
    INFO = L("importer_settings_log_level_info", "Info")
    DEBUG = L("importer_settings_log_level_debug", "Debug")
