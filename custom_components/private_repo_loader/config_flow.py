"""Config- and options-flow for Private Repo Loader."""
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

# ─────────── Initial “Add integration” flow ───────────
class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Ask once for an optional default GitHub PAT."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        # Prevent more than one instance
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            # Create the entry with empty repo list
            return self.async_create_entry(
                title="Private Repo Loader",
                data={},
                options={
                    CONF_TOKEN: user_input.get(CONF_TOKEN, ""),
                    CONF_REPOS: [],
                },
            )

        # Show first form: just the default token
        schema = vol.Schema(
            {vol.Optional(CONF_TOKEN): selector({"text": {"type": "password"}})}
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        """Hook to open the repo‐list editor from the Integrations UI."""
        return OptionsFlow(entry)


# ─────────── Gear-icon (Options) flow ───────────
class OptionsFlow(config_entries.OptionsFlow):
    """Add / edit / remove your private repos."""

    def __init__(self, entry: config_entries.ConfigEntry | None = None):
        # Store the entry until HA injects self.config_entry on newer core versions
        self._entry_param = entry

    @property
    def _entry(self) -> config_entries.ConfigEntry:
        return getattr(self, "config_entry", self._entry_param)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        # Pre-populate with whatever is already in options
        current = self._entry.options.get(CONF_REPOS, [])

        # A list of dicts selector for repos
        repo_selector = selector({
            "add_dict": {
                "key_selector": {"text": {}},
                "value_selector": {
                    "object": {
                        "keys": [
                            {"name": CONF_SLUG,   "selector": {"text": {"default": DEFAULT_SLUG}}},
                            {"name": CONF_BRANCH, "selector": {"text": {"default": DEFAULT_BRANCH}}},
                            {"name": CONF_TOKEN,  "selector": {"text": {"type": "password"}}},
                        ]
                    }
                }
            }
        })

        schema = vol.Schema({
            vol.Optional(CONF_REPOS, default=current): repo_selector
        })

        return self.async_show_form(step_id="init", data_schema=schema)
