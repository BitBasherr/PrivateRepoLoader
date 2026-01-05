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

# Directory to store cloned repos
STAGING_DIR_NAME = ".private_repo_loader"


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


def _find_integration_in_repo(repo_path: Path, slug: str) -> Path | None:
    """Find the custom component folder in a repository.

    Searches for integration in these locations (in order):
    1. custom_components/<slug>/  (standard HACS structure)
    2. custom_components/<any_single_integration>/  (single integration in repo)
    3. Root of repo if it has __init__.py and manifest.json (flat structure)

    Returns the path to the integration folder, or None if not found.
    """
    custom_components_path = repo_path / "custom_components"

    # Case 1: Standard structure - custom_components/<slug>
    if custom_components_path.exists() and custom_components_path.is_dir():
        slug_path = custom_components_path / slug
        if slug_path.exists() and slug_path.is_dir():
            if (slug_path / "manifest.json").exists():
                return slug_path

        # Case 2: Check for any single integration in custom_components
        integrations = [
            d
            for d in custom_components_path.iterdir()
            if d.is_dir()
            and not d.name.startswith(".")
            and (d / "manifest.json").exists()
        ]
        if len(integrations) == 1:
            return integrations[0]
        elif len(integrations) > 1:
            # Multiple integrations - try to find one matching the slug
            for integration in integrations:
                if integration.name == slug:
                    return integration
            # If no exact match, return the first one
            return integrations[0]

    # Case 3: Flat structure - integration at root of repo
    if (repo_path / "manifest.json").exists() and (
        repo_path / "__init__.py"
    ).exists():
        return repo_path

    return None


def _sync_integration_files(
    source: Path, dest: Path, is_flat_structure: bool = False
) -> bool:
    """Sync integration files from source to destination.

    If is_flat_structure is True, source is the repo root and we copy
    only the integration files (not .git, etc).

    Returns True if files were changed (new or updated).
    """
    # Determine what to copy
    if is_flat_structure:
        # Copy only integration files, not git metadata
        exclude_patterns = {".git", ".github", ".gitignore", "README.md", "LICENSE"}
    else:
        exclude_patterns = set()

    # Check if destination exists and compare
    if dest.exists():
        # For now, just sync everything - git handles the change detection
        pass

    # Create destination if needed
    dest.parent.mkdir(parents=True, exist_ok=True)

    if is_flat_structure:
        # Copy files selectively
        dest.mkdir(exist_ok=True)
        for item in source.iterdir():
            if item.name in exclude_patterns:
                continue
            dest_item = dest / item.name
            if item.is_dir():
                if dest_item.exists():
                    shutil.rmtree(dest_item)
                shutil.copytree(item, dest_item)
            else:
                shutil.copy2(item, dest_item)
    else:
        # Copy the entire folder
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)

    return True


def _get_staging_path(config_root: Path, slug: str) -> Path:
    """Get the staging path for a repository.

    Repos are cloned to a staging area and then the custom_components
    content is copied to the actual custom_components folder.
    """
    staging_base = config_root / STAGING_DIR_NAME
    staging_base.mkdir(parents=True, exist_ok=True)
    return staging_base / slug


def sync_repo(root: Path, cfg: dict[str, Any]) -> str:
    """Sync a repository to the custom_components folder.

    Returns a simple string status for backwards compatibility.
    For full details, use sync_repo_detailed.
    """
    result = sync_repo_detailed(root, cfg)
    return result.status


def sync_repo_detailed(root: Path, cfg: dict[str, Any]) -> SyncResult:
    """Sync a repository and return detailed result including change detection.

    This function:
    1. Clones/updates the repo in a staging area
    2. Finds the custom_components/<integration> folder
    3. Copies only the integration files to HA's custom_components folder

    Args:
        root: Path to HA's custom_components folder
        cfg: Configuration dict with repo URL, slug, branch, token

    Returns:
        SyncResult with status and details
    """
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

    # Get staging path for the repository clone
    # The staging area is at the same level as custom_components
    config_root = root.parent  # Go up from custom_components to config dir
    staging_path = _get_staging_path(config_root, slug)

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
        is_new_clone = False

        if staging_path.exists():
            try:
                repo = git.Repo(staging_path)
            except InvalidGitRepositoryError:
                _LOGGER.warning("%s is not a git repo – moving aside", staging_path)
                _move_aside(staging_path)
                cloned_repo = git.Repo.clone_from(auth, staging_path, branch=branch)
                is_new_clone = True
                repo = cloned_repo
                commit_before = None
                commit_after = _get_current_commit(repo)
            else:
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
        else:
            cloned_repo = git.Repo.clone_from(auth, staging_path, branch=branch)
            is_new_clone = True
            repo = cloned_repo
            commit_before = None
            commit_after = _get_current_commit(repo)

        # Find the integration folder in the cloned repo
        integration_source = _find_integration_in_repo(staging_path, slug)

        if integration_source is None:
            _LOGGER.error(
                "Could not find custom component in repository %s. "
                "Expected custom_components/<integration>/ structure.",
                slug,
            )
            return SyncResult(
                status="skipped",
                error=(
                    "Repository does not contain a valid custom component. "
                    "Expected custom_components/<integration>/ structure."
                ),
                error_type="structure",
            )

        # Determine the integration name from the source path
        is_flat_structure = integration_source == staging_path
        if is_flat_structure:
            integration_name = slug
        else:
            integration_name = integration_source.name

        # Destination in HA's custom_components folder
        dest = root / integration_name

        # Determine if files have changed (git commit changed)
        has_git_changes = commit_before != commit_after if commit_before else True

        if has_git_changes:
            # Sync the integration files
            _sync_integration_files(integration_source, dest, is_flat_structure)

            if is_new_clone:
                _LOGGER.info(
                    "Repository %s cloned successfully, integration '%s' installed",
                    slug,
                    integration_name,
                )
                return SyncResult(
                    status="cloned",
                    has_changes=True,
                    commit_sha=commit_after,
                )
            else:
                _LOGGER.info(
                    "Repo %s updated: %s -> %s, integration '%s' updated",
                    slug,
                    commit_before[:8] if commit_before else "None",
                    commit_after[:8],
                    integration_name,
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
