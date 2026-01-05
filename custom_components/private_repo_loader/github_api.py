"""GitHub API helper for validating tokens and fetching repositories."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubError(Enum):
    """GitHub API error types."""

    NONE = "none"
    INVALID_TOKEN = "invalid_token"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    REPO_NOT_FOUND = "repo_not_found"
    RATE_LIMITED = "rate_limited"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


@dataclass
class GitHubValidationResult:
    """Result of GitHub API validation."""

    valid: bool
    error: GitHubError = GitHubError.NONE
    error_message: str | None = None
    username: str | None = None
    repo_info: dict[str, Any] | None = None


@dataclass
class GitHubRepoInfo:
    """Information about a GitHub repository."""

    full_name: str  # owner/repo
    name: str
    private: bool
    html_url: str
    clone_url: str
    default_branch: str
    description: str | None = None


async def validate_token(token: str) -> GitHubValidationResult:
    """Validate a GitHub Personal Access Token.

    Returns information about the token validity and the authenticated user.
    """
    if not token:
        return GitHubValidationResult(
            valid=False,
            error=GitHubError.INVALID_TOKEN,
            error_message="Token is empty",
        )

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "PrivateRepoLoader-HomeAssistant",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GITHUB_API_BASE}/user", headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return GitHubValidationResult(
                        valid=True,
                        username=data.get("login"),
                    )
                elif response.status == 401:
                    return GitHubValidationResult(
                        valid=False,
                        error=GitHubError.INVALID_TOKEN,
                        error_message="Invalid or expired token",
                    )
                elif response.status == 403:
                    # Check for rate limiting
                    remaining = response.headers.get("X-RateLimit-Remaining", "0")
                    if remaining == "0":
                        return GitHubValidationResult(
                            valid=False,
                            error=GitHubError.RATE_LIMITED,
                            error_message="GitHub API rate limit exceeded",
                        )
                    return GitHubValidationResult(
                        valid=False,
                        error=GitHubError.INSUFFICIENT_PERMISSIONS,
                        error_message="Token has insufficient permissions",
                    )
                else:
                    return GitHubValidationResult(
                        valid=False,
                        error=GitHubError.UNKNOWN,
                        error_message=f"Unexpected response: {response.status}",
                    )
    except aiohttp.ClientError as exc:
        _LOGGER.error("Network error validating token: %s", exc)
        return GitHubValidationResult(
            valid=False,
            error=GitHubError.NETWORK_ERROR,
            error_message=str(exc),
        )


async def validate_repo_access(
    token: str, owner: str, repo: str
) -> GitHubValidationResult:
    """Validate access to a specific repository.

    Returns detailed information about whether the token can access the repo.
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "PrivateRepoLoader-HomeAssistant",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}", headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return GitHubValidationResult(
                        valid=True,
                        repo_info=data,
                    )
                elif response.status == 401:
                    return GitHubValidationResult(
                        valid=False,
                        error=GitHubError.INVALID_TOKEN,
                        error_message="Invalid or expired token",
                    )
                elif response.status == 403:
                    remaining = response.headers.get("X-RateLimit-Remaining", "0")
                    if remaining == "0":
                        return GitHubValidationResult(
                            valid=False,
                            error=GitHubError.RATE_LIMITED,
                            error_message="GitHub API rate limit exceeded",
                        )
                    return GitHubValidationResult(
                        valid=False,
                        error=GitHubError.INSUFFICIENT_PERMISSIONS,
                        error_message=(
                            f"Token does not have access to {owner}/{repo}. "
                            "Ensure your PAT has 'repo' scope for private repositories."
                        ),
                    )
                elif response.status == 404:
                    # Could be repo doesn't exist OR no access
                    if token:
                        return GitHubValidationResult(
                            valid=False,
                            error=GitHubError.REPO_NOT_FOUND,
                            error_message=(
                                f"Repository {owner}/{repo} not found or token lacks access. "
                                "For private repos, ensure PAT has 'repo' scope."
                            ),
                        )
                    return GitHubValidationResult(
                        valid=False,
                        error=GitHubError.REPO_NOT_FOUND,
                        error_message=(
                            f"Repository {owner}/{repo} not found. "
                            "For private repos, you must provide a PAT."
                        ),
                    )
                else:
                    return GitHubValidationResult(
                        valid=False,
                        error=GitHubError.UNKNOWN,
                        error_message=f"Unexpected response: {response.status}",
                    )
    except aiohttp.ClientError as exc:
        _LOGGER.error("Network error accessing repo %s/%s: %s", owner, repo, exc)
        return GitHubValidationResult(
            valid=False,
            error=GitHubError.NETWORK_ERROR,
            error_message=str(exc),
        )


async def list_user_repos(
    token: str, include_private: bool = True
) -> list[GitHubRepoInfo]:
    """List repositories accessible to the authenticated user.

    Returns a list of repositories the user has access to.
    """
    if not token:
        return []

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "PrivateRepoLoader-HomeAssistant",
    }

    repos: list[GitHubRepoInfo] = []
    page = 1
    per_page = 100

    try:
        async with aiohttp.ClientSession() as session:
            while True:
                params = {
                    "visibility": "all" if include_private else "public",
                    "per_page": str(per_page),
                    "page": str(page),
                    "sort": "updated",
                    "direction": "desc",
                }
                async with session.get(
                    f"{GITHUB_API_BASE}/user/repos",
                    headers=headers,
                    params=params,
                ) as response:
                    if response.status != 200:
                        _LOGGER.warning(
                            "Failed to fetch repos page %d: %s",
                            page,
                            response.status,
                        )
                        break

                    data = await response.json()
                    if not data:
                        break

                    for repo_data in data:
                        repos.append(
                            GitHubRepoInfo(
                                full_name=repo_data["full_name"],
                                name=repo_data["name"],
                                private=repo_data["private"],
                                html_url=repo_data["html_url"],
                                clone_url=repo_data["clone_url"],
                                default_branch=repo_data.get("default_branch", "main"),
                                description=repo_data.get("description"),
                            )
                        )

                    if len(data) < per_page:
                        break
                    page += 1

                    # Safety limit to prevent infinite loops
                    if page > 10:
                        _LOGGER.warning("Reached maximum page limit for repo listing")
                        break

    except aiohttp.ClientError as exc:
        _LOGGER.error("Network error listing repos: %s", exc)

    return repos


def parse_github_url(url: str) -> tuple[str, str] | None:
    """Parse a GitHub URL to extract owner and repo name.

    Supports:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - git@github.com:owner/repo.git

    Returns tuple of (owner, repo) or None if parsing fails.
    """
    if not url:
        return None

    url = url.strip()

    # Handle HTTPS URLs
    if url.startswith("https://github.com/"):
        path = url[len("https://github.com/") :]
        path = path.rstrip("/")
        if path.endswith(".git"):
            path = path[:-4]
        parts = path.split("/")
        if len(parts) >= 2:
            return (parts[0], parts[1])

    # Handle SSH URLs
    if url.startswith("git@github.com:"):
        path = url[len("git@github.com:") :]
        if path.endswith(".git"):
            path = path[:-4]
        parts = path.split("/")
        if len(parts) >= 2:
            return (parts[0], parts[1])

    return None
