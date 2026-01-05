"""DataUpdateCoordinator for Private Repo Loader with sliding scale polling."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_REPO,
    CONF_SLUG,
    CONF_BRANCH,
    CONF_TOKEN,
    CONF_POLL_INTERVAL,
    CONF_LAST_CHANGED,
    DEFAULT_POLL_INTERVAL,
    POLL_INTERVAL_1_DAY,
    POLL_INTERVAL_1_WEEK,
    POLL_INTERVAL_1_MONTH,
    THRESHOLD_1_DAY,
    THRESHOLD_1_WEEK,
    THRESHOLD_1_MONTH,
)
from .loader import sync_repo_detailed, SyncResult

_LOGGER = logging.getLogger(__name__)


def calculate_poll_interval(
    last_changed: datetime | None,
    base_interval: int = DEFAULT_POLL_INTERVAL,
) -> int:
    """Calculate poll interval based on time since last change.

    Implements sliding scale:
    - Default: base_interval (1 minute)
    - No change for 1 day: 5 minutes
    - No change for 1 week: 30 minutes
    - No change for 1 month: 60 minutes
    """
    if last_changed is None:
        return base_interval

    now = datetime.now()
    time_since_change = (now - last_changed).total_seconds()

    if time_since_change >= THRESHOLD_1_MONTH:
        return POLL_INTERVAL_1_MONTH
    elif time_since_change >= THRESHOLD_1_WEEK:
        return POLL_INTERVAL_1_WEEK
    elif time_since_change >= THRESHOLD_1_DAY:
        return POLL_INTERVAL_1_DAY
    else:
        return base_interval


class PrivateRepoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for a single private repository with sliding scale polling."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self._last_changed: datetime | None = None
        self._last_commit_sha: str | None = None
        self._base_poll_interval = entry.options.get(
            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
        )

        # Load last_changed from stored data if available
        stored_last_changed = entry.data.get(CONF_LAST_CHANGED)
        if stored_last_changed:
            try:
                self._last_changed = datetime.fromisoformat(stored_last_changed)
            except (ValueError, TypeError):
                self._last_changed = None

        # Calculate initial update interval
        initial_interval = calculate_poll_interval(
            self._last_changed, self._base_poll_interval
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data.get(CONF_SLUG, 'unknown')}",
            update_interval=timedelta(minutes=initial_interval),
            config_entry=entry,
        )

        _LOGGER.debug(
            "Coordinator initialized for %s with poll interval %d minutes",
            entry.data.get(CONF_SLUG),
            initial_interval,
        )

    @property
    def repo_slug(self) -> str:
        """Return the repository slug."""
        return self.entry.data.get(CONF_SLUG, "unknown")

    @property
    def repo_url(self) -> str:
        """Return the repository URL."""
        return self.entry.data.get(CONF_REPO, "")

    @property
    def last_changed(self) -> datetime | None:
        """Return the last changed timestamp."""
        return self._last_changed

    @property
    def current_poll_interval(self) -> int:
        """Return the current poll interval in minutes."""
        return int(self.update_interval.total_seconds() / 60)

    def _dest_root(self) -> Path:
        """Return path to the custom_components folder."""
        return Path(self.hass.config.path("custom_components"))

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the repository."""
        cfg = {
            CONF_REPO: self.entry.data.get(CONF_REPO, ""),
            CONF_SLUG: self.entry.data.get(CONF_SLUG, ""),
            CONF_BRANCH: self.entry.options.get(
                CONF_BRANCH, self.entry.data.get(CONF_BRANCH, "main")
            ),
            CONF_TOKEN: self.entry.options.get(
                CONF_TOKEN, self.entry.data.get(CONF_TOKEN, "")
            ),
        }

        root = self._dest_root()

        try:
            result: SyncResult = await self.hass.async_add_executor_job(
                sync_repo_detailed, root, cfg
            )
        except Exception as exc:
            raise UpdateFailed(f"Error syncing repo: {exc}") from exc

        now = datetime.now()
        data = {
            "status": result.status,
            "has_changes": result.has_changes,
            "commit_sha": result.commit_sha,
            "last_checked": now.isoformat(),
            "slug": cfg[CONF_SLUG],
            "error": result.error,
        }

        # Update last_changed if there were changes
        if result.has_changes:
            self._last_changed = now
            self._last_commit_sha = result.commit_sha
            data["last_changed"] = now.isoformat()

            # Store last_changed in config entry data
            new_data = dict(self.entry.data)
            new_data[CONF_LAST_CHANGED] = now.isoformat()
            self.hass.config_entries.async_update_entry(self.entry, data=new_data)

            _LOGGER.info(
                "Repository %s has changes, resetting poll interval to %d minutes",
                self.repo_slug,
                self._base_poll_interval,
            )
        elif self._last_changed:
            data["last_changed"] = self._last_changed.isoformat()

        # Recalculate poll interval based on last change time
        new_interval = calculate_poll_interval(
            self._last_changed, self._base_poll_interval
        )

        if new_interval != self.current_poll_interval:
            self.update_interval = timedelta(minutes=new_interval)
            _LOGGER.debug(
                "Repository %s poll interval changed to %d minutes",
                self.repo_slug,
                new_interval,
            )

        return data

    async def async_force_sync(self) -> dict[str, Any]:
        """Force an immediate sync of the repository."""
        return await self._async_update_data()
