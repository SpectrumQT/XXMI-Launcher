"""Shared pytest fixtures and configuration."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config_dir(temp_dir):
    """Create a mock configuration directory."""
    config_dir = temp_dir / "config"
    config_dir.mkdir(exist_ok=True)
    return config_dir


@pytest.fixture
def mock_app_config():
    """Create a mock application configuration."""
    return {
        "general": {
            "theme": "dark",
            "language": "en",
            "auto_update": True,
            "show_notifications": True,
        },
        "paths": {
            "game_path": "C:\\Games\\TestGame",
            "mods_path": "C:\\Games\\TestGame\\Mods",
            "backup_path": "C:\\Games\\TestGame\\Backups",
        },
        "launcher": {
            "minimize_to_tray": False,
            "start_with_windows": False,
            "check_updates_on_start": True,
        },
    }


@pytest.fixture
def mock_game_info():
    """Create mock game information."""
    return {
        "name": "Test Game",
        "version": "1.0.0",
        "executable": "game.exe",
        "installed": True,
        "path": "C:\\Games\\TestGame",
    }


@pytest.fixture
def mock_mod_info():
    """Create mock mod information."""
    return {
        "id": "test-mod-001",
        "name": "Test Mod",
        "version": "1.2.3",
        "author": "Test Author",
        "description": "A test mod for testing",
        "enabled": True,
        "files": ["mod.dll", "config.ini"],
    }


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for network tests."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.text = '{"status": "success"}'
        mock_response.content = b'{"status": "success"}'
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success"
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests."""
    # This fixture runs automatically before each test
    # Add any singleton reset logic here as needed
    yield


@pytest.fixture
def mock_window():
    """Create a mock GUI window for testing GUI components."""
    window = Mock()
    window.winfo_x.return_value = 100
    window.winfo_y.return_value = 100
    window.winfo_width.return_value = 800
    window.winfo_height.return_value = 600
    window.title = Mock()
    window.geometry = Mock()
    window.mainloop = Mock()
    window.destroy = Mock()
    return window


@pytest.fixture
def clean_environment():
    """Ensure a clean test environment."""
    # Store original environment
    original_env = os.environ.copy()
    
    # Clear specific env vars that might affect tests
    test_env_vars = [
        'XXMI_CONFIG_PATH',
        'XXMI_LOG_LEVEL',
        'XXMI_DEBUG',
    ]
    
    for var in test_env_vars:
        os.environ.pop(var, None)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_platform_system():
    """Mock platform.system for cross-platform tests."""
    with patch('platform.system') as mock_system:
        mock_system.return_value = 'Windows'
        yield mock_system