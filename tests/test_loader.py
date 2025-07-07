import shutil
from pathlib import Path

import git
import pytest

from custom_components.private_repo_loader.loader import sync_repo


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create and commit in a temporary Git repo on branch 'main'."""
    repo_dir = tmp_path / "repo"
    repo = git.Repo.init(repo_dir)
    # Initial commit
    (repo_dir / "README.md").write_text("# test")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    # Rename to 'main'
    repo.git.branch("-M", "main")
    return repo_dir


def test_sync_fresh_clone(tmp_repo: Path, tmp_path: Path) -> None:
    """sync_repo should clone a fresh repo."""
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
    dest_root = tmp_path / "out"
    dest_root.mkdir()
    # First clone
    first = sync_repo(dest_root, cfg)
    assert first == "cloned"

    # Simulate upstream change
    (tmp_repo / "foo.txt").write_text("bar")
    upstream = git.Repo(tmp_repo)
    upstream.index.add(["foo.txt"])
    upstream.index.commit("add foo")
    upstream.git.branch("-M", "main")

    # Then update
    second = sync_repo(dest_root, cfg)
    assert second == "updated"
    assert (dest_root / "r" / "foo.txt").read_text() == "bar"
