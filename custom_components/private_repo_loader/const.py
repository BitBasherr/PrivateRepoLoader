"""Shared constants."""
DOMAIN               = "private_repo_loader"

CONF_REPOS           = "repos"         # list[dict]
CONF_PAT             = "github_pat"
CONF_URL             = "url"
CONF_BRANCH          = "branch"
CONF_SLUG            = "slug"

DEFAULT_BRANCH       = "main"
DEFAULT_SLUG         = "example_component"

ENTRY_VERSION        = 1
SCAN_INTERVAL_SEC    = 6 * 3600        # 6 h
