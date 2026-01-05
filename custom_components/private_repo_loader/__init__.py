"""Private Repo Loader – sync private GitHub repos with sliding scale polling.

Each repository is its own config entry, allowing individual management
and proper linking from the integrations page.
"""

from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.persistent_notification import async_create

from .const import (
    DOMAIN,
    CONF_SLUG,
    SERVICE_SYNC_NOW,
    SERVICE_RELOAD_REPOS,
)
from .coordinator import PrivateRepoCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]

type PrivateRepoConfigEntry = ConfigEntry[PrivateRepoCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Private Repo Loader integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PrivateRepoConfigEntry) -> bool:
    """Set up a private repository from a config entry."""
    coordinator = PrivateRepoCoordinator(hass, entry)

    # Initial refresh
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in entry runtime data
    entry.runtime_data = coordinator

    # Register services if not already registered
    await _async_register_services(hass)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    slug = entry.data.get(CONF_SLUG, "unknown")
    poll_interval = coordinator.current_poll_interval

    _LOGGER.info(
        "Private Repo Loader entry set up for %s with poll interval %d minutes",
        slug,
        poll_interval,
    )

    # Check if the initial sync resulted in changes (new clone)
    if coordinator.data and coordinator.data.get("status") == "cloned":
        # Create a persistent notification for restart
        await async_create(
            hass,
            (
                f"Repository **{slug}** has been cloned successfully.\n\n"
                "**A restart of Home Assistant is required** to load the new "
                "custom component.\n\n"
                "Go to Settings → System → Restart to complete the installation."
            ),
            title="Private Repo Loader: Restart Required",
            notification_id=f"{DOMAIN}_restart_{entry.entry_id}",
        )
        _LOGGER.warning(
            "Repository %s cloned. Home Assistant restart required to load component.",
            slug,
        )
    elif coordinator.data and coordinator.data.get("status") == "updated":
        # Notify about update (restart also needed for code changes)
        await async_create(
            hass,
            (
                f"Repository **{slug}** has been updated.\n\n"
                "If the custom component code has changed, "
                "**a restart of Home Assistant may be required** "
                "to apply the changes."
            ),
            title="Private Repo Loader: Repository Updated",
            notification_id=f"{DOMAIN}_updated_{entry.entry_id}",
        )
        _LOGGER.info("Repository %s updated.", slug)

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: PrivateRepoConfigEntry
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_SYNC_NOW):
        return

    async def _handle_sync_now(call: ServiceCall) -> None:
        """Handle sync_now service call."""
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                coordinator: PrivateRepoCoordinator = entry.runtime_data
                await coordinator.async_request_refresh()

    async def _handle_reload_repos(call: ServiceCall) -> None:
        """Handle reload_repos service call - force refresh all repos."""
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                coordinator: PrivateRepoCoordinator = entry.runtime_data
                await coordinator.async_force_sync()

    hass.services.async_register(DOMAIN, SERVICE_SYNC_NOW, _handle_sync_now)
    hass.services.async_register(DOMAIN, SERVICE_RELOAD_REPOS, _handle_reload_repos)


async def async_unload_entry(
    hass: HomeAssistant, entry: PrivateRepoConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove services if this was the last entry
    entries = hass.config_entries.async_entries(DOMAIN)
    if len(entries) <= 1:  # Current entry being unloaded is still in the list
        if hass.services.has_service(DOMAIN, SERVICE_SYNC_NOW):
            hass.services.async_remove(DOMAIN, SERVICE_SYNC_NOW)
        if hass.services.has_service(DOMAIN, SERVICE_RELOAD_REPOS):
            hass.services.async_remove(DOMAIN, SERVICE_RELOAD_REPOS)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries to new format.

    Version 1: Single entry with multiple repos in options
    Version 2: Each repo is its own entry
    """
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        # Migration from V1 to V2 requires manual reconfiguration
        # as we can't automatically create multiple entries from one
        _LOGGER.warning(
            "Private Repo Loader config entry is outdated (v1). "
            "Please remove and re-add your repositories."
        )
        # We still return True to allow the entry to load, but it won't work correctly
        # The user needs to delete and re-add repos
        return True

    return True
