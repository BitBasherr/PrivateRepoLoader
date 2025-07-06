"""Config- and options-flow for Private Repo Loader."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
    CONF_BRANCH,
    CONF_REPO,
    CONF_REPOS,
    CONF_SLUG,
    CONF_TOKEN,
    DEFAULT_BRANCH,
    DEFAULT_SLUG,
)

# ────────────────────────────────────────────────────────────────────────────────
REPO_OBJECT_TEMPLATE = {
    "keys": [
        {"name": CONF_SLUG,   "selector": {"text": {"default": DEFAULT_SLUG}}},
        {"name": CONF_BRANCH, "selector": {"text": {"default": DEFAULT_BRANCH}}},
        {"name": CONF_TOKEN,  "selector": {"text": {"type": "password"}}},
    ]
}


class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Initial flow: ask (once) for a *default* PAT (optional)."""
    VERSION = 1
    _entry_unique_id = DOMAIN  # ensures single instance

    async def async_step_user(self, user_input: dict | None = None):
        """Single form: optional default token."""
        if user_input is not None:
            await self._handle_existing_entry()
            return self.async_create_entry(
                title="Private Repo Loader",
                data={},  # nothing sensitive here
                options={
                    CONF_TOKEN: user_input.get(CONF_TOKEN, ""),
                    CONF_REPOS: [],
                },
            )

        schema = vol.Schema(
            {vol.Optional(CONF_TOKEN): selector({"text": {"type": "password"}})}
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    # ------------------------------------------------------------------
    async def _handle_existing_entry(self) -> None:
        """Abort if an instance already exists (single-instance integration)."""
        if self._async_current_entries():
            self._async_abort_entries_match({})
        await self.async_set_unique_id(self._entry_unique_id)

    # ------------------------------------------------------------------
    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return OptionsFlow(entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Add / edit / delete repositories after install."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict | None = None):
        if user_input is not None:
            # Always store repos list under CONF_REPOS
            new_options = dict(self.entry.options)
            new_options[CONF_REPOS] = user_input.get(CONF_REPOS, [])
            return self.async_create_entry(data=new_options)

        current = self.entry.options.get(CONF_REPOS, [])
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_REPOS,
                    description={"suggested_value": current},
                    default=current
                    or [
                        {
                            CONF_REPO: "https://github.com/<owner>/<repo>",
                            CONF_SLUG: DEFAULT_SLUG,
                            CONF_BRANCH: DEFAULT_BRANCH,
                            CONF_TOKEN: self.entry.options.get(CONF_TOKEN, ""),
                        }
                    ],
                ): selector(
                    {
                        "add_dict": {
                            "key_selector": {"text": {}},  # repo URL key
                            "value_selector": {"object": REPO_OBJECT_TEMPLATE},
                        }
                    }
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
