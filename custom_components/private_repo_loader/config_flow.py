"""Config- and options-flow for Private Repo Loader (stable version)."""
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
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input:
            return self.async_create_entry(
                title="Private Repo Loader",
                data={},
                options={CONF_TOKEN: user_input.get(CONF_TOKEN, ""), CONF_REPOS: []},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Optional(CONF_TOKEN): selector({"text": {"type": "password"}})}
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return OptionsFlow(entry)

# ─────────── Gear-icon (Options) flow ───────────
class OptionsFlow(config_entries.OptionsFlow):
    """
    Works on every HA version.

    • Accepts *entry* in __init__ (older cores).
    • New cores inject self.config_entry later.
    • Never touches self.config_entry inside __init__.
    """

    def __init__(self, entry: config_entries.ConfigEntry | None = None):
        self._entry_param = entry

    @property
    def _entry(self) -> config_entries.ConfigEntry:
        return getattr(self, "config_entry", None) or self._entry_param

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
