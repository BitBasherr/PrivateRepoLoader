"""Clone / pull a private GitHub repo (runs in executor)."""
from __future__ import annotations

import shutil
import time
from pathlib import Path
import logging
from typing import Dict, Any

import git                         # GitPython
from git.exc import GitCommandError, InvalidGitRepositoryError

from .const import (
    CONF_TOKEN,
    CONF_REPO,
    CONF_BRANCH,
    CONF_SLUG,
    DEFAULT_BRANCH,
)

_LOGGER = logging.getLogger(__name__)


def _auth_url(url: str, token: str | None) -> str:
    """Return an https URL with the token embedded (if given)."""
    if not url.startswith("https://"):
        raise ValueError("Only https:// clone URLs are supported")
    if token:
        return url.replace("https://", f"https://{token}@")
    return url


def _safe_move_to_old(path: Path) -> None:
    """Move *path* → *path.old_TIMESTAMP* (never overwrite)."""
    ts = int(time.time())
    shutil.move(str(path), f"{path}.old_{ts}")


def sync_repo(root: Path, cfg: Dict[str, Any]) -> str:
    """
    Clone or update a repo definition.
    cfg keys: repository, slug, branch, token
    Returns "cloned", "updated", or "skipped".
    """
    url     = cfg[CONF_REPO]
    slug    = cfg.get(CONF_SLUG, DEFAULT_SLUG)
    branch  = cfg.get(CONF_BRANCH, DEFAULT_BRANCH)
    token   = cfg.get(CONF_TOKEN, "")
    dest    = root / slug
    authurl = _auth_url(url, token)

    try:
        if dest.exists():
            try:
                repo = git.Repo(dest)
            except InvalidGitRepositoryError:
                _LOGGER.warning("%s is not a git repo – moving aside", dest)
                _safe_move_to_old(dest)
                git.Repo.clone_from(authurl, dest, branch=branch)
                return "cloned"

            # existing repo – update
            repo.remote().set_url(authurl)
            repo.git.fetch("--all", "--prune")
            try:
                repo.git.checkout(branch)
            except GitCommandError:
                # branch missing locally – create tracking branch
                repo.git.checkout("-B", branch, f"origin/{branch}")
            repo.git.pull("--ff-only")
            return "updated"

        # fresh clone
        git.Repo.clone_from(authurl, dest, branch=branch)
        return "cloned"

    except Exception as exc:           # noqa: BLE001
        _LOGGER.error("Repo %s: %s", url, exc)
        return "skipped"
