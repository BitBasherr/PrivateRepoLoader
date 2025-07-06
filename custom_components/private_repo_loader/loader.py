"""Clone or update a private GitHub repo (runs in executor thread)."""
from pathlib import Path
import logging
import git                               # GitPython

from .const import (
    CONF_TOKEN,
    CONF_REPO,
    CONF_SLUG,        # ← add this
    CONF_BRANCH,
    DEFAULT_BRANCH,   # ← if you defined one in const.py
)

_LOGGER = logging.getLogger(__name__)


def _auth_url(url: str, token: str) -> str:
    """Inject the PAT into an https-clone URL."""
    if not url.startswith("https://"):
        raise ValueError("Only https:// clone URLs supported")
    # https://github.com/owner/repo.git  →  https://<TOKEN>@github.com/…
    return url.replace("https://", f"https://{token}@")


def sync_repo(dest_root: Path, cfg: dict) -> str:
    """
    Clone or pull the repo described by *cfg* into <dest_root>/<slug>.

    cfg must contain CONF_REPO, CONF_TOKEN, CONF_SLUG.
    """
    slug   = cfg[CONF_SLUG]
    branch = cfg.get(CONF_BRANCH, DEFAULT_BRANCH)
    dest   = dest_root / slug
    auth   = _auth_url(cfg[CONF_REPO], cfg[CONF_TOKEN])

    if dest.exists():
        repo = git.Repo(dest)
        repo.remote().set_url(auth)
        repo.git.fetch()
        repo.git.checkout(branch or repo.active_branch.name)
        repo.remote().pull()
        _LOGGER.debug("Private Repo Loader: updated %s (%s)", slug, branch)
        return "updated"

    git.Repo.clone_from(auth, dest, branch=branch or None)
    _LOGGER.debug("Private Repo Loader: cloned %s (%s)", slug, branch)
    return "cloned"
