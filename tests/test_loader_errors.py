"""Tests for the loader error handling and PAT permission detection."""

from pathlib import Path
import json

import git
import pytest

from custom_components.private_repo_loader.loader import (
    sync_repo_detailed,
    _parse_git_error,
    SyncResult,
)


class TestParseGitError:
    """Test the _parse_git_error function."""

    def test_authentication_failed(self):
        """Test parsing authentication failure."""
        error_type, message = _parse_git_error(
            "Authentication failed for 'https://...'"
        )
        assert error_type == "auth"
        assert "PAT" in message

    def test_401_unauthorized(self):
        """Test parsing 401 Unauthorized."""
        error_type, message = _parse_git_error("fatal: 401 Unauthorized")
        assert error_type == "auth"

    def test_403_forbidden(self):
        """Test parsing 403 Forbidden."""
        error_type, message = _parse_git_error("fatal: 403 Forbidden")
        assert error_type == "permission"
        assert "repo" in message.lower() or "scope" in message.lower()

    def test_404_not_found(self):
        """Test parsing 404 Not Found."""
        error_type, message = _parse_git_error(
            "fatal: repository 'https://...' not found"
        )
        assert error_type == "not_found"

    def test_remote_hung_up(self):
        """Test parsing remote hung up."""
        error_type, message = _parse_git_error("fatal: remote hung up unexpectedly")
        assert error_type == "network"

    def test_could_not_read_from_remote(self):
        """Test parsing could not read from remote."""
        error_type, message = _parse_git_error(
            "fatal: Could not read from remote repository"
        )
        assert error_type == "network"

    def test_unknown_error(self):
        """Test parsing unknown error."""
        error_type, message = _parse_git_error("Some random error")
        assert error_type == "unknown"
        assert message == "Some random error"


class TestSyncResultErrorTypes:
    """Test SyncResult error_type field."""

    def test_sync_result_with_error_type(self):
        """Test SyncResult creation with error_type."""
        result = SyncResult(
            status="skipped",
            error="Permission denied",
            error_type="permission",
        )
        assert result.status == "skipped"
        assert result.error_type == "permission"

    def test_sync_result_default_error_type(self):
        """Test SyncResult default error_type is None."""
        result = SyncResult(status="cloned")
        assert result.error_type is None


class TestUrlValidation:
    """Test URL validation in sync_repo_detailed."""

    def test_invalid_url_scheme(self, tmp_path: Path):
        """Test that invalid URL scheme returns config error."""
        cfg = {
            "repository": "git@github.com:owner/repo.git",
            "slug": "testrepo",
            "branch": "main",
            "token": "",
        }
        custom_components = tmp_path / "config" / "custom_components"
        custom_components.mkdir(parents=True)

        result = sync_repo_detailed(custom_components, cfg)
        assert result.status == "skipped"
        assert result.error_type == "config"
        assert "https" in result.error.lower()

    def test_empty_url(self, tmp_path: Path):
        """Test that empty URL returns config error."""
        cfg = {
            "repository": "",
            "slug": "testrepo",
            "branch": "main",
            "token": "",
        }
        custom_components = tmp_path / "config" / "custom_components"
        custom_components.mkdir(parents=True)

        result = sync_repo_detailed(custom_components, cfg)
        assert result.status == "skipped"
        assert result.error_type == "config"
        assert "empty" in result.error.lower()


class TestPrivateRepoCloning:
    """Test private repository cloning scenarios."""

    @pytest.fixture
    def tmp_repo(self, tmp_path: Path) -> Path:
        """Create a repo with proper custom_components structure."""
        repo_dir = tmp_path / "repo"
        integration_dir = repo_dir / "custom_components" / "testrepo"
        integration_dir.mkdir(parents=True)

        manifest = {
            "domain": "testrepo",
            "name": "Test Repo",
            "version": "1.0.0",
        }
        (integration_dir / "manifest.json").write_text(json.dumps(manifest))
        (integration_dir / "__init__.py").write_text("# Test integration")
        (repo_dir / "README.md").write_text("# test")

        repo = git.Repo.init(repo_dir)
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
    def tmp_config(self, tmp_path: Path) -> Path:
        """Create a temporary HA config directory structure."""
        custom_components = tmp_path / "config" / "custom_components"
        custom_components.mkdir(parents=True)
        return custom_components

    def test_successful_clone_returns_changes(self, tmp_repo: Path, tmp_config: Path):
        """Test successful clone returns has_changes=True."""
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
        assert result.error_type is None

    def test_no_changes_returns_unchanged(self, tmp_repo: Path, tmp_config: Path):
        """Test no changes returns has_changes=False."""
        url = tmp_repo.as_uri()
        cfg = {
            "repository": url,
            "slug": "testrepo",
            "branch": "main",
            "token": "",
        }

        # First clone
        sync_repo_detailed(tmp_config, cfg)

        # Sync without any upstream changes
        result = sync_repo_detailed(tmp_config, cfg)
        assert result.status == "unchanged"
        assert result.has_changes is False
        assert result.error is None

    def test_update_returns_changes(self, tmp_repo: Path, tmp_config: Path):
        """Test update returns has_changes=True."""
        url = tmp_repo.as_uri()
        cfg = {
            "repository": url,
            "slug": "testrepo",
            "branch": "main",
            "token": "",
        }

        # First clone
        sync_repo_detailed(tmp_config, cfg)

        # Make a change to the upstream integration
        integration_dir = tmp_repo / "custom_components" / "testrepo"
        (integration_dir / "NEW_FILE.py").write_text("# new content")
        upstream = git.Repo(tmp_repo)
        upstream.index.add(["custom_components/testrepo/NEW_FILE.py"])
        upstream.index.commit("add new file")

        # Sync with upstream changes
        result = sync_repo_detailed(tmp_config, cfg)
        assert result.status == "updated"
        assert result.has_changes is True
        assert result.error is None
