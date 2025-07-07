import os
import sys

# Make custom_components importable
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    ),
)

import shutil
from pathlib import Path

import git
import pytest

# Override _auth_url to accept file:// URLs in tests
import custom_components.private_repo_loader.loader as loader_module
loader_module._auth_url = lambda url, token: url

from custom_components.private_repo_loader.loader import sync_repo


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create and commit in a temporary Git repo."""
    repo_dir = tmp_path / "repo"
    repo = git.Repo.init(repo_dir)
    (repo_dir / "README.md").write_text("# test")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    return repo_dir


def test_sync_fresh_clone(tmp_repo: Path, tmp_path: Path) -> None:
    """sync_repo should clone a fresh repo."""
    # Now file:// is accepted because of our override
    url = tmp_repo.as_uri()
    cfg = {
        "repository": url,
        "slug": "testrepo",
        "branch": "main",
        "token": "",
    }
    dest_root = tmp_path / "out"
    dest_root.mkdir()
    result = sync_repo(dest_root, cfg)
    assert result == "cloned"
    assert (dest_root / "testrepo" / "README.md").exists()


def test_sync_update(tmp_repo: Path, tmp_path: Path) -> None:
    """sync_repo should pull new commits onto an existing clone."""
    cfg = {
        "repository": tmp_repo.as_uri(),
        "slug": "r",
        "branch": "main",
        "token": "",
    }
    dest = tmp_path / "out"
    shutil.copytree(tmp_repo, dest / "r")

    # Simulate upstream change
    (tmp_repo / "foo.txt").write_text("bar")
    upstream = git.Repo(tmp_repo)
    upstream.index.add(["foo.txt"])
    upstream.index.commit("add foo")

    result = sync_repo(dest, cfg)
    assert result == "updated"
    assert (dest / "r" / "foo.txt").read_text() == "bar"