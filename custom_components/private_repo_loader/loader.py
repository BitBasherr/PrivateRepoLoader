"""Clone / pull a single GitHub repo (runs in an executor thread).

Return value: "cloned" | "updated" | "skipped".
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Final

import git  # GitPython

from .const import (
    CONF_BRANCH,
    CONF_REPO,
    CONF_SLUG,
    CONF_TOKEN,
    LOGGER_NAME,
)

_LOGGER: Final = logging.getLogger(LOGGER_NAME)


# ────────────────────────────────────────────────────────────────────────────────
def _tokenised_url(url: str, token: str | None) -> str:
    """Insert the PAT into an https clone URL (if provided)."""
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS clone URLs are supported")

    if token:
        # Remove trailing `.git`, inject token, re-append `.git`
        url_no_git = re.sub(r"\.git$", "", url, flags=re.I)
        owner_repo = url_no_git.removeprefix("https://")
        return f"https://{token}@{owner_repo}.git"
    return url


def sync_repo(root: Path, cfg: dict) -> str:
    """Clone or pull a single repository."""
    url:    str = cfg[CONF_REPO]
    branch: str = cfg.get(CONF_BRANCH) or "main"
    slug:   str = cfg.get(CONF_SLUG)   or branch
    token:  str = cfg.get(CONF_TOKEN)  or None

    dest = root / slug
    clone_url = _tokenised_url(url, token)

    if dest.exists():
        repo = git.Repo(dest)
        origin = repo.remotes.origin
        origin.set_url(clone_url)
        origin.fetch()
        origin.pull(branch)
        _LOGGER.debug("Updated %s -> %s", url, dest)
        return "updated"

    dest.parent.mkdir(parents=True, exist_ok=True)
    git.Repo.clone_from(clone_url, dest, branch=branch, depth=1)
    _LOGGER.debug("Cloned %s -> %s", url, dest)
    return "cloned"
