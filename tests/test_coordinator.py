"""Tests for the sliding scale polling coordinator."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from custom_components.private_repo_loader.coordinator import (
    PrivateRepoCoordinator,
    calculate_poll_interval,
)
from custom_components.private_repo_loader.const import (
    CONF_REPO,
    CONF_SLUG,
    CONF_BRANCH,
    CONF_TOKEN,
    CONF_POLL_INTERVAL,
    CONF_LAST_CHANGED,
    POLL_INTERVAL_1_DAY,
    POLL_INTERVAL_1_WEEK,
    POLL_INTERVAL_1_MONTH,
)


class TestCalculatePollInterval:
    """Test the calculate_poll_interval function."""

    def test_no_last_changed_returns_base(self):
        """Test that no last_changed returns base interval."""
        result = calculate_poll_interval(None, base_interval=1)
        assert result == 1

    def test_recent_change_returns_base(self):
        """Test that recent change returns base interval."""
        now = datetime.now()
        last_changed = now - timedelta(hours=1)
        result = calculate_poll_interval(last_changed, base_interval=1)
        assert result == 1

    def test_one_day_no_change(self):
        """Test that 1 day without change returns 5 min interval."""
        now = datetime.now()
        # 25 hours ago (just over 1 day)
        last_changed = now - timedelta(hours=25)
        result = calculate_poll_interval(last_changed, base_interval=1)
        assert result == POLL_INTERVAL_1_DAY

    def test_one_week_no_change(self):
        """Test that 1 week without change returns 30 min interval."""
        now = datetime.now()
        # 8 days ago
        last_changed = now - timedelta(days=8)
        result = calculate_poll_interval(last_changed, base_interval=1)
        assert result == POLL_INTERVAL_1_WEEK

    def test_one_month_no_change(self):
        """Test that 1 month without change returns 60 min interval."""
        now = datetime.now()
        # 31 days ago
        last_changed = now - timedelta(days=31)
        result = calculate_poll_interval(last_changed, base_interval=1)
        assert result == POLL_INTERVAL_1_MONTH

    def test_custom_base_interval(self):
        """Test that custom base interval is used."""
        now = datetime.now()
        last_changed = now - timedelta(hours=1)
        result = calculate_poll_interval(last_changed, base_interval=5)
        assert result == 5


class TestPrivateRepoCoordinator:
    """Test the PrivateRepoCoordinator class."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = MagicMock()
        hass.config.path = lambda x: f"/tmp/test_config/{x}"
        hass.async_add_executor_job = AsyncMock()
        hass.config_entries.async_update_entry = MagicMock()
        return hass

    @pytest.fixture
    def mock_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.data = {
            CONF_REPO: "https://github.com/owner/repo",
            CONF_SLUG: "test_repo",
            CONF_BRANCH: "main",
            CONF_TOKEN: "test_token",
        }
        entry.options = {
            CONF_POLL_INTERVAL: 1,
        }
        return entry

    def test_coordinator_initial_interval(self, mock_hass, mock_entry):
        """Test coordinator sets initial interval correctly."""
        coordinator = PrivateRepoCoordinator(mock_hass, mock_entry)
        assert coordinator.current_poll_interval == 1

    def test_coordinator_custom_poll_interval(self, mock_hass, mock_entry):
        """Test coordinator respects custom poll interval."""
        mock_entry.options = {CONF_POLL_INTERVAL: 10}
        coordinator = PrivateRepoCoordinator(mock_hass, mock_entry)
        assert coordinator.current_poll_interval == 10

    def test_coordinator_with_stored_last_changed(self, mock_hass, mock_entry):
        """Test coordinator loads stored last_changed."""
        # Set a timestamp from 2 days ago
        two_days_ago = datetime.now() - timedelta(days=2)
        mock_entry.data = {
            **mock_entry.data,
            CONF_LAST_CHANGED: two_days_ago.isoformat(),
        }
        coordinator = PrivateRepoCoordinator(mock_hass, mock_entry)
        # Should use 5 minute interval for 1 day+ without change
        assert coordinator.current_poll_interval == POLL_INTERVAL_1_DAY

    def test_coordinator_repo_slug(self, mock_hass, mock_entry):
        """Test coordinator returns correct repo slug."""
        coordinator = PrivateRepoCoordinator(mock_hass, mock_entry)
        assert coordinator.repo_slug == "test_repo"

    def test_coordinator_repo_url(self, mock_hass, mock_entry):
        """Test coordinator returns correct repo URL."""
        coordinator = PrivateRepoCoordinator(mock_hass, mock_entry)
        assert coordinator.repo_url == "https://github.com/owner/repo"

    @pytest.mark.asyncio
    async def test_coordinator_update_with_changes(self, mock_hass, mock_entry):
        """Test coordinator update when changes are detected."""
        coordinator = PrivateRepoCoordinator(mock_hass, mock_entry)

        with patch(
            "custom_components.private_repo_loader.coordinator.sync_repo_detailed"
        ):
            mock_result = MagicMock()
            mock_result.status = "updated"
            mock_result.has_changes = True
            mock_result.commit_sha = "abc123"
            mock_result.error = None
            mock_hass.async_add_executor_job.return_value = mock_result

            result = await coordinator._async_update_data()

            assert result["status"] == "updated"
            assert result["has_changes"] is True
            assert result["commit_sha"] == "abc123"
            assert "last_changed" in result

    @pytest.mark.asyncio
    async def test_coordinator_update_no_changes(self, mock_hass, mock_entry):
        """Test coordinator update when no changes are detected."""
        coordinator = PrivateRepoCoordinator(mock_hass, mock_entry)

        mock_result = MagicMock()
        mock_result.status = "unchanged"
        mock_result.has_changes = False
        mock_result.commit_sha = "abc123"
        mock_result.error = None
        mock_hass.async_add_executor_job.return_value = mock_result

        result = await coordinator._async_update_data()

        assert result["status"] == "unchanged"
        assert result["has_changes"] is False
