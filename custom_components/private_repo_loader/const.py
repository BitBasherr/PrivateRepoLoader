"""Shared constants for Private Repo Loader."""
DOMAIN = "private_repo_loader"

# Config-entry data / options
CONF_TOKEN   = "token"          # Personal-access token (PAT) – may be ""
CONF_REPOS   = "repos"          # list-of-dicts, each repo definition
CONF_REPO    = "repository"     # https://github.com/owner/repo
CONF_BRANCH  = "branch"         # branch / tag; default = main
CONF_SLUG    = "slug"           # folder name under custom_components

DEFAULT_BRANCH = "main"
DEFAULT_SLUG   = "example"

# Storage helpers
STORAGE_VERSION = 1
STORAGE_KEY     = f"{DOMAIN}.storage"

# Service name
SERVICE_SYNC_NOW = "sync_now"
