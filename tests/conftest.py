"""Fixtures for Private Repo Loader tests."""

import os
import sys

import pytest

# Make custom_components importable for all tests
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)

# Override _auth_url so file:// URLs work in tests
from custom_components.private_repo_loader import loader  # noqa: E402

loader._auth_url = lambda url, token: url


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    from unittest.mock import MagicMock, AsyncMock

    hass = MagicMock()
    hass.config.path = lambda x: f"/tmp/test_config/{x}"
    hass.is_running = True
    hass.async_create_task = lambda x: x
    hass.async_add_executor_job = AsyncMock()
    hass.bus.async_listen_once = MagicMock()
    hass.services.async_register = MagicMock()
    hass.services.has_service = MagicMock(return_value=False)
    hass.services.async_remove = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_reload = AsyncMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    from unittest.mock import MagicMock

    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.options = {
        "token": "test_token",
        "repos": [],
    }
    entry.async_on_unload = MagicMock()
    return entry
