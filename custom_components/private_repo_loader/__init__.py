"""Entry point – schedules periodic sync & exposes 'sync_now' service."""
from __future__ import annotations
from datetime import timedelta
import asyncio
import logging

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, CONF_REPOS, CONF_PAT, SCAN_INTERVAL_SEC
from .loader import sync_repo

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, _config):
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    token: str = entry.options[CONF_PAT]
    repos: list[dict] = entry.options.get(CONF_REPOS, [])
    interval = timedelta(seconds=SCAN_INTERVAL_SEC)

    async def _sync(_now):
        for cfg in repos:
            await hass.async_add_executor_job(sync_repo, hass, cfg, token)

        # ask HACS to reload its local cache (non-blocking)
        if "hacs" in hass.config.components:
            await hass.services.async_call("hacs", "reload", blocking=False)

    # run once at startup
    hass.async_create_task(_sync(None))
    unsub = async_track_time_interval(hass, _sync, interval)
    entry.async_on_unload(unsub)

    # -------- manual trigger service (sync_now) ----------
    async def _svc(_call):
        await _sync(None)

    if not hass.services.has_service(DOMAIN, "sync_now"):
        hass.services.async_register(DOMAIN, "sync_now", _svc)

    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    return True
