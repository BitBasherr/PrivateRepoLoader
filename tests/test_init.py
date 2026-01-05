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
)


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
        "custom_components.private_repo_loader.async_track_time_interval"
    ) as mock_track:
        mock_track.return_value = MagicMock()

        result = await async_setup_entry(mock_hass, mock_config_entry)

        assert result is True
        mock_hass.services.async_register.assert_called_once()
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_registers_service(mock_hass, mock_config_entry):
    """Test that the sync_now service is registered."""
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    with patch(
        "custom_components.private_repo_loader.async_track_time_interval"
    ) as mock_track:
        mock_track.return_value = MagicMock()

        await async_setup_entry(mock_hass, mock_config_entry)

        # Check service was registered with correct domain and name
        call_args = mock_hass.services.async_register.call_args
        assert call_args[0][0] == DOMAIN
        assert call_args[0][1] == SERVICE_SYNC_NOW


@pytest.mark.asyncio
async def test_async_unload_entry(mock_hass, mock_config_entry):
    """Test unloading the integration."""
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    mock_hass.config_entries.async_entries = MagicMock(return_value=[])
    mock_hass.services.has_service = MagicMock(return_value=True)

    result = await async_unload_entry(mock_hass, mock_config_entry)

    assert result is True
    mock_hass.services.async_remove.assert_called_once_with(DOMAIN, SERVICE_SYNC_NOW)


@pytest.mark.asyncio
async def test_async_unload_entry_keeps_service_with_other_entries(
    mock_hass, mock_config_entry
):
    """Test that service is kept if there are other entries."""
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    mock_hass.config_entries.async_entries = MagicMock(
        return_value=[MagicMock()]  # Other entry exists
    )

    result = await async_unload_entry(mock_hass, mock_config_entry)

    assert result is True
    mock_hass.services.async_remove.assert_not_called()
