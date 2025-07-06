"""Shared constants for Private Repo Loader."""
from typing import Final
import logging

DOMAIN: Final = "private_repo_loader"
LOGGER_NAME: Final = f"custom_components.{DOMAIN}"

# Per-repo fields --------------------------------------------------------------
CONF_TOKEN:  Final = "token"       # GitHub PAT (kept in options)
CONF_REPO:   Final = "repository"  # https URL
CONF_BRANCH: Final = "branch"
CONF_SLUG:   Final = "slug"

DEFAULT_BRANCH: Final = "main"
DEFAULT_SLUG:   Final = "my_private_repo"

# Options-entry root keys -------------------------------------------------------
CONF_REPOS:  Final = "repos"

_LOGGER: Final = logging.getLogger(LOGGER_NAME)
