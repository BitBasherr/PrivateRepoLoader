"""Clone / pull a private GitHub repo (runs in an executor thread)."""
from __future__ import annotations

import shutil
import time
from pathlib import Path
import logging
from typing import Dict, Any

import git                                   # GitPython
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
    """Embed PAT into HTTPS URL (if given)."""
    if not url.startswith("https://"):
        raise ValueError("Only https URLs supported")
    return url.replace("https://", f"https://{token}@") if token else url


def _move_aside(path: Path) -> None:
    """Move *path* → *path.old_<timestamp>*."""
    shutil.move(str(path), f"{path}.old_{int(time.time())}")


def sync_repo(root: Path, cfg: Dict[str, Any]) -> str:
    """
    Clone or update the repo described by *cfg*.
    Returns: 'cloned' | 'updated' | 'skipped'.
    """
    url    = cfg[CONF_REPO]
    slug   = cfg.get(CONF_SLUG, cfg.get(CONF_BRANCH, DEFAULT_BRANCH))
    branch = cfg.get(CONF_BRANCH, DEFAULT_BRANCH)
    token  = cfg.get(CONF_TOKEN, "")
    dest   = root / slug
    auth   = _auth_url(url, token)

    try:
        if dest.exists():
            try:
                repo = git.Repo(dest)
            except InvalidGitRepositoryError:
                _LOGGER.warning("%s is not a git repo – moving aside", dest)
                _move_aside(dest)
                git.Repo.clone_from(auth, dest, branch=branch)
                return "cloned"

            # existing repo – update
            repo.remote().set_url(auth)
            repo.git.fetch("--all", "--prune")
            try:
                repo.git.checkout(branch)
            except GitCommandError:
                repo.git.checkout("-B", branch, f"origin/{branch}")
            repo.git.pull("--ff-only")
            return "updated"

        git.Repo.clone_from(auth, dest, branch=branch)
        return "cloned"

    except Exception as exc:                      # noqa: BLE001
        _LOGGER.error("Repo %s: %s", url, exc)
        return "skipped"
