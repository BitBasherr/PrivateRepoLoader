"""Clone / pull a private GitHub repo (runs in executor)."""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path
import logging
from typing import Dict, Any

import git
from git.exc import GitCommandError, InvalidGitRepositoryError

from .const import (
    CONF_TOKEN,
    CONF_REPO,
    CONF_BRANCH,
    CONF_SLUG,
    DEFAULT_BRANCH,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation."""

    status: str  # "cloned", "updated", "unchanged", "skipped"
    has_changes: bool = False
    commit_sha: str | None = None
    error: str | None = None


def _auth_url(url: str, token: str | None) -> str:
    if not url.startswith("https://"):
        raise ValueError("Only https clone URLs are supported")
    return url.replace("https://", f"https://{token}@") if token else url


def _move_aside(path: Path) -> None:
    shutil.move(str(path), f"{path}.old_{int(time.time())}")


def _get_current_commit(repo: git.Repo) -> str:
    """Get the current commit SHA."""
    return repo.head.commit.hexsha


def sync_repo(root: Path, cfg: Dict[str, Any]) -> str:
    """Sync a repository to the custom_components folder.

    Returns a simple string status for backwards compatibility.
    For full details, use sync_repo_detailed.
    """
    result = sync_repo_detailed(root, cfg)
    return result.status


def sync_repo_detailed(root: Path, cfg: Dict[str, Any]) -> SyncResult:
    """Sync a repository and return detailed result including change detection."""
    url = cfg.get(CONF_REPO, "")
    if not url:
        _LOGGER.error("Repository URL is empty")
        return SyncResult(status="skipped", error="Repository URL is empty")

    slug = cfg.get(CONF_SLUG, "")
    if not slug:
        # Extract repo name from URL as fallback
        url_parts = url.rstrip("/").split("/")
        if len(url_parts) > 0:
            extracted = url_parts[-1].replace(".git", "").strip()
            slug = extracted if extracted else ""

    if not slug:
        _LOGGER.error("Could not determine slug from URL: %s", url)
        return SyncResult(status="skipped", error="Could not determine slug from URL")

    branch = cfg.get(CONF_BRANCH, DEFAULT_BRANCH)
    token = cfg.get(CONF_TOKEN, "")
    dest = root / slug
    auth = _auth_url(url, token)

    try:
        if dest.exists():
            try:
                repo = git.Repo(dest)
            except InvalidGitRepositoryError:
                _LOGGER.warning("%s is not a git repo – moving aside", dest)
                _move_aside(dest)
                cloned_repo = git.Repo.clone_from(auth, dest, branch=branch)
                return SyncResult(
                    status="cloned",
                    has_changes=True,
                    commit_sha=_get_current_commit(cloned_repo),
                )

            # Get commit before fetch/pull
            commit_before = _get_current_commit(repo)

            repo.remote().set_url(auth)
            repo.git.fetch("--all", "--prune")
            try:
                repo.git.checkout(branch)
            except GitCommandError:
                repo.git.checkout("-B", branch, f"origin/{branch}")
            repo.git.pull("--ff-only")

            # Check if commit changed
            commit_after = _get_current_commit(repo)
            has_changes = commit_before != commit_after

            if has_changes:
                _LOGGER.info(
                    "Repo %s updated: %s -> %s",
                    slug,
                    commit_before[:8],
                    commit_after[:8],
                )
                return SyncResult(
                    status="updated",
                    has_changes=True,
                    commit_sha=commit_after,
                )
            else:
                return SyncResult(
                    status="unchanged",
                    has_changes=False,
                    commit_sha=commit_after,
                )

        cloned_repo = git.Repo.clone_from(auth, dest, branch=branch)
        return SyncResult(
            status="cloned",
            has_changes=True,
            commit_sha=_get_current_commit(cloned_repo),
        )

    except Exception as exc:  # noqa: BLE001
        _LOGGER.error("Repo %s: %s", url, exc)
        return SyncResult(status="skipped", error=str(exc))
