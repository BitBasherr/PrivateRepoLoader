# tests/test_loader.py

from pathlib import Path
import json

import git
import pytest

from custom_components.private_repo_loader.loader import (
    sync_repo,
    sync_repo_detailed,
    _find_integration_in_repo,
    _get_staging_path,
    STAGING_DIR_NAME,
)


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a temporary Git repo with proper custom_components structure."""
    repo_dir = tmp_path / "repo"
    repo = git.Repo.init(repo_dir)

    # Create proper custom_components structure
    integration_dir = repo_dir / "custom_components" / "testrepo"
    integration_dir.mkdir(parents=True)

    # Create manifest.json (required for HA integrations)
    manifest = {
        "domain": "testrepo",
        "name": "Test Repo",
        "version": "1.0.0",
        "documentation": "https://example.com",
        "requirements": [],
        "codeowners": ["@test"],
    }
    (integration_dir / "manifest.json").write_text(json.dumps(manifest))
    (integration_dir / "__init__.py").write_text("# Test integration")
    (repo_dir / "README.md").write_text("# test")

    repo.index.add(
        [
            "README.md",
            "custom_components/testrepo/manifest.json",
            "custom_components/testrepo/__init__.py",
        ]
    )
    repo.index.commit("initial")
    repo.git.branch("-M", "main")
    return repo_dir


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Create a temporary HA config directory structure."""
    config_dir = tmp_path / "config"
    custom_components = config_dir / "custom_components"
    custom_components.mkdir(parents=True)
    return custom_components


def test_sync_fresh_clone(tmp_repo: Path, tmp_config: Path) -> None:
    """sync_repo should clone a fresh repo and extract integration."""
    url = tmp_repo.as_uri()
    cfg = {
        "repository": url,
        "slug": "testrepo",
        "branch": "main",
        "token": "",
    }

    result = sync_repo(tmp_config, cfg)
    assert result == "cloned"
    # The integration should be in custom_components/testrepo
    assert (tmp_config / "testrepo" / "manifest.json").exists()
    assert (tmp_config / "testrepo" / "__init__.py").exists()
    # Staging area should exist
    staging_dir = tmp_config.parent / STAGING_DIR_NAME / "testrepo"
    assert staging_dir.exists()


def test_sync_fresh_clone_detailed(tmp_repo: Path, tmp_config: Path) -> None:
    """sync_repo_detailed should return full result for fresh clone."""
    url = tmp_repo.as_uri()
    cfg = {
        "repository": url,
        "slug": "testrepo",
        "branch": "main",
        "token": "",
    }

    result = sync_repo_detailed(tmp_config, cfg)
    assert result.status == "cloned"
    assert result.has_changes is True
    assert result.commit_sha is not None
    assert result.error is None


def test_sync_update(tmp_repo: Path, tmp_config: Path) -> None:
    """sync_repo should pull new commits and update the integration."""
    url = tmp_repo.as_uri()
    cfg = {
        "repository": url,
        "slug": "testrepo",
        "branch": "main",
        "token": "",
    }

    # First clone
    result = sync_repo(tmp_config, cfg)
    assert result == "cloned"

    # Simulate upstream change in the integration
    integration_dir = tmp_repo / "custom_components" / "testrepo"
    (integration_dir / "new_file.py").write_text("# New file")
    upstream = git.Repo(tmp_repo)
    upstream.index.add(["custom_components/testrepo/new_file.py"])
    upstream.index.commit("add new file")

    # Sync again - should detect update
    result = sync_repo(tmp_config, cfg)
    assert result == "updated"
    # New file should be in destination
    assert (tmp_config / "testrepo" / "new_file.py").exists()


def test_sync_update_detailed_with_changes(tmp_repo: Path, tmp_config: Path) -> None:
    """sync_repo_detailed should detect changes on update."""
    url = tmp_repo.as_uri()
    cfg = {
        "repository": url,
        "slug": "testrepo",
        "branch": "main",
        "token": "",
    }

    # First clone
    sync_repo_detailed(tmp_config, cfg)

    # Simulate upstream change
    integration_dir = tmp_repo / "custom_components" / "testrepo"
    (integration_dir / "updated.py").write_text("# Updated")
    upstream = git.Repo(tmp_repo)
    upstream.index.add(["custom_components/testrepo/updated.py"])
    upstream.index.commit("add updated file")

    # Sync again
    result = sync_repo_detailed(tmp_config, cfg)
    assert result.status == "updated"
    assert result.has_changes is True
    assert result.commit_sha is not None


def test_sync_no_changes(tmp_repo: Path, tmp_config: Path) -> None:
    """sync_repo_detailed should detect no changes."""
    url = tmp_repo.as_uri()
    cfg = {
        "repository": url,
        "slug": "testrepo",
        "branch": "main",
        "token": "",
    }

    # First clone
    sync_repo_detailed(tmp_config, cfg)

    # Sync again without upstream changes - should detect "unchanged"
    result = sync_repo_detailed(tmp_config, cfg)
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


def test_sync_slug_from_url(tmp_repo: Path, tmp_config: Path) -> None:
    """sync_repo should extract slug from URL if not provided."""
    url = tmp_repo.as_uri()
    cfg = {
        "repository": url,
        # No slug provided - should be extracted from URL
        "branch": "main",
        "token": "",
    }

    result = sync_repo(tmp_config, cfg)
    assert result == "cloned"
    # The integration should be "testrepo" from the custom_components folder
    assert (tmp_config / "testrepo" / "manifest.json").exists()


def test_find_integration_standard_structure(tmp_path: Path) -> None:
    """Test finding integration in standard custom_components/<integration> structure."""
    repo_dir = tmp_path / "repo"
    integration_dir = repo_dir / "custom_components" / "my_integration"
    integration_dir.mkdir(parents=True)
    (integration_dir / "manifest.json").write_text('{"domain": "my_integration"}')
    (integration_dir / "__init__.py").write_text("")

    result = _find_integration_in_repo(repo_dir, "my_integration")
    assert result is not None
    assert result.name == "my_integration"


def test_find_integration_flat_structure(tmp_path: Path) -> None:
    """Test finding integration in flat structure (files at repo root)."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "manifest.json").write_text('{"domain": "flat_integration"}')
    (repo_dir / "__init__.py").write_text("")

    result = _find_integration_in_repo(repo_dir, "flat_integration")
    assert result is not None
    assert result == repo_dir


def test_find_integration_not_found(tmp_path: Path) -> None:
    """Test that None is returned when no integration is found."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "README.md").write_text("# Just a readme")

    result = _find_integration_in_repo(repo_dir, "nonexistent")
    assert result is None


def test_staging_path(tmp_path: Path) -> None:
    """Test that staging path is created correctly."""
    config_root = tmp_path / "config"
    config_root.mkdir()

    staging = _get_staging_path(config_root, "my_repo")
    assert staging == config_root / STAGING_DIR_NAME / "my_repo"
    assert staging.parent.exists()


def test_sync_invalid_structure(tmp_path: Path, tmp_config: Path) -> None:
    """Test sync with repo that doesn't have custom_components structure."""
    # Create a repo without custom_components structure
    repo_dir = tmp_path / "bad_repo"
    repo = git.Repo.init(repo_dir)
    (repo_dir / "README.md").write_text("# Just a readme")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    repo.git.branch("-M", "main")

    url = repo_dir.as_uri()
    cfg = {
        "repository": url,
        "slug": "bad_repo",
        "branch": "main",
        "token": "",
    }

    result = sync_repo_detailed(tmp_config, cfg)
    assert result.status == "skipped"
    assert result.error is not None
    assert "custom component" in result.error.lower()
