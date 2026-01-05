"""Update entity for Private Repo Loader - HACS-like update tracking."""

from __future__ import annotations

from typing import Any

from homeassistant.components.update import (
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
)
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
    """Set up update entity for a repository."""
    coordinator: PrivateRepoCoordinator = entry.runtime_data

    async_add_entities([RepoUpdateEntity(coordinator, entry)])


class RepoUpdateEntity(CoordinatorEntity[PrivateRepoCoordinator], UpdateEntity):
    """Update entity for repository updates.

    This entity shows when a repository has been updated and provides
    an install action that triggers a Home Assistant restart.
    """

    _attr_supported_features = UpdateEntityFeature.INSTALL

    def __init__(
        self,
        coordinator: PrivateRepoCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._pending_update = False
        self._installed_version: str | None = None
        self._latest_version: str | None = None

        slug = entry.data.get(CONF_SLUG, "unknown")
        self._attr_unique_id = f"{entry.entry_id}_update"
        self._attr_name = f"{slug} Update"
        self._attr_title = slug
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Private Repo: {slug}",
            "manufacturer": "Private Repo Loader",
            "model": "GitHub Repository",
            "configuration_url": entry.data.get(CONF_REPO),
        }

        self.entity_description = UpdateEntityDescription(
            key="update",
            name=f"{slug} Update",
        )

    @property
    def installed_version(self) -> str | None:
        """Return the installed version (current commit SHA)."""
        if self._installed_version:
            return self._installed_version[:8]  # Short SHA
        if self.coordinator.data:
            sha = self.coordinator.data.get("commit_sha")
            if sha and not self._pending_update:
                return sha[:8]
        return None

    @property
    def latest_version(self) -> str | None:
        """Return the latest version (new commit SHA if updated)."""
        if self._pending_update and self._latest_version:
            return self._latest_version[:8]
        return self.installed_version

    @property
    def in_progress(self) -> bool:
        """Return if an update is in progress."""
        return False

    @property
    def release_summary(self) -> str | None:
        """Return the release summary."""
        if self._pending_update:
            return (
                "A new version has been downloaded and is ready to install.\n\n"
                "**Action Required:** Click 'Install' to restart Home Assistant "
                "and apply the update."
            )
        return None

    @property
    def release_url(self) -> str | None:
        """Return the release URL."""
        return self._entry.data.get(CONF_REPO)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data:
            status = self.coordinator.data.get("status")
            if status in ("cloned", "updated"):
                # There's an update that needs restart
                new_sha = self.coordinator.data.get("commit_sha")
                if new_sha != self._installed_version:
                    self._pending_update = True
                    self._latest_version = new_sha
                    if self._installed_version is None:
                        self._installed_version = "new"
            elif status == "unchanged":
                # No update, sync versions
                sha = self.coordinator.data.get("commit_sha")
                if not self._pending_update:
                    self._installed_version = sha

        super()._handle_coordinator_update()

    async def async_install(
        self,
        version: str | None,
        backup: bool,
        **kwargs: Any,
    ) -> None:
        """Install the update by restarting Home Assistant."""
        # Clear the pending update flag
        self._installed_version = self._latest_version
        self._pending_update = False
        self.async_write_ha_state()

        # Trigger Home Assistant restart
        await self.hass.services.async_call(
            "homeassistant",
            "restart",
            blocking=False,
        )
