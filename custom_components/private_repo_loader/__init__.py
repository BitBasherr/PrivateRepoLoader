"""Private Repo Loader – keep private GitHub repos in sync & refresh HACS."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback  # ← ensure `callback` is imported
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    CONF_REPOS,
    SERVICE_SYNC_NOW,
    DISPATCHER_SYNC_DONE,
)
from .loader import sync_repo

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=6)
PLATFORMS = [Platform.SENSOR]


async def async_setup(*_) -> bool:
    """No YAML setup required."""
    return True


@callback
def _dest_root(hass: HomeAssistant) -> Path:
    """Return folder where repos are cloned."""
    return Path(hass.config.path("custom_components"))


async def _sync_all(hass: HomeAssistant, repos: list[dict]) -> None:
    """Clone/pull every repo, log failures, then notify sensor."""
    root = _dest_root(hass)

    results = await asyncio.gather(
        *[hass.async_add_executor_job(sync_repo, root, cfg) for cfg in repos],
        return_exceptions=True,
    )
    for cfg, res in zip(repos, results, strict=False):
        if isinstance(res, Exception):
            _LOGGER.error("Repo %s failed: %s", cfg.get("repository"), res)

    # Fire sensor update
    async_dispatcher_send(hass, DISPATCHER_SYNC_DONE, datetime.now())

    # Reload HACS if installed
    for entry in hass.config_entries.async_entries("hacs"):
        _LOGGER.debug("Reloading HACS after repo sync")
        await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Start sync loop, register service, and load sensor platform."""
    async def _run(_=None):
        await _sync_all(hass, entry.options.get(CONF_REPOS, []))

    # Initial run
    if hass.is_running:
        hass.async_create_task(_run())
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _run)

    # Schedule periodic
    entry.async_on_unload(
        async_track_time_interval(hass, _run, SCAN_INTERVAL)
    )

    # (Re)register sync service
    async def _svc(_: ServiceCall):
        await _run()

    try:
        hass.services.async_register(DOMAIN, SERVICE_SYNC_NOW, _svc)
    except ValueError:
        pass

    # Forward to sensor
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload sensor and remove service if this was the last entry."""
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if not hass.config_entries.async_entries(DOMAIN):
        if hass.services.has_service(DOMAIN, SERVICE_SYNC_NOW):
            hass.services.async_remove(DOMAIN, SERVICE_SYNC_NOW)

    return True
