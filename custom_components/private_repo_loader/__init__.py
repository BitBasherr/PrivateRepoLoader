"""Private Repo Loader – keeps private GitHub repos in sync & reloads HACS."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN
from .loader import sync_repo                 # ← ONLY thing we import
                                            #   (no constants to avoid loops)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=6)
PLATFORMS: list[str] = []                    # helper – no entities


async def async_setup(hass: HomeAssistant, _yaml) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


@callback
def _dest_root(hass: HomeAssistant) -> Path:
    return Path(hass.config.path("custom_components"))


async def _sync_all(hass: HomeAssistant, repos: list[dict]) -> None:
    root = _dest_root(hass)
    await asyncio.gather(
        *[hass.async_add_executor_job(sync_repo, root, rcfg) for rcfg in repos]
    )
    if "hacs" in hass.config.components:
        await hass.services.async_call("hacs", "reload", blocking=False)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Starts the periodic sync + manual service for this config-entry."""
    async def _run(_=None):
        await _sync_all(hass, entry.options.get("repos", []))

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _run)
    unsub = async_track_time_interval(hass, _run, SCAN_INTERVAL)
    entry.async_on_unload(unsub)

    async def _svc(_: ServiceCall):  # manual “refresh”
        await _run()

    if not hass.services.has_service(DOMAIN, "refresh"):
        hass.services.async_register(DOMAIN, "refresh", _svc)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
