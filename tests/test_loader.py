# tests/test_loader.py

from pathlib import Path
import shutil

import git
import pytest

from custom_components.private_repo_loader.loader import sync_repo, sync_repo_detailed


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create and commit in a temporary Git repo on branch 'main'."""
    repo_dir = tmp_path / "repo"
    repo = git.Repo.init(repo_dir)
    (repo_dir / "README.md").write_text("# test")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
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


def test_sync_fresh_clone_detailed(tmp_repo: Path, tmp_path: Path) -> None:
    """sync_repo_detailed should return full result for fresh clone."""
    url = tmp_repo.as_uri()
    cfg = {
        "repository": url,
        "slug": "testrepo",
        "branch": "main",
        "token": "",
    }
    dest_root = tmp_path / "out"
    dest_root.mkdir()

    result = sync_repo_detailed(dest_root, cfg)
    assert result.status == "cloned"
    assert result.has_changes is True
    assert result.commit_sha is not None
    assert result.error is None


def test_sync_update(tmp_repo: Path, tmp_path: Path) -> None:
    """sync_repo should pull new commits onto an existing clone."""
    url = tmp_repo.as_uri()
    cfg = {
        "repository": url,
        "slug": "r",
        "branch": "main",
        "token": "",
    }
    dest_root = tmp_path / "out"
    dest_root.mkdir()

    # copy the repo in place to simulate an existing clone
    shutil.copytree(tmp_repo, dest_root / "r")

    # add an 'origin' remote and set upstream for pulls
    dest_repo = git.Repo(dest_root / "r")
    dest_repo.create_remote("origin", url)
    dest_repo.git.fetch()
    dest_repo.git.branch(
        "--set-upstream-to=origin/main",
        "main",
    )

    # simulate upstream change
    (tmp_repo / "foo.txt").write_text("bar")
    upstream = git.Repo(tmp_repo)
    upstream.index.add(["foo.txt"])
    upstream.index.commit("add foo")
    upstream.git.branch("-M", "main")

    result = sync_repo(dest_root, cfg)
    assert result == "updated"
    assert (dest_root / "r" / "foo.txt").read_text() == "bar"


def test_sync_update_detailed_with_changes(tmp_repo: Path, tmp_path: Path) -> None:
    """sync_repo_detailed should detect changes on update."""
    url = tmp_repo.as_uri()
    cfg = {
        "repository": url,
        "slug": "r",
        "branch": "main",
        "token": "",
    }
    dest_root = tmp_path / "out"
    dest_root.mkdir()

    # copy the repo in place to simulate an existing clone
    shutil.copytree(tmp_repo, dest_root / "r")

    # add an 'origin' remote and set upstream for pulls
    dest_repo = git.Repo(dest_root / "r")
    dest_repo.create_remote("origin", url)
    dest_repo.git.fetch()
    dest_repo.git.branch(
        "--set-upstream-to=origin/main",
        "main",
    )

    # simulate upstream change
    (tmp_repo / "foo.txt").write_text("bar")
    upstream = git.Repo(tmp_repo)
    upstream.index.add(["foo.txt"])
    upstream.index.commit("add foo")
    upstream.git.branch("-M", "main")

    result = sync_repo_detailed(dest_root, cfg)
    assert result.status == "updated"
    assert result.has_changes is True
    assert result.commit_sha is not None


def test_sync_no_changes(tmp_repo: Path, tmp_path: Path) -> None:
    """sync_repo_detailed should detect no changes."""
    url = tmp_repo.as_uri()
    cfg = {
        "repository": url,
        "slug": "r",
        "branch": "main",
        "token": "",
    }
    dest_root = tmp_path / "out"
    dest_root.mkdir()

    # copy the repo in place to simulate an existing clone
    shutil.copytree(tmp_repo, dest_root / "r")

    # add an 'origin' remote and set upstream for pulls
    dest_repo = git.Repo(dest_root / "r")
    dest_repo.create_remote("origin", url)
    dest_repo.git.fetch()
    dest_repo.git.branch(
        "--set-upstream-to=origin/main",
        "main",
    )

    # No upstream changes - should detect "unchanged"
    result = sync_repo_detailed(dest_root, cfg)
    assert result.status == "unchanged"
    assert result.has_changes is False


def test_sync_empty_url(tmp_path: Path) -> None:
    """sync_repo should handle empty URL gracefully."""
    cfg = {
        "repository": "",
        "slug": "testrepo",
        "branch": "main",
        "token": "",
    }
    dest_root = tmp_path / "out"
    dest_root.mkdir()

    result = sync_repo(dest_root, cfg)
    assert result == "skipped"


def test_sync_empty_url_detailed(tmp_path: Path) -> None:
    """sync_repo_detailed should return error for empty URL."""
    cfg = {
        "repository": "",
        "slug": "testrepo",
        "branch": "main",
        "token": "",
    }
    dest_root = tmp_path / "out"
    dest_root.mkdir()

    result = sync_repo_detailed(dest_root, cfg)
    assert result.status == "skipped"
    assert result.error is not None


def test_sync_missing_url(tmp_path: Path) -> None:
    """sync_repo should handle missing URL gracefully."""
    cfg = {
        "slug": "testrepo",
        "branch": "main",
        "token": "",
    }
    dest_root = tmp_path / "out"
    dest_root.mkdir()

    result = sync_repo(dest_root, cfg)
    assert result == "skipped"


def test_sync_slug_from_url(tmp_repo: Path, tmp_path: Path) -> None:
    """sync_repo should extract slug from URL if not provided."""
    url = tmp_repo.as_uri()
    cfg = {
        "repository": url,
        # No slug provided - should be extracted from URL
        "branch": "main",
        "token": "",
    }
    dest_root = tmp_path / "out"
    dest_root.mkdir()

    result = sync_repo(dest_root, cfg)
    assert result == "cloned"
    # The slug should be extracted as "repo" from the URL
    assert (dest_root / "repo" / "README.md").exists()
