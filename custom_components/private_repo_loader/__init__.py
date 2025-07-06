"""Private Repo Loader – sync private GitHub repos & refresh HACS."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path
import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    callback,
    ServiceCall,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DOMAIN,
    CONF_REPOS,
    SERVICE_SYNC_NOW,
)
from .loader import sync_repo

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=6)

PLATFORMS: list[str] = []      # no entities

# ────────────────────────────────────────────────────────────────
async def async_setup(_: HomeAssistant, __) -> bool:
    """Nothing to do in YAML."""
    return True

# ────────────────────────────────────────────────────────────────
@callback
def _dest_root(hass: HomeAssistant) -> Path:
    return Path(hass.config.path("custom_components"))


async def _sync_all(hass: HomeAssistant, repos: list[dict]) -> None:
    """Clone/pull every configured repo, then reload HACS."""
    root = _dest_root(hass)
    results = await asyncio.gather(
        *[
            hass.async_add_executor_job(sync_repo, root, repo_cfg)
            for repo_cfg in repos
        ],
        return_exceptions=True,
    )
    for cfg, res in zip(repos, results, strict=False):
        if isinstance(res, Exception):
            _LOGGER.error("Repo %s failed: %s", cfg.get("repository"), res)

    # reload HACS so it rescans custom_components
    hacs_entries = hass.config_entries.async_entries("hacs")
    if hacs_entries:
        await hass.config_entries.async_reload(hacs_entries[0].entry_id)
        _LOGGER.debug("HACS reloaded after repo sync")

# ────────────────────────────────────────────────────────────────
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create timers & services for a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry

    async def _periodic(_now=None):
        await _sync_all(hass, entry.options.get(CONF_REPOS, []))

    # first run (immediate if HA already started)
    if hass.is_running:
        hass.async_create_task(_periodic())
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _periodic)

    # schedule every 6 h
    unsub_timer = async_track_time_interval(hass, _periodic, SCAN_INTERVAL)
    entry.async_on_unload(unsub_timer)

    # manual “sync_now” service (register once globally)
    async def _service(call: ServiceCall):
        await _periodic()

    if not hass.services.has_service(DOMAIN, SERVICE_SYNC_NOW):
        hass.services.async_register(DOMAIN, SERVICE_SYNC_NOW, _service)

    return True

# ────────────────────────────────────────────────────────────────
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Clean up when the config-entry is removed."""
    hass.data[DOMAIN].pop(entry.entry_id, None)

    # remove service if no entries left
    if not hass.data[DOMAIN]:
        if hass.services.has_service(DOMAIN, SERVICE_SYNC_NOW):
            hass.services.async_remove(DOMAIN, SERVICE_SYNC_NOW)

    return True
