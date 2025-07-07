"""Diagnostic sensor: shows last successful repo sync."""
from __future__ import annotations

from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, DISPATCHER_SYNC_DONE

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    async_add_entities([LastSyncSensor(hass)])


class LastSyncSensor(SensorEntity):
    """Reports the timestamp of the most recent successful sync."""

    _attr_unique_id = f"{DOMAIN}_last_sync"
    _attr_name = "Private Repo Loader – Last Sync"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_value = "Never"

    def __init__(self, hass: HomeAssistant) -> None:
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "private_repo_loader")},
            "manufacturer": "BitBasherr",
            "name": "Private Repo Loader",
            "model": "Git-Sync Helper",
        }
        async_dispatcher_connect(hass, DISPATCHER_SYNC_DONE, self._handle_sync)

    # ------------------------------------------------------------------
    def _handle_sync(self, when: datetime) -> None:
        self._attr_native_value = when.isoformat(timespec="seconds")
        self.async_write_ha_state()
