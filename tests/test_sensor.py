"""Tests for the Private Repo Loader sensor entities."""

from unittest.mock import MagicMock

import pytest

from custom_components.private_repo_loader.sensor import (
    RepoStatusSensor,
    RepoLastSyncSensor,
    RepoLastChangedSensor,
    RepoPollIntervalSensor,
    async_setup_entry,
)
from custom_components.private_repo_loader.const import (
    CONF_REPO,
    CONF_SLUG,
    CONF_BRANCH,
    CONF_TOKEN,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "status": "updated",
        "has_changes": True,
        "commit_sha": "abc123def456",
        "last_checked": "2024-01-01T12:00:00",
        "last_changed": "2024-01-01T12:00:00",
        "slug": "test_repo",
        "error": None,
    }
    coordinator.current_poll_interval = 5
    return coordinator


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_REPO: "https://github.com/owner/repo",
        CONF_SLUG: "test_repo",
        CONF_BRANCH: "main",
        CONF_TOKEN: "",
    }
    return entry


class TestRepoStatusSensor:
    """Test the RepoStatusSensor entity."""

    def test_native_value(self, mock_coordinator, mock_entry):
        """Test native value returns status."""
        sensor = RepoStatusSensor(mock_coordinator, mock_entry)
        assert sensor.native_value == "updated"

    def test_native_value_pending(self, mock_coordinator, mock_entry):
        """Test native value returns pending when no data."""
        mock_coordinator.data = None
        sensor = RepoStatusSensor(mock_coordinator, mock_entry)
        assert sensor.native_value == "pending"

    def test_extra_state_attributes(self, mock_coordinator, mock_entry):
        """Test extra state attributes."""
        sensor = RepoStatusSensor(mock_coordinator, mock_entry)
        attrs = sensor.extra_state_attributes
        assert attrs["repository"] == "https://github.com/owner/repo"
        assert attrs["slug"] == "test_repo"
        assert attrs["commit_sha"] == "abc123def456"
        assert attrs["has_changes"] is True

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique ID format."""
        sensor = RepoStatusSensor(mock_coordinator, mock_entry)
        assert sensor.unique_id == "test_entry_id_status"


class TestRepoLastSyncSensor:
    """Test the RepoLastSyncSensor entity."""

    def test_native_value(self, mock_coordinator, mock_entry):
        """Test native value returns last_checked."""
        sensor = RepoLastSyncSensor(mock_coordinator, mock_entry)
        assert sensor.native_value == "2024-01-01T12:00:00"

    def test_native_value_never(self, mock_coordinator, mock_entry):
        """Test native value returns Never when no data."""
        mock_coordinator.data = None
        sensor = RepoLastSyncSensor(mock_coordinator, mock_entry)
        assert sensor.native_value == "Never"

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique ID format."""
        sensor = RepoLastSyncSensor(mock_coordinator, mock_entry)
        assert sensor.unique_id == "test_entry_id_last_sync"


class TestRepoLastChangedSensor:
    """Test the RepoLastChangedSensor entity."""

    def test_native_value(self, mock_coordinator, mock_entry):
        """Test native value returns last_changed."""
        sensor = RepoLastChangedSensor(mock_coordinator, mock_entry)
        assert sensor.native_value == "2024-01-01T12:00:00"

    def test_native_value_never(self, mock_coordinator, mock_entry):
        """Test native value returns Never when no data."""
        mock_coordinator.data = None
        sensor = RepoLastChangedSensor(mock_coordinator, mock_entry)
        assert sensor.native_value == "Never"

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique ID format."""
        sensor = RepoLastChangedSensor(mock_coordinator, mock_entry)
        assert sensor.unique_id == "test_entry_id_last_changed"


class TestRepoPollIntervalSensor:
    """Test the RepoPollIntervalSensor entity."""

    def test_native_value(self, mock_coordinator, mock_entry):
        """Test native value returns poll interval."""
        sensor = RepoPollIntervalSensor(mock_coordinator, mock_entry)
        assert sensor.native_value == 5

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique ID format."""
        sensor = RepoPollIntervalSensor(mock_coordinator, mock_entry)
        assert sensor.unique_id == "test_entry_id_poll_interval"


class TestAsyncSetupEntry:
    """Test the async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_creates_entities(self, mock_coordinator, mock_entry):
        """Test that setup creates all expected entities."""
        mock_entry.runtime_data = mock_coordinator
        mock_hass = MagicMock()
        entities_added = []

        def add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(mock_hass, mock_entry, add_entities)

        # Should create 4 entities
        assert len(entities_added) == 4
        entity_types = [type(e).__name__ for e in entities_added]
        assert "RepoStatusSensor" in entity_types
        assert "RepoLastSyncSensor" in entity_types
        assert "RepoLastChangedSensor" in entity_types
        assert "RepoPollIntervalSensor" in entity_types
