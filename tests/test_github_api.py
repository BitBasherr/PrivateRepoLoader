"""Tests for the GitHub API helper."""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from custom_components.private_repo_loader.github_api import (
    validate_token,
    validate_repo_access,
    list_user_repos,
    parse_github_url,
    GitHubError,
    GitHubRepoInfo,
)


class TestParseGitHubUrl:
    """Test the parse_github_url function."""

    def test_parse_https_url(self):
        """Test parsing standard HTTPS URL."""
        result = parse_github_url("https://github.com/owner/repo")
        assert result == ("owner", "repo")

    def test_parse_https_url_with_git_suffix(self):
        """Test parsing HTTPS URL with .git suffix."""
        result = parse_github_url("https://github.com/owner/repo.git")
        assert result == ("owner", "repo")

    def test_parse_https_url_with_trailing_slash(self):
        """Test parsing HTTPS URL with trailing slash."""
        result = parse_github_url("https://github.com/owner/repo/")
        assert result == ("owner", "repo")

    def test_parse_ssh_url(self):
        """Test parsing SSH URL."""
        result = parse_github_url("git@github.com:owner/repo.git")
        assert result == ("owner", "repo")

    def test_parse_ssh_url_without_git_suffix(self):
        """Test parsing SSH URL without .git suffix."""
        result = parse_github_url("git@github.com:owner/repo")
        assert result == ("owner", "repo")

    def test_parse_empty_url(self):
        """Test parsing empty URL."""
        result = parse_github_url("")
        assert result is None

    def test_parse_invalid_url(self):
        """Test parsing invalid URL."""
        result = parse_github_url("not-a-github-url")
        assert result is None

    def test_parse_bitbasherr_private_repo(self):
        """Test parsing BitBasherr private repo URL."""
        result = parse_github_url("https://github.com/BitBasherr/Custom-Entity-Private")
        assert result == ("BitBasherr", "Custom-Entity-Private")

    def test_parse_bitbasherr_public_repo(self):
        """Test parsing BitBasherr public repo URL."""
        result = parse_github_url("https://github.com/BitBasherr/Custom-Entity")
        assert result == ("BitBasherr", "Custom-Entity")


class TestValidateToken:
    """Test the validate_token function."""

    @pytest.mark.asyncio
    async def test_empty_token_returns_invalid(self):
        """Test that empty token returns invalid result."""
        result = await validate_token("")
        assert result.valid is False
        assert result.error == GitHubError.INVALID_TOKEN

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_valid_token_returns_username(self, mock_session_class):
        """Test that valid token returns username."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"login": "testuser"})

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await validate_token("valid_token")
        assert result.valid is True
        assert result.username == "testuser"

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_invalid_token_returns_error(self, mock_session_class):
        """Test that invalid token returns error."""
        mock_response = AsyncMock()
        mock_response.status = 401

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await validate_token("invalid_token")
        assert result.valid is False
        assert result.error == GitHubError.INVALID_TOKEN

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_rate_limited_returns_error(self, mock_session_class):
        """Test that rate limiting returns error."""
        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.headers = {"X-RateLimit-Remaining": "0"}

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await validate_token("token")
        assert result.valid is False
        assert result.error == GitHubError.RATE_LIMITED


class TestValidateRepoAccess:
    """Test the validate_repo_access function."""

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_accessible_repo_returns_valid(self, mock_session_class):
        """Test that accessible repo returns valid."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "full_name": "owner/repo",
                "private": True,
            }
        )

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await validate_repo_access("token", "owner", "repo")
        assert result.valid is True
        assert result.repo_info is not None

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_private_repo_without_token_returns_not_found(
        self, mock_session_class
    ):
        """Test that private repo without token returns not found."""
        mock_response = AsyncMock()
        mock_response.status = 404

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await validate_repo_access("", "BitBasherr", "Custom-Entity-Private")
        assert result.valid is False
        assert result.error == GitHubError.REPO_NOT_FOUND
        assert "PAT" in result.error_message

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_private_repo_with_bad_token_returns_not_found(
        self, mock_session_class
    ):
        """Test that private repo with bad token returns not found."""
        mock_response = AsyncMock()
        mock_response.status = 404

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await validate_repo_access(
            "bad_token", "BitBasherr", "Custom-Entity-Private"
        )
        assert result.valid is False
        assert result.error == GitHubError.REPO_NOT_FOUND
        assert (
            "repo" in result.error_message.lower()
            or "scope" in result.error_message.lower()
        )

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_insufficient_permissions_returns_error(self, mock_session_class):
        """Test that 403 returns insufficient permissions."""
        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.headers = {"X-RateLimit-Remaining": "100"}

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await validate_repo_access("token", "owner", "repo")
        assert result.valid is False
        assert result.error == GitHubError.INSUFFICIENT_PERMISSIONS


class TestListUserRepos:
    """Test the list_user_repos function."""

    @pytest.mark.asyncio
    async def test_empty_token_returns_empty_list(self):
        """Test that empty token returns empty list."""
        result = await list_user_repos("")
        assert result == []

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_returns_repo_list(self, mock_session_class):
        """Test that valid token returns repo list."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=[
                {
                    "full_name": "owner/repo1",
                    "name": "repo1",
                    "private": False,
                    "html_url": "https://github.com/owner/repo1",
                    "clone_url": "https://github.com/owner/repo1.git",
                    "default_branch": "main",
                    "description": "Test repo 1",
                },
                {
                    "full_name": "owner/repo2",
                    "name": "repo2",
                    "private": True,
                    "html_url": "https://github.com/owner/repo2",
                    "clone_url": "https://github.com/owner/repo2.git",
                    "default_branch": "master",
                    "description": None,
                },
            ]
        )

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await list_user_repos("valid_token")
        assert len(result) == 2
        assert result[0].full_name == "owner/repo1"
        assert result[0].private is False
        assert result[1].full_name == "owner/repo2"
        assert result[1].private is True


class TestGitHubRepoInfo:
    """Test GitHubRepoInfo dataclass."""

    def test_repo_info_creation(self):
        """Test creating a GitHubRepoInfo instance."""
        info = GitHubRepoInfo(
            full_name="BitBasherr/Custom-Entity-Private",
            name="Custom-Entity-Private",
            private=True,
            html_url="https://github.com/BitBasherr/Custom-Entity-Private",
            clone_url="https://github.com/BitBasherr/Custom-Entity-Private.git",
            default_branch="main",
            description="Private test repo",
        )
        assert info.full_name == "BitBasherr/Custom-Entity-Private"
        assert info.private is True
        assert info.default_branch == "main"


class TestPrivateRepoScenarios:
    """Test scenarios specific to private repositories."""

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_bitbasherr_custom_entity_private_with_valid_token(
        self, mock_session_class
    ):
        """Test accessing BitBasherr/Custom-Entity-Private with valid token."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "full_name": "BitBasherr/Custom-Entity-Private",
                "name": "Custom-Entity-Private",
                "private": True,
                "html_url": "https://github.com/BitBasherr/Custom-Entity-Private",
                "clone_url": "https://github.com/BitBasherr/Custom-Entity-Private.git",
                "default_branch": "main",
            }
        )

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await validate_repo_access(
            "valid_pat_with_repo_scope", "BitBasherr", "Custom-Entity-Private"
        )
        assert result.valid is True
        assert result.repo_info["private"] is True

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_bitbasherr_custom_entity_public_without_token(
        self, mock_session_class
    ):
        """Test accessing BitBasherr/Custom-Entity (public) without token."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "full_name": "BitBasherr/Custom-Entity",
                "name": "Custom-Entity",
                "private": False,
                "html_url": "https://github.com/BitBasherr/Custom-Entity",
                "clone_url": "https://github.com/BitBasherr/Custom-Entity.git",
                "default_branch": "main",
            }
        )

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await validate_repo_access(
            "",  # No token needed for public repos
            "BitBasherr",
            "Custom-Entity",
        )
        assert result.valid is True
        assert result.repo_info["private"] is False
