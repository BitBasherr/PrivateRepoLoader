"""Config- and options-flow for Private Repo Loader.

Each repository is now its own config entry, allowing individual management
and proper linking from the integrations page.
"""

from __future__ import annotations

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


def _generate_unique_id(repo_url: str, slug: str) -> str:
    """Generate a unique ID for a repository entry."""
    return f"{DOMAIN}_{slug}"


class FlowHandler(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle adding a new private repository.

    Each repository is a separate config entry.
    """

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a new repository."""
        errors: dict[str, str] = {}

        if user_input is not None:
            repo_url = user_input.get(CONF_REPO, "").strip()
            slug = user_input.get(CONF_SLUG, "").strip()
            branch = user_input.get(CONF_BRANCH, DEFAULT_BRANCH).strip()
            token = user_input.get(CONF_TOKEN, "").strip()
            poll_interval = user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

            if not repo_url:
                errors[CONF_REPO] = "required"
            elif not repo_url.startswith("https://"):
                errors[CONF_REPO] = "invalid_url"

            if not slug:
                errors[CONF_SLUG] = "required"

            if not errors:
                # Check for duplicate slug across existing entries
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

        schema = vol.Schema(
            {
                vol.Required(CONF_REPO): str,
                vol.Required(CONF_SLUG): str,
                vol.Optional(CONF_BRANCH, default=DEFAULT_BRANCH): str,
                vol.Optional(CONF_TOKEN, default=""): str,
                vol.Optional(
                    CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

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
