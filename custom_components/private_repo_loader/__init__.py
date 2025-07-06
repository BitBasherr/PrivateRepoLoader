"""Private Repo Loader – keeps private GitHub repos in sync & reloads HACS."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import (          # ← pull constants from const.py
    DOMAIN,
    CONF_TOKEN,
    CONF_REPO,
    CONF_SLUG,
    CONF_BRANCH,
)
from .loader import sync_repo  # ← loader only supplies the function

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=6)

PLATFORMS: list[str] = []  # helper integration – no entities

# ------------------------------------------------------------------
async def async_setup(hass: HomeAssistant, _yaml) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


# ------------------------------------------------------------------
@callback
def _dest_root(hass: HomeAssistant) -> Path:
    return Path(hass.config.path("custom_components"))


async def _sync_all(hass: HomeAssistant, repos: list[dict]) -> None:
    root = _dest_root(hass)
    await asyncio.gather(
        *[
            hass.async_add_executor_job(sync_repo, root, repo_cfg)
            for repo_cfg in repos
        ]
    )
    if "hacs" in hass.config.components:
        await hass.services.async_call("hacs", "reload", blocking=False)


# ------------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN][entry.entry_id] = entry

    async def _periodic(_now=None):
        await _sync_all(hass, entry.options.get("repos", []))

    # run once after HA is started
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _periodic)

    # then every 6 h
    unsub = async_track_time_interval(hass, _periodic, SCAN_INTERVAL)
    entry.async_on_unload(unsub)

    # manual refresh
    async def _service(call: ServiceCall):
        await _periodic()

    if not hass.services.has_service(DOMAIN, "refresh"):
        hass.services.async_register(DOMAIN, "refresh", _service)

    return True


# ------------------------------------------------------------------
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
