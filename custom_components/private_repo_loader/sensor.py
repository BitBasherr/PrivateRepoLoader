"""Sensor entities for Private Repo Loader – per-repository status tracking."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_SLUG, CONF_REPO
from .coordinator import PrivateRepoCoordinator

from homeassistant.config_entries import ConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities for a repository."""
    coordinator: PrivateRepoCoordinator = entry.runtime_data

    entities = [
        RepoStatusSensor(coordinator, entry),
        RepoLastSyncSensor(coordinator, entry),
        RepoLastChangedSensor(coordinator, entry),
        RepoPollIntervalSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class RepoBaseSensor(CoordinatorEntity[PrivateRepoCoordinator], SensorEntity):
    """Base sensor for repository data."""

    def __init__(
        self,
        coordinator: PrivateRepoCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Private Repo: {entry.data.get(CONF_SLUG, 'Unknown')}",
            "manufacturer": "Private Repo Loader",
            "model": "GitHub Repository",
            "configuration_url": entry.data.get(CONF_REPO),
        }

    @property
    def repo_slug(self) -> str:
        """Return the repository slug."""
        return self._entry.data.get(CONF_SLUG, "unknown")


class RepoStatusSensor(RepoBaseSensor):
    """Sensor for repository sync status."""

    def __init__(self, coordinator: PrivateRepoCoordinator, entry: ConfigEntry) -> None:
        """Initialize the status sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="status",
                name=f"{entry.data.get(CONF_SLUG, 'Repo')} Status",
                icon="mdi:source-repository",
            ),
        )

    @property
    def native_value(self) -> str | None:
        """Return the current status."""
        if self.coordinator.data:
            return self.coordinator.data.get("status", "unknown")
        return "pending"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self.coordinator.data or {}
        return {
            "repository": self._entry.data.get(CONF_REPO, ""),
            "slug": self.repo_slug,
            "commit_sha": data.get("commit_sha"),
            "has_changes": data.get("has_changes", False),
            "error": data.get("error"),
        }


class RepoLastSyncSensor(RepoBaseSensor):
    """Sensor for last sync timestamp."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PrivateRepoCoordinator, entry: ConfigEntry) -> None:
        """Initialize the last sync sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="last_sync",
                name=f"{entry.data.get(CONF_SLUG, 'Repo')} Last Sync",
                icon="mdi:clock-outline",
            ),
        )

    @property
    def native_value(self) -> str | None:
        """Return the last sync timestamp."""
        if self.coordinator.data:
            return self.coordinator.data.get("last_checked", "Never")
        return "Never"


class RepoLastChangedSensor(RepoBaseSensor):
    """Sensor for last changed timestamp."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PrivateRepoCoordinator, entry: ConfigEntry) -> None:
        """Initialize the last changed sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="last_changed",
                name=f"{entry.data.get(CONF_SLUG, 'Repo')} Last Changed",
                icon="mdi:source-commit",
            ),
        )

    @property
    def native_value(self) -> str | None:
        """Return the last changed timestamp."""
        if self.coordinator.data:
            return self.coordinator.data.get("last_changed", "Never")
        return "Never"


class RepoPollIntervalSensor(RepoBaseSensor):
    """Sensor for current poll interval."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PrivateRepoCoordinator, entry: ConfigEntry) -> None:
        """Initialize the poll interval sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="poll_interval",
                name=f"{entry.data.get(CONF_SLUG, 'Repo')} Poll Interval",
                icon="mdi:timer-outline",
                native_unit_of_measurement="min",
            ),
        )

    @property
    def native_value(self) -> int:
        """Return the current poll interval in minutes."""
        return self.coordinator.current_poll_interval
