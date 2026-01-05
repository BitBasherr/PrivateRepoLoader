"""Tests for the update entity."""

from unittest.mock import MagicMock, AsyncMock

import pytest

from custom_components.private_repo_loader.update import RepoUpdateEntity
from custom_components.private_repo_loader.const import DOMAIN, CONF_REPO, CONF_SLUG


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "status": "unchanged",
        "commit_sha": "abc123def456",
        "has_changes": False,
    }
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


class TestRepoUpdateEntity:
    """Test the RepoUpdateEntity class."""

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique ID generation."""
        entity = RepoUpdateEntity(mock_coordinator, mock_entry)
        assert entity.unique_id == "test_entry_id_update"

    def test_name(self, mock_coordinator, mock_entry):
        """Test entity name."""
        entity = RepoUpdateEntity(mock_coordinator, mock_entry)
        assert entity.name == "test_repo Update"

    def test_device_info(self, mock_coordinator, mock_entry):
        """Test device info."""
        entity = RepoUpdateEntity(mock_coordinator, mock_entry)
        device_info = entity.device_info
        assert (DOMAIN, "test_entry_id") in device_info["identifiers"]
        assert device_info["name"] == "Private Repo: test_repo"

    def test_installed_version_from_coordinator(self, mock_coordinator, mock_entry):
        """Test installed version from coordinator data."""
        entity = RepoUpdateEntity(mock_coordinator, mock_entry)
        # Set up hass mock to avoid RuntimeError
        entity.hass = MagicMock()
        entity.async_write_ha_state = MagicMock()

        # Trigger coordinator update handling
        entity._handle_coordinator_update()
        assert entity.installed_version == "abc123de"  # Short SHA

    def test_pending_update_on_clone(self, mock_coordinator, mock_entry):
        """Test pending update is set on clone."""
        mock_coordinator.data = {
            "status": "cloned",
            "commit_sha": "newsha12345678",
            "has_changes": True,
        }
        entity = RepoUpdateEntity(mock_coordinator, mock_entry)
        # Set up hass mock to avoid RuntimeError
        entity.hass = MagicMock()
        entity.async_write_ha_state = MagicMock()

        entity._handle_coordinator_update()

        assert entity._pending_update is True
        assert entity.latest_version == "newsha12"

    def test_pending_update_on_update(self, mock_coordinator, mock_entry):
        """Test pending update is set on update."""
        entity = RepoUpdateEntity(mock_coordinator, mock_entry)
        # Set up hass mock to avoid RuntimeError
        entity.hass = MagicMock()
        entity.async_write_ha_state = MagicMock()

        # First, set an initial version
        mock_coordinator.data = {
            "status": "unchanged",
            "commit_sha": "oldsha1234",
            "has_changes": False,
        }
        entity._handle_coordinator_update()

        # Then simulate an update
        mock_coordinator.data = {
            "status": "updated",
            "commit_sha": "newsha5678",
            "has_changes": True,
        }
        entity._handle_coordinator_update()

        assert entity._pending_update is True
        assert entity.latest_version == "newsha56"

    def test_release_summary_when_pending(self, mock_coordinator, mock_entry):
        """Test release summary shows when update is pending."""
        mock_coordinator.data = {
            "status": "updated",
            "commit_sha": "newsha",
            "has_changes": True,
        }
        entity = RepoUpdateEntity(mock_coordinator, mock_entry)
        # Set up hass mock to avoid RuntimeError
        entity.hass = MagicMock()
        entity.async_write_ha_state = MagicMock()

        entity._handle_coordinator_update()

        assert entity.release_summary is not None
        assert "Install" in entity.release_summary or "restart" in entity.release_summary.lower()

    def test_release_url(self, mock_coordinator, mock_entry):
        """Test release URL returns repo URL."""
        entity = RepoUpdateEntity(mock_coordinator, mock_entry)
        assert entity.release_url == "https://github.com/owner/repo"

    @pytest.mark.asyncio
    async def test_install_clears_pending_and_restarts(self, mock_coordinator, mock_entry):
        """Test install clears pending update and triggers restart."""
        mock_coordinator.data = {
            "status": "updated",
            "commit_sha": "newsha",
            "has_changes": True,
        }
        entity = RepoUpdateEntity(mock_coordinator, mock_entry)

        # Mock hass
        entity.hass = MagicMock()
        entity.hass.services.async_call = AsyncMock()
        entity.async_write_ha_state = MagicMock()

        # Trigger the update to set pending state
        entity._handle_coordinator_update()

        await entity.async_install(None, False)

        assert entity._pending_update is False
        entity.hass.services.async_call.assert_called_once_with(
            "homeassistant",
            "restart",
            blocking=False,
        )
