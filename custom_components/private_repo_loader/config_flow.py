"""Config- and options-flow for Private Repo Loader (one-step installer)."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
    # field names
    CONF_TOKEN,
    CONF_REPOS,
    CONF_REPO,
    CONF_BRANCH,
    CONF_SLUG,
    # defaults
    DEFAULT_BRANCH,
    DEFAULT_SLUG,
)

# ────────────────────── Add-integration flow ──────────────────────
class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input:
            # always store the global PAT
            options = {CONF_TOKEN: user_input.get(CONF_TOKEN, ""), CONF_REPOS: []}

            # if the user entered a repo URL, store the first repo too
            if user_input.get(CONF_REPO):
                options[CONF_REPOS].append(
                    {
                        CONF_REPO: user_input[CONF_REPO],
                        CONF_BRANCH: user_input.get(CONF_BRANCH, DEFAULT_BRANCH),
                        CONF_SLUG: user_input.get(CONF_SLUG, DEFAULT_SLUG),
                        CONF_TOKEN: options[CONF_TOKEN],  # reuse default PAT
                    }
                )

            return self.async_create_entry(title="Private Repo Loader", data={}, options=options)

        schema = vol.Schema(
            {
                vol.Optional(CONF_TOKEN): selector({"text": {"type": "password"}}),
                vol.Optional(CONF_REPO): selector({"text": {}}),
                vol.Optional(CONF_BRANCH, default=DEFAULT_BRANCH): selector({"text": {}}),
                vol.Optional(CONF_SLUG,   default=DEFAULT_SLUG): selector({"text": {}}),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    # Hook up the familiar repo-editor for later additions
    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return OptionsFlow(entry)

# ───────────────────── Options-flow (gear icon) ────────────────────
class OptionsFlow(config_entries.OptionsFlow):
    """Add / edit / delete repositories later."""

    def __init__(self, entry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        if user_input:
            return self.async_create_entry(data=user_input)

        current = self._entry.options.get(CONF_REPOS, [])

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

        schema = vol.Schema({vol.Optional(CONF_REPOS, default=current): repo_selector})
        return self.async_show_form(step_id="init", data_schema=schema)
