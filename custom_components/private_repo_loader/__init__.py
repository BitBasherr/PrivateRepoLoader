"""Private Repo Loader – keeps private GitHub repos in sync."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_REPO,
    CONF_SLUG,
    CONF_BRANCH,
)
from .loader import sync_repo

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=6)

PLATFORMS: list[str] = []  # helper → no entities or platforms

# -------------------------------------------------------------------
async def async_setup(hass: HomeAssistant, _yaml) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


# -------------------------------------------------------------------
@callback
def _dest_root(hass: HomeAssistant) -> Path:
    return Path(hass.config.path("custom_components"))


async def _sync_all(hass: HomeAssistant, repos: list[dict]) -> None:
    root = _dest_root(hass)
    loop = hass.async_add_executor_job
    await asyncio.gather(*[loop(sync_repo, root, r) for r in repos])
    if "hacs" in hass.config.components:
        await hass.services.async_call("hacs", "reload", blocking=False)


# -------------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Start periodic sync and register service."""
    hass.data[DOMAIN][entry.entry_id] = entry

    async def _periodic(_now=None):
        await _sync_all(hass, entry.options.get("repos", []))

    # First run after HA starts
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _periodic)

    # Then every 6 h
    unsub = async_track_time_interval(hass, _periodic, SCAN_INTERVAL)
    entry.async_on_unload(unsub)

    # Manual refresh service
    async def _svc(call: ServiceCall):
        await _periodic()

    if not hass.services.has_service(DOMAIN, "refresh"):
        hass.services.async_register(DOMAIN, "refresh", _svc)

    return True


# -------------------------------------------------------------------
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
