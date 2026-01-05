"""Button entities for Private Repo Loader - Restart and Sync buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_SLUG, CONF_REPO
from .coordinator import PrivateRepoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities for a repository."""
    coordinator: PrivateRepoCoordinator = entry.runtime_data

    async_add_entities(
        [
            RepoSyncButton(coordinator, entry),
            RestartHAButton(coordinator, entry),
        ]
    )


class RepoSyncButton(CoordinatorEntity[PrivateRepoCoordinator], ButtonEntity):
    """Button to trigger repository sync."""

    def __init__(
        self,
        coordinator: PrivateRepoCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sync button."""
        super().__init__(coordinator)
        self._entry = entry

        slug = entry.data.get(CONF_SLUG, "unknown")
        self._attr_unique_id = f"{entry.entry_id}_sync"
        self._attr_name = f"{slug} Sync Now"
        self._attr_icon = "mdi:sync"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Private Repo: {slug}",
            "manufacturer": "Private Repo Loader",
            "model": "GitHub Repository",
            "configuration_url": entry.data.get(CONF_REPO),
        }

        self.entity_description = ButtonEntityDescription(
            key="sync",
            name=f"{slug} Sync Now",
            icon="mdi:sync",
        )

    async def async_press(self) -> None:
        """Handle the button press - trigger sync."""
        await self.coordinator.async_request_refresh()


class RestartHAButton(CoordinatorEntity[PrivateRepoCoordinator], ButtonEntity):
    """Button to restart Home Assistant.

    This button is useful when updates have been downloaded and need
    to be applied by restarting Home Assistant.
    """

    def __init__(
        self,
        coordinator: PrivateRepoCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the restart button."""
        super().__init__(coordinator)
        self._entry = entry

        slug = entry.data.get(CONF_SLUG, "unknown")
        self._attr_unique_id = f"{entry.entry_id}_restart"
        self._attr_name = f"{slug} Restart HA"
        self._attr_icon = "mdi:restart"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Private Repo: {slug}",
            "manufacturer": "Private Repo Loader",
            "model": "GitHub Repository",
            "configuration_url": entry.data.get(CONF_REPO),
        }

        self.entity_description = ButtonEntityDescription(
            key="restart",
            name=f"{slug} Restart HA",
            icon="mdi:restart",
        )

    async def async_press(self) -> None:
        """Handle the button press - restart Home Assistant."""
        await self.hass.services.async_call(
            "homeassistant",
            "restart",
            blocking=False,
        )
