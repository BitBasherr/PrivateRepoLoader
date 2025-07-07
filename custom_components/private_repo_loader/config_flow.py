"""Config- and options-flow for Private Repo Loader (universal version)."""
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

# ────────────────────────── Config flow ──────────────────────────
class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Initial step – ask once for an optional default GitHub PAT."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        # Allow only one instance
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input:
            return self.async_create_entry(
                title="Private Repo Loader",
                data={},  # nothing stored in .data
                options={
                    CONF_TOKEN: user_input.get(CONF_TOKEN, ""),
                    CONF_REPOS: [],
                },
            )

        schema = vol.Schema(
            {vol.Optional(CONF_TOKEN): selector({"text": {"type": "password"}})}
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    # Register options flow
    @staticmethod
    @callback
    def async_get_options_flow(_entry: config_entries.ConfigEntry):
        # ← NO ARGUMENTS passed to the constructor
        return OptionsFlow()


# ───────────────────────── Options flow ──────────────────────────
class OptionsFlow(config_entries.OptionsFlow):
    """
    Add / edit / delete repositories.

    * No __init__ needed – Home Assistant injects self.config_entry.
    * Works on every 2024+ version, no deprecated attributes.
    """

    async def async_step_init(self, user_input=None):
        if user_input:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(CONF_REPOS, [])

        # Plain object selector: compatible with all HA builds
        repo_selector = selector(
            {
                "object": {
                    "keys": [
                        {"name": CONF_REPO,   "selector": {"text": {}}},
                        {"name": CONF_SLUG,   "selector": {"text": {"default": DEFAULT_SLUG}}},
                        {"name": CONF_BRANCH, "selector": {"text": {"default": DEFAULT_BRANCH}}},
                        {"name": CONF_TOKEN,  "selector": {"text": {"type": "password"}}},
                    ]
                }
            }
        )

        schema = vol.Schema(
            {vol.Optional(CONF_REPOS, default=current): repo_selector}
        )

        return self.async_show_form(step_id="init", data_schema=schema)
