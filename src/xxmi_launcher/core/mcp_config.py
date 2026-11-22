import re


MIN_MCP_XXMI_DLL_VERSION = (1, 3, 3)


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version)[:3])


def apply_mcp_ini_setting(
    ini,
    xxmi_dll_version: str | None,
    enabled: bool,
) -> None:
    if not xxmi_dll_version:
        return
    if _version_tuple(xxmi_dll_version) < MIN_MCP_XXMI_DLL_VERSION:
        return
    ini.set_option("MCP", "enabled", 1 if enabled else 0)
