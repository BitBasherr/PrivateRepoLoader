"""Config- and options-flow for Private Repo Loader (compat version)."""
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
    """Initial step – ask for an optional default GitHub PAT."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input:
            return self.async_create_entry(
                title="Private Repo Loader",
                data={},
                options={
                    CONF_TOKEN: user_input.get(CONF_TOKEN, ""),
                    CONF_REPOS: [],
                },
            )

        schema = vol.Schema(
            {vol.Optional(CONF_TOKEN): selector({"text": {"type": "password"}})}
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    # Let HA pass the entry to the options flow for max compatibility
    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return OptionsFlow(entry)


# ───────────────────────── Options flow ──────────────────────────
class OptionsFlow(config_entries.OptionsFlow):
    """
    Maintain the list of repositories.

    Works on every HA version because:
        • accepts `entry` in __init__  (older builds expect this)
        • falls back to self.config_entry if HA injected it (new builds)
    """

    # Accept the entry but keep it optional for future HA versions
    def __init__(self, entry: config_entries.ConfigEntry | None = None):
        # Older HA passes entry here
        if entry is not None:
            self._entry = entry  # store privately
        # Newer HA may inject self.config_entry automatically

    # Convenience property: always returns the config_entry, regardless of path
    @property
    def _cfg_entry(self) -> config_entries.ConfigEntry:
        return getattr(self, "config_entry", None) or getattr(self, "_entry")

    # ------------------------------------------------------------------
    async def async_step_init(self, user_input=None):
        if user_input:
            return self.async_create_entry(data=user_input)

        current = self._cfg_entry.options.get(CONF_REPOS, [])

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
