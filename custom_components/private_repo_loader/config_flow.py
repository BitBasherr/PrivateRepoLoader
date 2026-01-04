"""Config- and options-flow for Private Repo Loader."""

from __future__ import annotations

import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_REPOS,
    CONF_REPO,
    CONF_BRANCH,
    CONF_SLUG,
    DEFAULT_BRANCH,
)


class FlowHandler(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Ask once for an optional default GitHub PAT."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial setup step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="Private Repo Loader",
                data={},
                options={
                    CONF_TOKEN: user_input.get(CONF_TOKEN, ""),
                    CONF_REPOS: [],
                },
            )

        schema = vol.Schema(
            {
                vol.Optional(CONF_TOKEN, default=""): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        entry: config_entries.ConfigEntry,
    ) -> OptionsFlow:
        """Hook to open the repo-list editor."""
        return OptionsFlow(entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Add, edit or remove repository definitions."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._entry = entry
        self._repos: list[dict[str, Any]] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show menu to add, edit, or remove repos."""
        self._repos = list(self._entry.options.get(CONF_REPOS, []))

        if not self._repos:
            # No repos yet, go directly to add
            return await self.async_step_add()

        # Build menu options
        return self.async_show_menu(
            step_id="init",
            menu_options=["add", "edit", "remove", "done"],
        )

    async def async_step_add(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new repository."""
        errors: dict[str, str] = {}

        if user_input is not None:
            repo_url = user_input.get(CONF_REPO, "").strip()
            slug = user_input.get(CONF_SLUG, "").strip()
            branch = user_input.get(CONF_BRANCH, DEFAULT_BRANCH).strip()
            token = user_input.get(CONF_TOKEN, "").strip()

            if not repo_url:
                errors[CONF_REPO] = "required"
            elif not repo_url.startswith("https://"):
                errors[CONF_REPO] = "invalid_url"

            if not slug:
                errors[CONF_SLUG] = "required"

            if not errors:
                # Check for duplicate slug
                if any(r.get(CONF_SLUG) == slug for r in self._repos):
                    errors[CONF_SLUG] = "duplicate_slug"
                else:
                    self._repos.append(
                        {
                            CONF_REPO: repo_url,
                            CONF_SLUG: slug,
                            CONF_BRANCH: branch or DEFAULT_BRANCH,
                            CONF_TOKEN: token,
                        }
                    )
                    return self._save_and_finish()

        schema = vol.Schema(
            {
                vol.Required(CONF_REPO): str,
                vol.Required(CONF_SLUG): str,
                vol.Optional(CONF_BRANCH, default=DEFAULT_BRANCH): str,
                vol.Optional(CONF_TOKEN, default=""): str,
            }
        )
        return self.async_show_form(step_id="add", data_schema=schema, errors=errors)

    async def async_step_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select a repository to edit."""
        if not self._repos:
            return await self.async_step_add()

        if user_input is not None:
            idx = int(user_input.get("repo_index", 0))
            return await self.async_step_edit_repo(None, idx)

        # Create selection for existing repos
        repo_options = {
            str(i): f"{r.get(CONF_SLUG)} ({r.get(CONF_REPO)})"
            for i, r in enumerate(self._repos)
        }

        schema = vol.Schema(
            {
                vol.Required("repo_index"): vol.In(repo_options),
            }
        )
        return self.async_show_form(step_id="edit", data_schema=schema)

    async def async_step_edit_repo(
        self, user_input: dict[str, Any] | None = None, idx: int | None = None
    ) -> FlowResult:
        """Edit a specific repository."""
        if idx is not None:
            self._edit_idx = idx

        errors: dict[str, str] = {}
        current = self._repos[self._edit_idx]

        if user_input is not None:
            repo_url = user_input.get(CONF_REPO, "").strip()
            slug = user_input.get(CONF_SLUG, "").strip()
            branch = user_input.get(CONF_BRANCH, DEFAULT_BRANCH).strip()
            token = user_input.get(CONF_TOKEN, "").strip()

            if not repo_url:
                errors[CONF_REPO] = "required"
            elif not repo_url.startswith("https://"):
                errors[CONF_REPO] = "invalid_url"

            if not slug:
                errors[CONF_SLUG] = "required"

            if not errors:
                # Check for duplicate slug (excluding current)
                if any(
                    r.get(CONF_SLUG) == slug
                    for i, r in enumerate(self._repos)
                    if i != self._edit_idx
                ):
                    errors[CONF_SLUG] = "duplicate_slug"
                else:
                    self._repos[self._edit_idx] = {
                        CONF_REPO: repo_url,
                        CONF_SLUG: slug,
                        CONF_BRANCH: branch or DEFAULT_BRANCH,
                        CONF_TOKEN: token,
                    }
                    return self._save_and_finish()

        schema = vol.Schema(
            {
                vol.Required(CONF_REPO, default=current.get(CONF_REPO, "")): str,
                vol.Required(CONF_SLUG, default=current.get(CONF_SLUG, "")): str,
                vol.Optional(
                    CONF_BRANCH,
                    default=current.get(CONF_BRANCH, DEFAULT_BRANCH),
                ): str,
                vol.Optional(CONF_TOKEN, default=current.get(CONF_TOKEN, "")): str,
            }
        )
        return self.async_show_form(
            step_id="edit_repo", data_schema=schema, errors=errors
        )

    async def async_step_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove a repository."""
        if not self._repos:
            return await self.async_step_init()

        if user_input is not None:
            idx = int(user_input.get("repo_index", 0))
            del self._repos[idx]
            return self._save_and_finish()

        # Create selection for existing repos
        repo_options = {
            str(i): f"{r.get(CONF_SLUG)} ({r.get(CONF_REPO)})"
            for i, r in enumerate(self._repos)
        }

        schema = vol.Schema(
            {
                vol.Required("repo_index"): vol.In(repo_options),
            }
        )
        return self.async_show_form(step_id="remove", data_schema=schema)

    async def async_step_done(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Save and finish."""
        return self._save_and_finish()

    def _save_and_finish(self) -> FlowResult:
        """Save options and finish the flow."""
        return self.async_create_entry(
            title="",
            data={
                CONF_TOKEN: self._entry.options.get(CONF_TOKEN, ""),
                CONF_REPOS: self._repos,
            },
        )
