"""Git clone / pull helpers – runs in executor."""
from pathlib import Path
import git
import logging

from .const import CONF_URL, CONF_BRANCH, CONF_SLUG, CONF_PAT

_LOGGER = logging.getLogger(__name__)


def _with_pat(url: str, pat: str) -> str:
    if not url.startswith("https://"):
        raise ValueError("Only https:// GitHub URLs supported")
    return url.replace("https://", f"https://{pat}@")


def sync_repo(hass, repo_cfg: dict, pat: str) -> None:
    """Clone or pull a single repo."""
    dest = Path(hass.config.path()) / "custom_components" / repo_cfg[CONF_SLUG]
    url  = _with_pat(repo_cfg[CONF_URL], pat)
    branch = repo_cfg.get(CONF_BRANCH, "main")

    try:
        if dest.exists():
            repo = git.Repo(dest)
            repo.remotes.origin.pull()
            _LOGGER.info("Pulled private repo '%s'", dest.name)
        else:
            git.Repo.clone_from(url, dest, branch=branch)
            _LOGGER.info("Cloned private repo '%s'", dest.name)
    except Exception as exc:          # pylint: disable=broad-except
        _LOGGER.error("Git error on %s – %s", repo_cfg[CONF_URL], exc)
