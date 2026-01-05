"""Config- and options-flow for Private Repo Loader.

Each repository is now its own config entry, allowing individual management
and proper linking from the integrations page.
"""

from __future__ import annotations

import logging
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_REPO,
    CONF_BRANCH,
    CONF_SLUG,
    CONF_POLL_INTERVAL,
    DEFAULT_BRANCH,
    DEFAULT_POLL_INTERVAL,
)
from .github_api import (
    validate_token,
    validate_repo_access,
    list_user_repos,
    parse_github_url,
    GitHubError,
)

_LOGGER = logging.getLogger(__name__)


def _generate_unique_id(repo_url: str, slug: str) -> str:
    """Generate a unique ID for a repository entry."""
    return f"{DOMAIN}_{slug}"


class FlowHandler(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle adding a new private repository.

    Each repository is a separate config entry.
    Implements a two-step flow:
    1. Enter PAT token (optional for public repos)
    2. Select from available repos or enter URL manually
    """

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the flow handler."""
        self._token: str = ""
        self._available_repos: list[Any] = []
        self._username: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Get the GitHub PAT token."""
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}

        if user_input is not None:
            token = user_input.get(CONF_TOKEN, "").strip()
            self._token = token

            if token:
                # Validate the token
                result = await validate_token(token)
                if result.valid:
                    self._username = result.username
                    _LOGGER.info("GitHub token validated for user: %s", result.username)

                    # Fetch available repos
                    self._available_repos = await list_user_repos(token)
                    _LOGGER.info(
                        "Found %d repositories for user %s",
                        len(self._available_repos),
                        result.username,
                    )

                    return await self.async_step_select_repo()
                else:
                    if result.error == GitHubError.INVALID_TOKEN:
                        errors[CONF_TOKEN] = "invalid_token"
                    elif result.error == GitHubError.RATE_LIMITED:
                        errors[CONF_TOKEN] = "rate_limited"
                    elif result.error == GitHubError.NETWORK_ERROR:
                        errors["base"] = "network_error"
                    else:
                        errors[CONF_TOKEN] = "unknown_error"

                    if result.error_message:
                        description_placeholders["error_detail"] = result.error_message
            else:
                # No token provided - go directly to manual entry
                return await self.async_step_manual()

        schema = vol.Schema(
            {
                vol.Optional(CONF_TOKEN, default=""): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_select_repo(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2a: Select from available repositories or enter manually."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_repo = user_input.get("selected_repo", "")

            if selected_repo == "__manual__":
                return await self.async_step_manual()

            if selected_repo:
                # Find the selected repo in our list
                repo_info = next(
                    (r for r in self._available_repos if r.full_name == selected_repo),
                    None,
                )
                if repo_info:
                    repo_url = repo_info.clone_url
                    # Use the repo name as slug (last part of full_name)
                    slug = repo_info.name
                    branch = repo_info.default_branch

                    # Validate repo access
                    parsed = parse_github_url(repo_url)
                    if parsed:
                        owner, repo = parsed
                        validation = await validate_repo_access(
                            self._token, owner, repo
                        )
                        if not validation.valid:
                            _LOGGER.warning(
                                "Repo access validation failed for %s: %s",
                                repo_info.full_name,
                                validation.error_message,
                            )
                            errors["selected_repo"] = "repo_access_error"

                    if not errors:
                        unique_id = _generate_unique_id(repo_url, slug)
                        await self.async_set_unique_id(unique_id)
                        self._abort_if_unique_id_configured()

                        return self.async_create_entry(
                            title=slug,
                            data={
                                CONF_REPO: repo_url,
                                CONF_SLUG: slug,
                                CONF_BRANCH: branch,
                                CONF_TOKEN: self._token,
                            },
                            options={
                                CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
                                CONF_BRANCH: branch,
                                CONF_TOKEN: self._token,
                            },
                        )
            else:
                errors["selected_repo"] = "required"

        # Build the list of repos for selection
        repo_options = {r.full_name: r.full_name for r in self._available_repos}
        repo_options["__manual__"] = "Enter repository URL manually..."

        schema = vol.Schema(
            {
                vol.Required("selected_repo"): vol.In(repo_options),
            }
        )
        return self.async_show_form(
            step_id="select_repo",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "username": self._username or "Unknown",
                "repo_count": str(len(self._available_repos)),
            },
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2b: Manual repository entry."""
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}

        if user_input is not None:
            repo_url = user_input.get(CONF_REPO, "").strip()
            slug = user_input.get(CONF_SLUG, "").strip()
            branch = user_input.get(CONF_BRANCH, DEFAULT_BRANCH).strip()
            token = user_input.get(CONF_TOKEN, self._token).strip()
            poll_interval = user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

            if not repo_url:
                errors[CONF_REPO] = "required"
            elif not repo_url.startswith("https://"):
                errors[CONF_REPO] = "invalid_url"

            if not slug:
                # Try to extract slug from URL
                parsed = parse_github_url(repo_url)
                if parsed:
                    slug = parsed[1]
                else:
                    errors[CONF_SLUG] = "required"

            # Validate repository access if we have a URL and token
            if repo_url and not errors:
                parsed = parse_github_url(repo_url)
                if parsed:
                    owner, repo = parsed
                    validation = await validate_repo_access(token, owner, repo)
                    if not validation.valid:
                        if validation.error == GitHubError.REPO_NOT_FOUND:
                            errors[CONF_REPO] = "repo_not_found"
                        elif validation.error == GitHubError.INVALID_TOKEN:
                            errors[CONF_TOKEN] = "invalid_token"
                        elif validation.error == GitHubError.INSUFFICIENT_PERMISSIONS:
                            errors[CONF_TOKEN] = "insufficient_permissions"
                        elif validation.error == GitHubError.RATE_LIMITED:
                            errors["base"] = "rate_limited"
                        else:
                            errors["base"] = "validation_failed"

                        if validation.error_message:
                            description_placeholders["error_detail"] = (
                                validation.error_message
                            )
                            _LOGGER.warning(
                                "Repository validation failed: %s",
                                validation.error_message,
                            )

            if not errors:
                unique_id = _generate_unique_id(repo_url, slug)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=slug,
                    data={
                        CONF_REPO: repo_url,
                        CONF_SLUG: slug,
                        CONF_BRANCH: branch or DEFAULT_BRANCH,
                        CONF_TOKEN: token,
                    },
                    options={
                        CONF_POLL_INTERVAL: poll_interval,
                        CONF_BRANCH: branch or DEFAULT_BRANCH,
                        CONF_TOKEN: token,
                    },
                )

        # Pre-fill token if we have one
        default_token = self._token if self._token else ""

        schema = vol.Schema(
            {
                vol.Required(CONF_REPO): str,
                vol.Optional(CONF_SLUG, default=""): str,
                vol.Optional(CONF_BRANCH, default=DEFAULT_BRANCH): str,
                vol.Optional(CONF_TOKEN, default=default_token): str,
                vol.Optional(
                    CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
            }
        )
        return self.async_show_form(
            step_id="manual",
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        entry: config_entries.ConfigEntry,
    ) -> OptionsFlow:
        """Hook to open the repository options editor."""
        return OptionsFlow(entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Edit repository configuration options."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit repository options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            branch = user_input.get(CONF_BRANCH, DEFAULT_BRANCH).strip()
            token = user_input.get(CONF_TOKEN, "").strip()
            poll_interval = user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

            return self.async_create_entry(
                title="",
                data={
                    CONF_BRANCH: branch or DEFAULT_BRANCH,
                    CONF_TOKEN: token,
                    CONF_POLL_INTERVAL: poll_interval,
                },
            )

        # Get current values
        current_branch = self._entry.options.get(
            CONF_BRANCH, self._entry.data.get(CONF_BRANCH, DEFAULT_BRANCH)
        )
        current_token = self._entry.options.get(
            CONF_TOKEN, self._entry.data.get(CONF_TOKEN, "")
        )
        current_poll_interval = self._entry.options.get(
            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_BRANCH, default=current_branch): str,
                vol.Optional(CONF_TOKEN, default=current_token): str,
                vol.Optional(
                    CONF_POLL_INTERVAL, default=current_poll_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
