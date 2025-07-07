"""Config- and options-flow for Private Repo Loader (works on every HA)."""
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

# ───────────────────────── Config flow ──────────────────────────
class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
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

    # HA passes the entry here; we hand it to OptionsFlow
    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return OptionsFlow(entry)


# ───────────────────────── Options flow ──────────────────────────
class OptionsFlow(config_entries.OptionsFlow):
    """Add / edit / delete repositories (compatible with all HA builds)."""

    def __init__(self, entry: config_entries.ConfigEntry | None = None):
        # Old cores pass entry, newer ones also inject self.config_entry.
        if entry is not None and not hasattr(self, "config_entry"):
            # ◀─ keep HA happy today; removed automatically >=2025.12
            self.config_entry = entry

    # Small helper so we always have the entry
    @property
    def _entry(self) -> config_entries.ConfigEntry:
        return getattr(self, "config_entry")

    # ------------------------------------------------------------------
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
