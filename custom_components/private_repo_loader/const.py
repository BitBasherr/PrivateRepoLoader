"""Shared constants for Private Repo Loader."""
from typing import Final
import logging

DOMAIN: Final = "private_repo_loader"

CONF_TOKEN:  Final = "token"
CONF_REPOS:  Final = "repos"
CONF_REPO:   Final = "repository"
CONF_BRANCH: Final = "branch"
CONF_SLUG:   Final = "slug"

DEFAULT_BRANCH: Final = "main"
DEFAULT_SLUG:   Final = "example"

SERVICE_SYNC_NOW: Final = "sync_now"
DISPATCHER_SYNC_DONE: Final = f"{DOMAIN}_sync_done"

_LOGGER: Final = logging.getLogger(f"custom_components.{DOMAIN}")
