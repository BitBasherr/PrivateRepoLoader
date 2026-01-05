"""Shared constants for Private Repo Loader."""

from typing import Final
import logging

DOMAIN: Final = "private_repo_loader"

CONF_TOKEN: Final = "token"
CONF_REPOS: Final = "repos"
CONF_REPO: Final = "repository"
CONF_BRANCH: Final = "branch"
CONF_SLUG: Final = "slug"
CONF_POLL_INTERVAL: Final = "poll_interval"
CONF_LAST_CHANGED: Final = "last_changed"
CONF_LAST_CHECKED: Final = "last_checked"

DEFAULT_BRANCH: Final = "main"

# Default polling intervals in minutes
DEFAULT_POLL_INTERVAL: Final = 1
POLL_INTERVAL_1_DAY: Final = 5  # After 1 day of no changes
POLL_INTERVAL_1_WEEK: Final = 30  # After 1 week of no changes
POLL_INTERVAL_1_MONTH: Final = 60  # After 1 month of no changes

# Time thresholds in seconds
THRESHOLD_1_DAY: Final = 24 * 60 * 60  # 1 day
THRESHOLD_1_WEEK: Final = 7 * 24 * 60 * 60  # 1 week
THRESHOLD_1_MONTH: Final = 30 * 24 * 60 * 60  # 1 month

SERVICE_SYNC_NOW: Final = "sync_now"
SERVICE_RELOAD_REPOS: Final = "reload_repos"
DISPATCHER_SYNC_DONE: Final = f"{DOMAIN}_sync_done"
DISPATCHER_REPO_UPDATED: Final = f"{DOMAIN}_repo_updated"

_LOGGER: Final = logging.getLogger(f"custom_components.{DOMAIN}")
