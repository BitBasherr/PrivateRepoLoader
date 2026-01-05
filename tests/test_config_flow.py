"""Tests for the Private Repo Loader config flow."""

from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from custom_components.private_repo_loader.config_flow import FlowHandler, OptionsFlow
from custom_components.private_repo_loader.const import (
    CONF_TOKEN,
    CONF_REPO,
    CONF_SLUG,
    CONF_BRANCH,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_BRANCH,
)
from custom_components.private_repo_loader.github_api import (
    GitHubValidationResult,
    GitHubError,
)


class TestFlowHandler:
    """Test the FlowHandler config flow."""

    @pytest.fixture
    def flow_handler(self):
        """Create a FlowHandler instance."""
        handler = FlowHandler()
        handler.hass = MagicMock()
        handler._async_current_entries = MagicMock(return_value=[])
        handler.async_set_unique_id = AsyncMock()
        handler._abort_if_unique_id_configured = MagicMock()
        handler.async_abort = MagicMock(
            side_effect=lambda reason: {"type": "abort", "reason": reason}
        )
        handler.async_create_entry = MagicMock(
            side_effect=lambda title, data, options: {
                "type": "create_entry",
                "title": title,
                "data": data,
                "options": options,
            }
        )
        handler.async_show_form = MagicMock(
            side_effect=lambda step_id, data_schema, **kwargs: {
                "type": "form",
                "step_id": step_id,
                "errors": kwargs.get("errors", {}),
            }
        )
        return handler

    @pytest.mark.asyncio
    async def test_user_step_no_input_shows_form(self, flow_handler):
        """Test that no input shows the token form."""
        result = await flow_handler.async_step_user(user_input=None)
        assert result["type"] == "form"
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_user_step_empty_token_goes_to_manual(self, flow_handler):
        """Test that empty token goes to manual entry step."""
        result = await flow_handler.async_step_user(user_input={CONF_TOKEN: ""})
        assert result["type"] == "form"
        assert result["step_id"] == "manual"

    @pytest.mark.asyncio
    @patch("custom_components.private_repo_loader.config_flow.validate_token")
    @patch("custom_components.private_repo_loader.config_flow.list_user_repos")
    async def test_user_step_valid_token_goes_to_select(
        self, mock_list_repos, mock_validate, flow_handler
    ):
        """Test that valid token goes to repo selection step."""
        mock_validate.return_value = GitHubValidationResult(
            valid=True, username="testuser"
        )
        mock_list_repos.return_value = []

        result = await flow_handler.async_step_user(
            user_input={CONF_TOKEN: "valid_token"}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "select_repo"

    @pytest.mark.asyncio
    @patch("custom_components.private_repo_loader.config_flow.validate_token")
    async def test_user_step_invalid_token_shows_error(
        self, mock_validate, flow_handler
    ):
        """Test that invalid token shows error."""
        mock_validate.return_value = GitHubValidationResult(
            valid=False,
            error=GitHubError.INVALID_TOKEN,
            error_message="Invalid token",
        )

        result = await flow_handler.async_step_user(
            user_input={CONF_TOKEN: "bad_token"}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert CONF_TOKEN in result["errors"]

    @pytest.mark.asyncio
    @patch("custom_components.private_repo_loader.config_flow.validate_repo_access")
    async def test_manual_step_creates_entry(self, mock_validate_repo, flow_handler):
        """Test that manual step creates entry with valid input."""
        mock_validate_repo.return_value = GitHubValidationResult(valid=True)

        result = await flow_handler.async_step_manual(
            user_input={
                CONF_REPO: "https://github.com/owner/repo",
                CONF_SLUG: "test_repo",
                CONF_BRANCH: "main",
                CONF_TOKEN: "test_token_123",
                CONF_POLL_INTERVAL: 5,
            }
        )
        assert result["type"] == "create_entry"
        assert result["title"] == "test_repo"
        assert result["data"][CONF_REPO] == "https://github.com/owner/repo"
        assert result["data"][CONF_SLUG] == "test_repo"
        assert result["options"][CONF_POLL_INTERVAL] == 5

    @pytest.mark.asyncio
    async def test_manual_step_validates_required_repo(self, flow_handler):
        """Test that repo URL is required."""
        result = await flow_handler.async_step_manual(
            user_input={
                CONF_REPO: "",
                CONF_SLUG: "test_repo",
            }
        )
        assert result["type"] == "form"
        assert CONF_REPO in result["errors"]

    @pytest.mark.asyncio
    async def test_manual_step_validates_url_format(self, flow_handler):
        """Test that URL must start with https://."""
        result = await flow_handler.async_step_manual(
            user_input={
                CONF_REPO: "git@github.com:owner/repo.git",
                CONF_SLUG: "test_repo",
            }
        )
        assert result["type"] == "form"
        assert result["errors"][CONF_REPO] == "invalid_url"

    @pytest.mark.asyncio
    @patch("custom_components.private_repo_loader.config_flow.validate_repo_access")
    async def test_manual_step_auto_detects_slug(
        self, mock_validate_repo, flow_handler
    ):
        """Test that slug is auto-detected from URL if not provided."""
        mock_validate_repo.return_value = GitHubValidationResult(valid=True)

        result = await flow_handler.async_step_manual(
            user_input={
                CONF_REPO: "https://github.com/owner/my-integration",
                CONF_SLUG: "",  # Empty slug - should be auto-detected
                CONF_BRANCH: "main",
                CONF_TOKEN: "",
                CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
            }
        )
        assert result["type"] == "create_entry"
        assert result["data"][CONF_SLUG] == "my-integration"

    @pytest.mark.asyncio
    @patch("custom_components.private_repo_loader.config_flow.validate_repo_access")
    async def test_manual_step_repo_not_found_error(
        self, mock_validate_repo, flow_handler
    ):
        """Test that repo not found shows error."""
        mock_validate_repo.return_value = GitHubValidationResult(
            valid=False,
            error=GitHubError.REPO_NOT_FOUND,
            error_message="Repository not found",
        )

        result = await flow_handler.async_step_manual(
            user_input={
                CONF_REPO: "https://github.com/owner/nonexistent",
                CONF_SLUG: "test_repo",
                CONF_BRANCH: "main",
                CONF_TOKEN: "token",
                CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
            }
        )
        assert result["type"] == "form"
        assert result["errors"][CONF_REPO] == "repo_not_found"

    @pytest.mark.asyncio
    @patch("custom_components.private_repo_loader.config_flow.validate_repo_access")
    async def test_manual_step_permission_error(self, mock_validate_repo, flow_handler):
        """Test that permission error shows error on token field."""
        mock_validate_repo.return_value = GitHubValidationResult(
            valid=False,
            error=GitHubError.INSUFFICIENT_PERMISSIONS,
            error_message="Token lacks permissions",
        )

        result = await flow_handler.async_step_manual(
            user_input={
                CONF_REPO: "https://github.com/owner/private-repo",
                CONF_SLUG: "test_repo",
                CONF_BRANCH: "main",
                CONF_TOKEN: "bad_token",
                CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
            }
        )
        assert result["type"] == "form"
        assert result["errors"][CONF_TOKEN] == "insufficient_permissions"


class TestOptionsFlow:
    """Test the OptionsFlow config flow."""

    @pytest.fixture
    def mock_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.data = {
            CONF_REPO: "https://github.com/owner/repo",
            CONF_SLUG: "test_repo",
            CONF_BRANCH: "main",
            CONF_TOKEN: "default_token",
        }
        entry.options = {
            CONF_BRANCH: "main",
            CONF_TOKEN: "default_token",
            CONF_POLL_INTERVAL: 5,
        }
        return entry

    @pytest.fixture
    def options_flow(self, mock_entry):
        """Create an OptionsFlow instance."""
        flow = OptionsFlow(mock_entry)
        flow.async_create_entry = MagicMock(
            side_effect=lambda title, data: {"type": "create_entry", "data": data}
        )
        flow.async_show_form = MagicMock(
            side_effect=lambda step_id, data_schema, **kwargs: {
                "type": "form",
                "step_id": step_id,
                "errors": kwargs.get("errors", {}),
            }
        )
        return flow

    @pytest.mark.asyncio
    async def test_init_step_shows_form(self, options_flow):
        """Test that init step shows options form."""
        result = await options_flow.async_step_init(user_input=None)
        assert result["type"] == "form"
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_init_step_saves_options(self, options_flow):
        """Test that submitting options saves them."""
        result = await options_flow.async_step_init(
            user_input={
                CONF_BRANCH: "develop",
                CONF_TOKEN: "new_token",
                CONF_POLL_INTERVAL: 10,
            }
        )
        assert result["type"] == "create_entry"
        assert result["data"][CONF_BRANCH] == "develop"
        assert result["data"][CONF_TOKEN] == "new_token"
        assert result["data"][CONF_POLL_INTERVAL] == 10

    @pytest.mark.asyncio
    async def test_options_preserve_defaults(self, options_flow, mock_entry):
        """Test that empty values use defaults."""
        result = await options_flow.async_step_init(
            user_input={
                CONF_BRANCH: "",
                CONF_TOKEN: "",
                CONF_POLL_INTERVAL: 1,
            }
        )
        assert result["type"] == "create_entry"
        assert result["data"][CONF_BRANCH] == DEFAULT_BRANCH
        assert result["data"][CONF_TOKEN] == ""
