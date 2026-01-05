"""Clone / pull a private GitHub repo (runs in executor)."""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path
import logging
from typing import Any

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


class AuthenticationError(Exception):
    """Exception raised when authentication fails."""

    pass


class PermissionError(Exception):
    """Exception raised when permission is denied."""

    pass


class RepositoryNotFoundError(Exception):
    """Exception raised when repository is not found."""

    pass


@dataclass
class SyncResult:
    """Result of a sync operation."""

    status: str  # "cloned", "updated", "unchanged", "skipped"
    has_changes: bool = False
    commit_sha: str | None = None
    error: str | None = None
    error_type: str | None = None  # "auth", "permission", "not_found", "network", etc.


def _auth_url(url: str, token: str | None) -> str:
    if not url.startswith("https://"):
        raise ValueError("Only https clone URLs are supported")
    return url.replace("https://", f"https://{token}@") if token else url


def _move_aside(path: Path) -> None:
    shutil.move(str(path), f"{path}.old_{int(time.time())}")


def _get_current_commit(repo: git.Repo) -> str:
    """Get the current commit SHA."""
    return repo.head.commit.hexsha


def _parse_git_error(error_str: str) -> tuple[str, str]:
    """Parse a git error string to determine error type and user-friendly message.

    Returns tuple of (error_type, user_message).
    """
    error_lower = error_str.lower()

    # Authentication failures
    if "authentication failed" in error_lower or "invalid credentials" in error_lower:
        return (
            "auth",
            "Authentication failed. Please check your Personal Access Token (PAT).",
        )

    # 401 Unauthorized
    if "401" in error_str or "unauthorized" in error_lower:
        return (
            "auth",
            "Unauthorized. Your PAT may be invalid or expired.",
        )

    # 403 Forbidden
    if "403" in error_str or "forbidden" in error_lower:
        return (
            "permission",
            "Permission denied. Ensure your PAT has 'repo' scope for private repos.",
        )

    # 404 Not Found
    if "404" in error_str or "not found" in error_lower:
        return (
            "not_found",
            "Repository not found. Check the URL or ensure your PAT has access.",
        )

    # Remote hung up / network issues
    if (
        "could not read from remote" in error_lower
        or "remote hung up" in error_lower
        or "connection refused" in error_lower
    ):
        return (
            "network",
            "Network error connecting to GitHub. Please check your connection.",
        )

    # Repository does not exist or no access
    if "does not appear to be a git repository" in error_lower:
        return (
            "not_found",
            "Repository not found or no access. Verify URL and PAT permissions.",
        )

    return ("unknown", error_str)


def sync_repo(root: Path, cfg: dict[str, Any]) -> str:
    """Sync a repository to the custom_components folder.

    Returns a simple string status for backwards compatibility.
    For full details, use sync_repo_detailed.
    """
    result = sync_repo_detailed(root, cfg)
    return result.status


def sync_repo_detailed(root: Path, cfg: dict[str, Any]) -> SyncResult:
    """Sync a repository and return detailed result including change detection."""
    url = cfg.get(CONF_REPO, "")
    if not url:
        _LOGGER.error("Repository URL is empty")
        return SyncResult(
            status="skipped",
            error="Repository URL is empty",
            error_type="config",
        )

    # Validate URL format (allow file:// for testing)
    if not url.startswith("https://") and not url.startswith("file://"):
        _LOGGER.error("Repository URL must start with https://: %s", url)
        return SyncResult(
            status="skipped",
            error="Repository URL must start with https://",
            error_type="config",
        )

    slug = cfg.get(CONF_SLUG, "")
    if not slug:
        # Extract repo name from URL as fallback
        url_parts = url.rstrip("/").split("/")
        if len(url_parts) > 0:
            extracted = url_parts[-1].replace(".git", "").strip()
            slug = extracted if extracted else ""

    if not slug:
        _LOGGER.error("Could not determine slug from URL: %s", url)
        return SyncResult(
            status="skipped",
            error="Could not determine slug from URL",
            error_type="config",
        )

    branch = cfg.get(CONF_BRANCH, DEFAULT_BRANCH)
    token = cfg.get(CONF_TOKEN, "")
    dest = root / slug

    try:
        auth = _auth_url(url, token)
    except ValueError as exc:
        _LOGGER.error("Invalid repository URL: %s", exc)
        return SyncResult(
            status="skipped",
            error=str(exc),
            error_type="config",
        )

    try:
        if dest.exists():
            try:
                repo = git.Repo(dest)
            except InvalidGitRepositoryError:
                _LOGGER.warning("%s is not a git repo – moving aside", dest)
                _move_aside(dest)
                cloned_repo = git.Repo.clone_from(auth, dest, branch=branch)
                _LOGGER.info("Repository %s cloned successfully", slug)
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
        _LOGGER.info("Repository %s cloned successfully", slug)
        return SyncResult(
            status="cloned",
            has_changes=True,
            commit_sha=_get_current_commit(cloned_repo),
        )

    except GitCommandError as exc:
        error_str = str(exc)
        error_type, user_message = _parse_git_error(error_str)
        _LOGGER.error("Git error for %s (%s): %s", slug, error_type, user_message)
        return SyncResult(
            status="skipped",
            error=user_message,
            error_type=error_type,
        )
    except Exception as exc:  # noqa: BLE001
        error_str = str(exc)
        error_type, user_message = _parse_git_error(error_str)
        _LOGGER.error("Repo %s: %s", url, exc)
        return SyncResult(
            status="skipped",
            error=user_message,
            error_type=error_type,
        )
