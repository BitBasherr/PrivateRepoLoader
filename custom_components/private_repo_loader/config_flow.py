# custom_components/private_repo_loader/config_flow.py

"""Config- & options-flow for Private Repo Loader – LIST selector version."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_REPOS,
    CONF_REPO,
    CONF_BRANCH,
    CONF_SLUG,
    DEFAULT_BRANCH,
    DEFAULT_SLUG,
)


# ─────────── Initial “Add Integration” flow ───────────
class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Ask once for a default GitHub PAT (optional)."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        # Only allow one instance
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="Private Repo Loader",
                data={},  # no data stored here
                options={
                    CONF_TOKEN: user_input.get(CONF_TOKEN, ""),
                    CONF_REPOS: [],
                },
            )

        schema = vol.Schema(
            {vol.Optional(CONF_TOKEN): selector({"text": {"type": "password"}})}
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        """Return the OptionsFlow handler for the gear-icon."""
        return OptionsFlow(entry)


# ─────────── Gear-icon “Options” flow ───────────
class OptionsFlow(config_entries.OptionsFlow):
    """Add / Edit / Remove repository list."""

    def __init__(self, entry: config_entries.ConfigEntry | None = None):
        # Store entry until HA injects self.config_entry
        self._entry_param = entry

    @property
    def _entry(self) -> config_entries.ConfigEntry:
        return getattr(self, "config_entry", self._entry_param)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # user_input[CONF_REPOS] is a list of dicts
            return self.async_create_entry(data=user_input)

        # Load existing list (or empty)
        current: list[dict] = self._entry.options.get(CONF_REPOS, [])

        # Define a list selector whose items are objects with four keys
        repos_selector = selector(
            {
                "list": {
                    "min_items": 0,
                    "max_items": 50,
                    "add_item": {"name": "Add repository"},
                    "item": {
                        "object": {
                            "keys": [
                                {
                                    "name": CONF_REPO,
                                    "selector": {"text": {"placeholder": "https://github.com/owner/repo"}},
                                },
                                {
                                    "name": CONF_SLUG,
                                    "selector": {"text": {"default": DEFAULT_SLUG}},
                                },
                                {
                                    "name": CONF_BRANCH,
                                    "selector": {"text": {"default": DEFAULT_BRANCH}},
                                },
                                {
                                    "name": CONF_TOKEN,
                                    "selector": {"text": {"type": "password"}},
                                },
                            ]
                        }
                    },
                }
            }
        )

        schema = vol.Schema(
            {vol.Optional(CONF_REPOS, default=current): repos_selector}
        )
        return self.async_show_form(step_id="init", data_schema=schema)
