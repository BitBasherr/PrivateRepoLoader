"""Private Repo Loader – keep private GitHub repos in sync & reload HACS."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from pathlib import Path
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    LOGGER_NAME,
    CONF_REPOS,
)
from .loader import sync_repo

_LOGGER: Final = logging.getLogger(LOGGER_NAME)
SCAN_INTERVAL: Final = timedelta(hours=6)

# ────────────────────────────────────────────────────────────────────────────────
async def async_setup(hass: HomeAssistant, _yaml) -> bool:
    """Set up the integration (nothing to do at YAML level)."""
    hass.data.setdefault(DOMAIN, {})
    return True


# Helpers ────────────────────────────────────────────────────────────────────────
@callback
def _dest_root(hass: HomeAssistant) -> Path:
    """Return the folder where repos are checked out."""
    return Path(hass.config.path("custom_components"))


async def _sync_all(hass: HomeAssistant, repos: list[dict]) -> None:
    """Clone/update every configured repo, then reload HACS if present."""
    root = _dest_root(hass)
    await asyncio.gather(
        *[
            hass.async_add_executor_job(sync_repo, root, repo_cfg)
            for repo_cfg in repos
        ]
    )

    if "hacs" in hass.config.components:
        for entry in hass.config_entries.async_entries("hacs"):
            _LOGGER.debug("Reloading HACS after repo sync")
            await hass.config_entries.async_reload(entry.entry_id)


# Config-entry lifecycle ────────────────────────────────────────────────────────
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Start periodic sync and register a manual `refresh` service."""
    async def _run(_=None) -> None:
        await _sync_all(hass, entry.options.get(CONF_REPOS, []))

    # 1) run once at HA-start
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _run)

    # 2) schedule periodic runs
    unsub = async_track_time_interval(hass, _run, SCAN_INTERVAL)
    entry.async_on_unload(unsub)

    # 3) manual service
    if not hass.services.has_service(DOMAIN, "refresh"):
        async def _svc(_: ServiceCall) -> None:
            await _run()
        hass.services.async_register(DOMAIN, "refresh", _svc)

    _LOGGER.info("Private Repo Loader set up (entry_id=%s)", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Clean up when the entry is removed."""
    await hass.services.async_remove(DOMAIN, "refresh")
    _LOGGER.info("Private Repo Loader removed (entry_id=%s)", entry.entry_id)
    return True
