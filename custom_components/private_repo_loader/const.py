"""Shared constants for Private Repo Loader."""
from typing import Final
import logging

DOMAIN: Final = "private_repo_loader"

# Config-entry options
CONF_TOKEN:  Final = "token"       # GitHub PAT
CONF_REPOS:  Final = "repos"       # list-of-dicts
CONF_REPO:   Final = "repository"  # HTTPS clone URL
CONF_BRANCH: Final = "branch"
CONF_SLUG:   Final = "slug"

DEFAULT_BRANCH: Final = "main"
DEFAULT_SLUG:   Final = "example"

# Service name
SERVICE_SYNC_NOW: Final = "sync_now"

_LOGGER: Final = logging.getLogger(f"custom_components.{DOMAIN}")
