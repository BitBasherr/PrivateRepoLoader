"""Shared constants for Private Repo Loader."""
DOMAIN = "private_repo_loader"

# Per-repo fields ---------------------------------------------------
CONF_TOKEN   = "token"          # preferred everywhere
CONF_PAT     = CONF_TOKEN       # alias – keeps old code working
CONF_REPO    = "repository"     # https URL
CONF_BRANCH  = "branch"
CONF_SLUG    = "slug"

DEFAULT_BRANCH = "main"
DEFAULT_SLUG   = "example"

# Storage -----------------------------------------------------------
STORAGE_VERSION = 1
STORAGE_KEY     = f"{DOMAIN}.storage"
DATA_REPOS      = "repos"
