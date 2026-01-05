"""Tests for the Private Repo Loader integration setup."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.private_repo_loader import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.private_repo_loader.const import (
    DOMAIN,
    SERVICE_SYNC_NOW,
    SERVICE_RELOAD_REPOS,
    CONF_REPO,
    CONF_SLUG,
    CONF_BRANCH,
    CONF_TOKEN,
    CONF_POLL_INTERVAL,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.config.path = lambda x: f"/tmp/test_config/{x}"
    hass.is_running = True
    hass.bus.async_listen_once = MagicMock()
    hass.services.async_register = MagicMock()
    hass.services.has_service = MagicMock(return_value=False)
    hass.services.async_remove = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_reload = AsyncMock()
    hass.config_entries.async_update_entry = MagicMock()
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry for a repository."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_REPO: "https://github.com/owner/repo",
        CONF_SLUG: "test_repo",
        CONF_BRANCH: "main",
        CONF_TOKEN: "test_token",
    }
    entry.options = {
        CONF_BRANCH: "main",
        CONF_TOKEN: "test_token",
        CONF_POLL_INTERVAL: 1,
    }
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock()
    return entry


@pytest.mark.asyncio
async def test_async_setup():
    """Test that async_setup returns True."""
    hass = MagicMock()
    result = await async_setup(hass, {})
    assert result is True


@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass, mock_config_entry):
    """Test setting up the integration from config entry."""
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    with patch(
        "custom_components.private_repo_loader.coordinator.PrivateRepoCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.current_poll_interval = 1
        mock_coordinator_class.return_value = mock_coordinator

        result = await async_setup_entry(mock_hass, mock_config_entry)

        assert result is True
        mock_hass.services.async_register.assert_called()
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_registers_services(mock_hass, mock_config_entry):
    """Test that services are registered."""
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    with patch(
        "custom_components.private_repo_loader.coordinator.PrivateRepoCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.current_poll_interval = 1
        mock_coordinator_class.return_value = mock_coordinator

        await async_setup_entry(mock_hass, mock_config_entry)

        # Check that both services were registered
        call_args_list = mock_hass.services.async_register.call_args_list
        registered_services = [(call[0][0], call[0][1]) for call in call_args_list]
        assert (DOMAIN, SERVICE_SYNC_NOW) in registered_services
        assert (DOMAIN, SERVICE_RELOAD_REPOS) in registered_services


@pytest.mark.asyncio
async def test_async_unload_entry(mock_hass, mock_config_entry):
    """Test unloading the integration."""
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    mock_hass.config_entries.async_entries = MagicMock(
        return_value=[mock_config_entry]
    )  # Only this entry exists
    mock_hass.services.has_service = MagicMock(return_value=True)

    result = await async_unload_entry(mock_hass, mock_config_entry)

    assert result is True
    # Services should be removed since this is the last entry
    mock_hass.services.async_remove.assert_any_call(DOMAIN, SERVICE_SYNC_NOW)
    mock_hass.services.async_remove.assert_any_call(DOMAIN, SERVICE_RELOAD_REPOS)


@pytest.mark.asyncio
async def test_async_unload_entry_keeps_services_with_other_entries(
    mock_hass, mock_config_entry
):
    """Test that services are kept if there are other entries."""
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    # Two entries exist
    mock_hass.config_entries.async_entries = MagicMock(
        return_value=[mock_config_entry, MagicMock()]
    )

    result = await async_unload_entry(mock_hass, mock_config_entry)

    assert result is True
    mock_hass.services.async_remove.assert_not_called()
