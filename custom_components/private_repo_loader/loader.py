"""Private Repo Loader – helper that clones / updates one GitHub repo.

Runs in an executor thread (HA calls it with hass.async_add_executor_job).
Return value: "cloned" | "updated" | "skipped".
"""

from __future__ import annotations

from pathlib import Path
import logging
import re
import git  # GitPython

from .const import (
    CONF_REPO,
    CONF_BRANCH,
    CONF_TOKEN,
    CONF_SLUG,
    DEFAULT_BRANCH,
)

_LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------------------------------


def _tokenised_url(url: str, token: str | None) -> str:
    """
    Turn ``https://github.com/owner/repo`` into
    ``https://<token>@github.com/owner/repo.git`` (if a token is supplied).

    Raises ValueError if the URL is not https-based.
    """
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS clone URLs are supported")

    if token:
        # remove a trailing “.git” before inserting token – we'll add it back
        base = re.sub(r"\.git$", "", url)
        return base.replace("https://", f"https://{token}@") + ".git"

    return url if url.endswith(".git") else f"{url}.git"


# -----------------------------------------------------------------------------


def sync_repo(dest_root: Path, cfg: dict) -> str:  # noqa: C901
    """
    Clone or pull the repo described by *cfg* into
    ``<dest_root>/<slug>``.

    *cfg* **must** contain

    * ``CONF_REPO``   – HTTPS URL (public or private)
    * ``CONF_SLUG``   – target folder name under ``custom_components``
    * ``CONF_TOKEN``  – PAT to use (may be empty ⇒ unauthenticated)
    * ``CONF_BRANCH`` – optional branch/ref to check out

    Returns ``"cloned"`` if the repo did not exist before,
    ``"updated"`` if `git pull` was executed,
    ``"skipped"`` if the working tree was already up-to-date.
    """
    slug: str = cfg[CONF_SLUG]
    repo_url: str = cfg[CONF_REPO]
    branch: str = cfg.get(CONF_BRANCH, DEFAULT_BRANCH)
    token: str | None = cfg.get(CONF_TOKEN) or None

    dest = dest_root / slug
    auth_url = _tokenised_url(repo_url, token)

    if dest.exists():
        try:
            repo = git.Repo(dest)
        except git.exc.InvalidGitRepositoryError:
            # folder exists but is not a git repo – start fresh
            _LOGGER.warning("Folder %s exists but is not a repo – re-cloning", dest)
            dest.rename(dest.with_suffix(".old"))
            git.Repo.clone_from(auth_url, dest, branch=branch)
            return "cloned"

        # switch remote URL (in case token or repo URL changed)
        repo.remote().set_url(auth_url)

        # ensure correct branch / ref
        if repo.active_branch.name != branch:
            repo.git.checkout(branch)

        # pull fast-forwards only
        info = repo.remote().pull("--ff-only")
        if not info or info[0].flags & info[0].UP_TO_DATE:
            return "skipped"

        _LOGGER.info("Updated %s → %s", slug, info[0].commit.hexsha[:7])
        return "updated"

    # brand-new clone
    git.Repo.clone_from(auth_url, dest, branch=branch)
    _LOGGER.info("Cloned %s → %s", repo_url, dest)
    return "cloned"
