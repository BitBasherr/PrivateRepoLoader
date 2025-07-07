import os
import shutil
import tempfile
from pathlib import Path
import pytest

import git
from custom_components.private_repo_loader.loader import sync_repo

@pytest.fixture
def tmp_repo(tmp_path):
    # Initialize a real Git repo
    repo_dir = tmp_path / "repo"
    repo = git.Repo.init(repo_dir)
    # create an initial commit
    (repo_dir / "README.md").write_text("# test")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    return repo_dir

def test_sync_fresh_clone(tmp_repo, tmp_path, monkeypatch):
    # Serve via file:// URL
    url = tmp_repo.as_uri()
    cfg = {"repository": url, "slug": "testrepo", "branch": "main", "token": ""}
    dest_root = tmp_path / "out"
    dest_root.mkdir()
    result = sync_repo(dest_root, cfg)
    assert result == "cloned"
    assert (dest_root / "testrepo" / "README.md").exists()

def test_sync_update(tmp_repo, tmp_path):
    # First clone
    cfg = {"repository": tmp_repo.as_uri(), "slug": "r", "branch": "main", "token": ""}
    dest = tmp_path / "out"
    shutil.copytree(tmp_repo, dest / "r")
    repo = git.Repo(dest / "r")
    # Add a new commit upstream
    (tmp_repo / "foo.txt").write_text("bar")
    repo_up = git.Repo(tmp_repo)
    repo_up.index.add(["foo.txt"])
    repo_up.index.commit("add foo")
    # Now sync
    result = sync_repo(dest, cfg)
    assert result == "updated"
    assert (dest / "r" / "foo.txt").read_text() == "bar"