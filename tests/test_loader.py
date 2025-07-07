import os import sys

Make custom_components importable for all tests

sys.path.insert( 0, os.path.abspath( os.path.join(os.path.dirname(file), "..") ), )

Override _auth_url so file:// URLs work in tests

from custom_components.private_repo_loader import loader  # noqa: E402 loader._auth_url = lambda url, token: url

import shutil from pathlib import Path

import git import pytest

from custom_components.private_repo_loader.loader import sync_repo

@pytest.fixture def tmp_repo(tmp_path: Path) -> Path: """Create and commit in a temporary Git repo on branch 'main'.""" repo_dir = tmp_path / "repo" repo = git.Repo.init(repo_dir) # Create initial commit (repo_dir / "README.md").write_text("# test") repo.index.add(["README.md"]) repo.index.commit("initial") # Rename the default branch to 'main' repo.git.branch("-M", "main") return repo_dir

def test_sync_fresh_clone(tmp_repo: Path, tmp_path: Path) -> None: """sync_repo should clone a fresh repo.""" url = tmp_repo.as_uri() cfg = { "repository": url, "slug": "testrepo", "branch": "main", "token": "", } dest_root = tmp_path / "out" dest_root.mkdir() result = sync_repo(dest_root, cfg) assert result == "cloned" assert (dest_root / "testrepo" / "README.md").exists()

def test_sync_update(tmp_repo: Path, tmp_path: Path) -> None: """sync_repo should pull new commits onto an existing clone.""" cfg = { "repository": tmp_repo.as_uri(), "slug": "r", "branch": "main", "token": "", } dest = tmp_path / "out" shutil.copytree(tmp_repo, dest / "r")

# Ensure the copied repo has an 'origin' remote for updates
dest_repo = git.Repo(dest / "r")
dest_repo.create_remote("origin", tmp_repo.as_uri())

# Simulate upstream change
(tmp_repo / "foo.txt").write_text("bar")
upstream = git.Repo(tmp_repo)
upstream.index.add(["foo.txt"])
upstream.index.commit("add foo")
upstream.git.branch("-M", "main")

result = sync_repo(dest, cfg)
assert result == "updated"
assert (dest / "r" / "foo.txt").read_text() == "bar"

