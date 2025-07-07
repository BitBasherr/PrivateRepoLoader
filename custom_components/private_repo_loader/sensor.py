"""Diagnostic sensor – shows the timestamp of the last repo sync."""
from __future__ import annotations

from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, DISPATCHER_SYNC_DONE


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities
) -> None:
    async_add_entities([LastSyncSensor()])


class LastSyncSensor(SensorEntity):
    """Reports the most recent successful sync time."""

    _attr_unique_id = f"{DOMAIN}_last_sync"
    _attr_name = "Private Repo Loader – Last Sync"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_value = "Never"

    def __init__(self) -> None:
        self._unsub: callback | None = None
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "private_repo_loader")},
            "manufacturer": "BitBasherr",
            "name": "Private Repo Loader",
            "model": "Git-Sync Helper",
        }

    # ------------------------------------------------------------------
    async def async_added_to_hass(self) -> None:
        """Register dispatcher listener *after* the entity is ready."""
        self._unsub = async_dispatcher_connect(
            self.hass, DISPATCHER_SYNC_DONE, self._handle_sync
        )

    async def async_will_remove_from_hass(self) -> None:
        """Tidy up the listener when the entity is removed."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    # ------------------------------------------------------------------
    @callback
    def _handle_sync(self, when: datetime) -> None:
        """Update native value from dispatcher callback."""
        self._attr_native_value = when.isoformat(timespec="seconds")
        self.async_write_ha_state()
