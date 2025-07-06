"""Low-level Git helper for Private Repo Loader – clone or pull one repo."""
from __future__ import annotations
from pathlib import Path
import logging
import git                       # GitPython

from .const import (
    CONF_TOKEN, CONF_REPO, CONF_SLUG,
    CONF_BRANCH, DEFAULT_BRANCH,
)

_LOGGER = logging.getLogger(__name__)


def _auth_url(url: str, token: str) -> str:
    """Embed a PAT into an https clone URL."""
    if not url.startswith("https://"):
        raise ValueError("Only https:// clone URLs supported")
    return url.replace("https://", f"https://{token}@")


def sync_repo(dest_root: Path, cfg: dict) -> str:
    """
    Clone or update *one* repo and return “cloned”, “updated” or “error”.
    `cfg` comes straight from the options flow.
    """
    slug   = cfg[CONF_SLUG]
    branch = cfg.get(CONF_BRANCH, DEFAULT_BRANCH)
    url    = cfg[CONF_REPO]
    token  = cfg.get(CONF_TOKEN, "")
    clone_url = _auth_url(url, token) if token else url
    dest    = dest_root / slug

    try:
        if dest.exists():
            repo = git.Repo(dest)
            repo.remote().set_url(clone_url)
            repo.git.fetch()
            repo.git.checkout(branch or repo.active_branch.name)
            repo.remote().pull()
            _LOGGER.debug("Private Repo Loader: %s updated", slug)
            return "updated"

        git.Repo.clone_from(clone_url, dest, branch=branch or None)
        _LOGGER.debug("Private Repo Loader: %s cloned", slug)
        return "cloned"

    except Exception:                           # pragma: no cover
        _LOGGER.exception("Private Repo Loader: %s failed", slug)
        return "error"
