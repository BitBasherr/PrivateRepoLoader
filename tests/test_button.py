"""Tests for the button entities."""

from unittest.mock import MagicMock, AsyncMock

import pytest

from custom_components.private_repo_loader.button import RepoSyncButton, RestartHAButton
from custom_components.private_repo_loader.const import DOMAIN, CONF_REPO, CONF_SLUG


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_REPO: "https://github.com/owner/repo",
        CONF_SLUG: "test_repo",
    }
    return entry


class TestRepoSyncButton:
    """Test the RepoSyncButton class."""

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique ID generation."""
        button = RepoSyncButton(mock_coordinator, mock_entry)
        assert button.unique_id == "test_entry_id_sync"

    def test_name(self, mock_coordinator, mock_entry):
        """Test button name."""
        button = RepoSyncButton(mock_coordinator, mock_entry)
        assert button.name == "test_repo Sync Now"

    def test_icon(self, mock_coordinator, mock_entry):
        """Test button icon."""
        button = RepoSyncButton(mock_coordinator, mock_entry)
        assert button.icon == "mdi:sync"

    def test_device_info(self, mock_coordinator, mock_entry):
        """Test device info."""
        button = RepoSyncButton(mock_coordinator, mock_entry)
        device_info = button.device_info
        assert (DOMAIN, "test_entry_id") in device_info["identifiers"]
        assert device_info["name"] == "Private Repo: test_repo"

    @pytest.mark.asyncio
    async def test_press_triggers_refresh(self, mock_coordinator, mock_entry):
        """Test that pressing the button triggers coordinator refresh."""
        button = RepoSyncButton(mock_coordinator, mock_entry)
        await button.async_press()

        mock_coordinator.async_request_refresh.assert_called_once()


class TestRestartHAButton:
    """Test the RestartHAButton class."""

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique ID generation."""
        button = RestartHAButton(mock_coordinator, mock_entry)
        assert button.unique_id == "test_entry_id_restart"

    def test_name(self, mock_coordinator, mock_entry):
        """Test button name."""
        button = RestartHAButton(mock_coordinator, mock_entry)
        assert button.name == "test_repo Restart HA"

    def test_icon(self, mock_coordinator, mock_entry):
        """Test button icon."""
        button = RestartHAButton(mock_coordinator, mock_entry)
        assert button.icon == "mdi:restart"

    def test_device_info(self, mock_coordinator, mock_entry):
        """Test device info."""
        button = RestartHAButton(mock_coordinator, mock_entry)
        device_info = button.device_info
        assert (DOMAIN, "test_entry_id") in device_info["identifiers"]
        assert device_info["name"] == "Private Repo: test_repo"

    @pytest.mark.asyncio
    async def test_press_triggers_restart(self, mock_coordinator, mock_entry):
        """Test that pressing the button triggers HA restart."""
        button = RestartHAButton(mock_coordinator, mock_entry)

        # Mock hass
        button.hass = MagicMock()
        button.hass.services.async_call = AsyncMock()

        await button.async_press()

        button.hass.services.async_call.assert_called_once_with(
            "homeassistant",
            "restart",
            blocking=False,
        )
