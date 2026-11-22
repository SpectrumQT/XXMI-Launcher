from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "xxmi_launcher"))

from core.utils.ini_handler import IniHandler, IniHandlerSettings  # noqa: E402
from core.mcp_config import apply_mcp_ini_setting  # noqa: E402


class MCPSettingTests(unittest.TestCase):
    def test_supported_xxmi_dll_gets_mcp_section_enabled(self):
        ini = IniHandler(
            IniHandlerSettings(),
            "[System]\ndll_initialization_delay = 0\n",
        )

        apply_mcp_ini_setting(ini, "1.3.3", True)

        self.assertIn("[MCP]\nenabled = 1\n", ini.to_string())

    def test_disabling_mcp_persists_enabled_zero(self):
        ini = IniHandler(
            IniHandlerSettings(),
            "[MCP]\nenabled = 1\n",
        )

        apply_mcp_ini_setting(ini, "1.3.3", False)

        self.assertIn("[MCP]\nenabled = 0\n", ini.to_string())

    def test_older_xxmi_dll_does_not_receive_mcp_section(self):
        source = "[System]\ndll_initialization_delay = 0\n"
        ini = IniHandler(IniHandlerSettings(), source)

        apply_mcp_ini_setting(ini, "1.2.0", True)

        self.assertNotIn("[MCP]", ini.to_string())


if __name__ == "__main__":
    unittest.main()
