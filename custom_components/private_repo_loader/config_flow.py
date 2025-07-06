"""Config- & options-flow for Private Repo Loader."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_REPO,
    CONF_BRANCH,
    CONF_SLUG,
    DEFAULT_BRANCH,
    DEFAULT_SLUG,
    CONF_PAT,       # alias – still resolves
)

REPO_OBJECT_TEMPLATE = {
    "keys": [
        {"name": CONF_SLUG,   "selector": {"text": {}}},
        {"name": CONF_BRANCH, "selector": {"text": {"default": DEFAULT_BRANCH}}},
        {"name": CONF_TOKEN,  "selector": {"text": {"type": "password"}}},
    ]
}

class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Ask optionally for a *default* PAT (may be left blank)."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="Private Repo Loader",
                data={},      # nothing in .storage data
                options={     # stored encrypted
                    CONF_TOKEN: user_input.get(CONF_TOKEN, ""),
                    "repos": [],
                },
            )

        schema = vol.Schema(
            {vol.Optional(CONF_TOKEN): selector({"text": {"type": "password"}})}
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    # -----------------------------------------------------------------
    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return OptionsFlow(entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Add / edit / delete repositories."""

    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.entry.options.get("repos", [])

        schema = vol.Schema(
            {
                vol.Optional(
                    "repos",
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
