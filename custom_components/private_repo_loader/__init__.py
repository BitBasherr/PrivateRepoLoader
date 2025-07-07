"""Private Repo Loader – sync private GitHub repos & refresh HACS."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path
import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, ServiceCall
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, CONF_REPOS, SERVICE_SYNC_NOW
from .loader import sync_repo

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=6)

# ────────────────────────────────────────────────────────────────
async def async_setup(*_) -> bool:
    """Nothing to configure via YAML."""
    return True


# ───────────────────────────── helpers ───────────────────────────
@callback
def _dest_root(hass: HomeAssistant) -> Path:
    """Return the folder where repos are checked out."""
    return Path(hass.config.path("custom_components"))


async def _sync_all(hass: HomeAssistant, repos: list[dict]) -> None:
    """Clone/pull every configured repo, then reload HACS."""
    root = _dest_root(hass)
    await asyncio.gather(
        *[hass.async_add_executor_job(sync_repo, root, cfg) for cfg in repos]
    )

    # Force HACS to rescan
    hacs_entries = hass.config_entries.async_entries("hacs")
    if hacs_entries:
        _LOGGER.debug("Reloading HACS after repo sync")
        await hass.config_entries.async_reload(hacs_entries[0].entry_id)


def _register_dummy_device(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Create a no-entities device so the integration always appears
    in the *Devices & Services* list without changing the filter.
    """
    dev_reg = dr.async_get(hass)
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "private_repo_loader")},
        manufacturer="BitBasherr",
        name="Private Repo Loader",
        model="Git-Sync Helper",
    )


# ────────────────────── config-entry life-cycle ──────────────────
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Kick off periodic sync, expose service, register device."""
    _register_dummy_device(hass, entry)  # <── NEW

    async def _run(_=None) -> None:
        await _sync_all(hass, entry.options.get(CONF_REPOS, []))

    # Initial run
    if hass.is_running:
        hass.async_create_task(_run())
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _run)

    # Periodic runs
    unsub_timer = async_track_time_interval(hass, _run, SCAN_INTERVAL)
    entry.async_on_unload(unsub_timer)

    # Manual service
    if not hass.services.has_service(DOMAIN, SERVICE_SYNC_NOW):

        async def _svc(_: ServiceCall) -> None:
            await _run()

        hass.services.async_register(DOMAIN, SERVICE_SYNC_NOW, _svc)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Clean up when the entry is removed."""
    # Remove service if last entry is gone
    if len(hass.config_entries.async_entries(DOMAIN)) == 1:
        if hass.services.has_service(DOMAIN, SERVICE_SYNC_NOW):
            hass.services.async_remove(DOMAIN, SERVICE_SYNC_NOW)
    return True
