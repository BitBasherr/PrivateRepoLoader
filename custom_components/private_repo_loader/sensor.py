"""Diagnostic sensor – timestamp of last successful repo sync."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, DISPATCHER_SYNC_DONE
from homeassistant.config_entries import ConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Callable[[list[SensorEntity]], None],
) -> None:
    """Set up the LastSyncSensor."""
    async_add_entities([LastSyncSensor()])


class LastSyncSensor(SensorEntity):
    """Reports the most recent successful sync time."""

    _attr_unique_id = f"{DOMAIN}_last_sync"
    _attr_name = "Private Repo Loader – Last Sync"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_value = "Never"

    def __init__(self) -> None:
        self._unsub: Callable[[], None] | None = None
        self._pending: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Register dispatcher listener after entity is ready."""
        self._unsub = async_dispatcher_connect(
            self.hass, DISPATCHER_SYNC_DONE, self._handle_sync
        )
        if self._pending:
            self._set_value(self._pending)
            self._pending = None

    async def async_will_remove_from_hass(self) -> None:
        """Tidy up the listener when the entity is removed."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_sync(self, when: datetime) -> None:
        """Update sensor value when sync is done."""
        if self.hass is None:
            self._pending = when
            return
        self._set_value(when)

    @callback
    def _set_value(self, when: datetime) -> None:
        self._attr_native_value = when.isoformat(timespec="seconds")
        self.async_write_ha_state()