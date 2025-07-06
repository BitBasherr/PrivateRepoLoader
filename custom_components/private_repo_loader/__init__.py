"""Private Repo Loader – let HACS install your own private repos."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import git
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    CONF_REPO,
    DATA_REPOS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = []  # no entities


# ------------------------------------------------------------------
#  Storage helpers
# ------------------------------------------------------------------
async def _async_get_storage(hass: HomeAssistant) -> dict[str, Any]:
    store = hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
    data = await store.async_load() or {DATA_REPOS: {}}
    return data


async def _async_save_storage(hass: HomeAssistant, data: dict[str, Any]) -> None:
    store = hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
    await store.async_save(data)


def _repo_slug(url: str) -> str:
    """Return <owner>/<repo> from any https/git@ URL."""
    return url.rstrip("/").removesuffix(".git").split("/")[-2] + "/" + url.rstrip("/").split("/")[-1].removesuffix(".git")


# ------------------------------------------------------------------
#  Core setup
# ------------------------------------------------------------------
async def async_setup(hass: HomeAssistant, yaml_config: ConfigType) -> bool:  # noqa: D401
    """YAML setup is supported but optional."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config-flow entry."""
    token: str = entry.data[CONF_TOKEN]
    url: str = entry.data[CONF_URL]

    # store in hass.data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        CONF_TOKEN: token,
        CONF_URL: url,
    }

    # persist list of repos + tokens (tokens encrypted by HA storage)
    data = await _async_get_storage(hass)
    data[DATA_REPOS][_repo_slug(url)] = {
        CONF_TOKEN: token,
        CONF_URL: url,
    }
    await _async_save_storage(hass, data)

    # ensure the repo is cloned on start-up
    await _async_clone_or_update(hass, token, url)

    # register service once (idempotent)
    if not hass.services.has_service(DOMAIN, "refresh"):
        hass.services.async_register(
            DOMAIN,
            "refresh",
            _service_refresh,
            schema=None,  # simple schema-less call → use service data
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove an entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)

    # remove from storage
    data = await _async_get_storage(hass)
    slug = _repo_slug(entry.data[CONF_URL])
    data[DATA_REPOS].pop(slug, None)
    await _async_save_storage(hass, data)
    return True


# ------------------------------------------------------------------
#  Git utilities
# ------------------------------------------------------------------
async def _async_clone_or_update(hass: HomeAssistant, token: str, url: str) -> None:
    """Clone or pull a private repo into custom_components."""
    slug = _repo_slug(url)
    dest: Path = Path(hass.config.path("custom_components")) / slug.split("/")[-1]

    # Build an authenticated URL  https://<token>@github.com/owner/repo.git
    auth_url = url.replace("https://", f"https://{token}@")

    def _git_task() -> str:
        if dest.exists():
            repo = git.Repo(dest)
            repo.remote().set_url(auth_url)
            repo.remote().pull()
            return "updated"
        git.Repo.clone_from(auth_url, dest)
        return "cloned"

    result = await hass.async_add_executor_job(_git_task)
    _LOGGER.info("PrivateRepoLoader %s %s", slug, result)

    # Ask HACS to reload repos (if HACS is present)
    if "hacs" in hass.config.components:
        hass.async_create_task(
            hass.services.async_call("hacs", "reload", {}, blocking=False)
        )


# ------------------------------------------------------------------
#  Service handler
# ------------------------------------------------------------------
async def _service_refresh(call: ServiceCall) -> None:
    """Refresh all registered private repos (or a single one)."""
    hass: HomeAssistant = call.hass
    slug: str | None = call.data.get("repo")  # optional owner/repo

    data = await _async_get_storage(hass)

    tasks = []
    for repo_slug, info in data[DATA_REPOS].items():
        if slug and slug != repo_slug:
            continue
        tasks.append(
            _async_clone_or_update(hass, info[CONF_TOKEN], info[CONF_URL])
        )

    if tasks:
        await asyncio.gather(*tasks)


# ------------------------------------------------------------------
#  On HA start-up, refresh everything once ( so repos added manually in
#  storage are cloned after a restore / re-install )
# ------------------------------------------------------------------
async def async_setup_after_start(hass: HomeAssistant) -> None:
    data = await _async_get_storage(hass)
    for repo_slug, info in data[DATA_REPOS].items():
        hass.async_create_task(
            _async_clone_or_update(hass, info[CONF_TOKEN], info[CONF_URL])
        )


def setup_startup_listener(hass: HomeAssistant) -> None:
    hass.bus.async_listen_once("homeassistant_started", async_setup_after_start)


# Register the listener as soon as the module is imported
# (works for both YAML and UI setup)
def _register(hass: HomeAssistant) -> None:
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    setup_startup_listener(hass)


# Home-Assistant calls async_setup before anything else, so we can hook here
async def async_setup_entry_first_run(hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    _register(hass)
    return True
