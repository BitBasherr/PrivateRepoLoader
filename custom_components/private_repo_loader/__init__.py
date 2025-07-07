"""Private Repo Loader – sync private GitHub repos & refresh HACS."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    CONF_REPOS,
    SERVICE_SYNC_NOW,
    DISPATCHER_SYNC_DONE,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=6)
PLATFORMS = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """No YAML setup required."""
    return True


@callback
def _dest_root(hass: HomeAssistant) -> Path:
    """Return path to the custom_components folder."""
    return Path(hass.config.path("custom_components"))


async def _sync_all(
    hass: HomeAssistant, repos: list[dict[str, Any]]
) -> None:
    """
    Clone/pull each repo, log errors, send update, reload HACS.

    GitPython is imported inside the executor call so import is
    deferred and not blocking.
    """
    root = _dest_root(hass)

    def _run_one(cfg: dict[str, Any]) -> str:
        from .loader import sync_repo  # noqa: F811
        return sync_repo(root, cfg)

    tasks = [
        hass.async_add_executor_job(_run_one, cfg)
        for cfg in repos
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for cfg, res in zip(repos, results, strict=False):
        if isinstance(res, Exception):
            _LOGGER.error("Repo %s failed: %s",
                          cfg.get("repository"), res)

    async_dispatcher_send(
        hass, DISPATCHER_SYNC_DONE, datetime.now()
    )

    for entry in hass.config_entries.async_entries("hacs"):
        _LOGGER.debug("Reloading HACS after sync")
        await hass.config_entries.async_reload(
            entry.entry_id
        )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Start sync loop, register service, and forward to sensor."""
    async def _run(_=None) -> None:
        await _sync_all(hass, entry.options.get(CONF_REPOS, []))

    if hass.is_running:
        hass.async_create_task(_run())
    else:
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED, _run
        )

    entry.async_on_unload(
        async_track_time_interval(hass, _run, SCAN_INTERVAL)
    )

    async def _svc(_: ServiceCall) -> None:
        await _run()

    try:
        hass.services.async_register(
            DOMAIN, SERVICE_SYNC_NOW, _svc
        )
    except ValueError:
        pass

    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload sensor and remove service if this was the last entry."""
    await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if not hass.config_entries.async_entries(DOMAIN):
        if hass.services.has_service(
            DOMAIN, SERVICE_SYNC_NOW
        ):
            hass.services.async_remove(
                DOMAIN, SERVICE_SYNC_NOW
            )

    return True