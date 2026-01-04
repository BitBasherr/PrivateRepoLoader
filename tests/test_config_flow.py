"""Tests for the Private Repo Loader config flow."""

from unittest.mock import MagicMock

import pytest

from custom_components.private_repo_loader.config_flow import FlowHandler, OptionsFlow
from custom_components.private_repo_loader.const import (
    CONF_REPOS,
    CONF_TOKEN,
    CONF_REPO,
    CONF_SLUG,
    CONF_BRANCH,
)


class TestFlowHandler:
    """Test the FlowHandler config flow."""

    @pytest.fixture
    def flow_handler(self):
        """Create a FlowHandler instance."""
        handler = FlowHandler()
        handler.hass = MagicMock()
        handler._async_current_entries = MagicMock(return_value=[])
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
            }
        )
        return handler

    @pytest.mark.asyncio
    async def test_user_step_no_input_shows_form(self, flow_handler):
        """Test that no input shows the configuration form."""
        result = await flow_handler.async_step_user(user_input=None)
        assert result["type"] == "form"
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_user_step_with_token(self, flow_handler):
        """Test that submitting a token creates an entry."""
        result = await flow_handler.async_step_user(
            user_input={CONF_TOKEN: "test_token_123"}
        )
        assert result["type"] == "create_entry"
        assert result["title"] == "Private Repo Loader"
        assert result["options"][CONF_TOKEN] == "test_token_123"
        assert result["options"][CONF_REPOS] == []

    @pytest.mark.asyncio
    async def test_user_step_empty_token(self, flow_handler):
        """Test that submitting without a token still creates an entry."""
        result = await flow_handler.async_step_user(user_input={})
        assert result["type"] == "create_entry"
        assert result["options"][CONF_TOKEN] == ""
        assert result["options"][CONF_REPOS] == []

    @pytest.mark.asyncio
    async def test_single_instance_only(self, flow_handler):
        """Test that only one instance is allowed."""
        flow_handler._async_current_entries = MagicMock(
            return_value=[MagicMock()]  # Existing entry
        )
        result = await flow_handler.async_step_user(user_input=None)
        assert result["type"] == "abort"
        assert result["reason"] == "single_instance_allowed"


class TestOptionsFlow:
    """Test the OptionsFlow config flow."""

    @pytest.fixture
    def mock_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.options = {
            CONF_TOKEN: "default_token",
            CONF_REPOS: [
                {
                    CONF_REPO: "https://github.com/owner/repo",
                    CONF_SLUG: "test_repo",
                    CONF_BRANCH: "main",
                    CONF_TOKEN: "",
                }
            ],
        }
        return entry

    @pytest.fixture
    def mock_entry_empty(self):
        """Create a mock config entry with no repos."""
        entry = MagicMock()
        entry.options = {
            CONF_TOKEN: "default_token",
            CONF_REPOS: [],
        }
        return entry

    @pytest.fixture
    def options_flow(self, mock_entry):
        """Create an OptionsFlow instance with existing repos."""
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
        flow.async_show_menu = MagicMock(
            side_effect=lambda step_id, menu_options: {
                "type": "menu",
                "step_id": step_id,
                "menu_options": menu_options,
            }
        )
        return flow

    @pytest.fixture
    def options_flow_empty(self, mock_entry_empty):
        """Create an OptionsFlow instance with no repos."""
        flow = OptionsFlow(mock_entry_empty)
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
        flow.async_show_menu = MagicMock(
            side_effect=lambda step_id, menu_options: {
                "type": "menu",
                "step_id": step_id,
                "menu_options": menu_options,
            }
        )
        return flow

    @pytest.mark.asyncio
    async def test_init_step_with_repos_shows_menu(self, options_flow):
        """Test that with repos, init shows menu."""
        result = await options_flow.async_step_init(user_input=None)
        assert result["type"] == "menu"
        assert result["step_id"] == "init"
        assert "add" in result["menu_options"]
        assert "edit" in result["menu_options"]
        assert "remove" in result["menu_options"]
        assert "done" in result["menu_options"]

    @pytest.mark.asyncio
    async def test_init_step_no_repos_goes_to_add(self, options_flow_empty):
        """Test that without repos, init goes to add."""
        result = await options_flow_empty.async_step_init(user_input=None)
        assert result["type"] == "form"
        assert result["step_id"] == "add"

    @pytest.mark.asyncio
    async def test_add_step_shows_form(self, options_flow):
        """Test that add step shows form."""
        result = await options_flow.async_step_add(user_input=None)
        assert result["type"] == "form"
        assert result["step_id"] == "add"

    @pytest.mark.asyncio
    async def test_add_step_validates_required_fields(self, options_flow):
        """Test that add step validates required fields."""
        result = await options_flow.async_step_add(
            user_input={CONF_REPO: "", CONF_SLUG: ""}
        )
        assert result["type"] == "form"
        assert CONF_REPO in result["errors"]

    @pytest.mark.asyncio
    async def test_add_step_validates_url_format(self, options_flow):
        """Test that add step validates URL format."""
        result = await options_flow.async_step_add(
            user_input={CONF_REPO: "not-a-url", CONF_SLUG: "test"}
        )
        assert result["type"] == "form"
        assert result["errors"][CONF_REPO] == "invalid_url"

    @pytest.mark.asyncio
    async def test_add_step_success(self, options_flow):
        """Test that add step adds repo successfully."""
        # First initialize
        await options_flow.async_step_init(user_input=None)

        result = await options_flow.async_step_add(
            user_input={
                CONF_REPO: "https://github.com/new/repo",
                CONF_SLUG: "new_repo",
                CONF_BRANCH: "develop",
                CONF_TOKEN: "custom_token",
            }
        )
        assert result["type"] == "create_entry"
        repos = result["data"][CONF_REPOS]
        assert len(repos) == 2  # Original + new
        assert repos[1][CONF_SLUG] == "new_repo"

    @pytest.mark.asyncio
    async def test_done_step_saves(self, options_flow):
        """Test that done step saves and finishes."""
        # First initialize
        await options_flow.async_step_init(user_input=None)

        result = await options_flow.async_step_done(user_input=None)
        assert result["type"] == "create_entry"
        assert CONF_REPOS in result["data"]
