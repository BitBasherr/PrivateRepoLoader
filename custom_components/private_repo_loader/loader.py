"""Clone or update a private GitHub repo."""
from pathlib import Path
import logging
import git

from .const import CONF_TOKEN, CONF_REPO, CONF_BRANCH

_LOGGER = logging.getLogger(__name__)


def _auth_url(url: str, token: str) -> str:
    """Return https://<token>@github.com/owner/repo.git."""
    if not url.startswith("https://"):
        raise ValueError("Only https:// clone URLs supported")
    return url.replace("https://", f"https://{token}@")

def sync_repo(dest_root: Path, cfg: dict) -> str:
    """
    Clone or pull the repo described by *cfg* into <dest_root>/<slug>.
    cfg must contain CONF_REPO, CONF_TOKEN, CONF_SLUG, CONF_BRANCH.
    """
    slug   = cfg[CONF_SLUG]
    branch = cfg.get(CONF_BRANCH)
    dest   = dest_root / slug
    auth   = _auth_url(cfg[CONF_REPO], cfg[CONF_TOKEN])

    if dest.exists():
        repo = git.Repo(dest)
        repo.remote().set_url(auth)
        repo.git.fetch()
        repo.git.checkout(branch or repo.active_branch.name)
        repo.remote().pull()
        return "updated"

    git.Repo.clone_from(auth, dest, branch=branch or None)
    return "cloned"
