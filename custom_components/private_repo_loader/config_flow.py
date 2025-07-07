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

class FlowHandler(
    config_entries.ConfigFlow, domain=DOMAIN
):
    """Ask once for an optional default GitHub PAT."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(
                reason="single_instance_allowed"
            )

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
                vol.Optional(CONF_TOKEN): selector(
                    {"text": {"type": "password"}}
                )
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        """Hook to open the repo-list editor."""
        return OptionsFlow(entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Add, edit or remove repository definitions."""

    def __init__(self, entry: config_entries.ConfigEntry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self._entry.options.get(CONF_REPOS, [])

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
                                    "selector": {
                                        "text": {
                                            "placeholder": (
                                                "https://"
                                                "github.com/owner/repo"
                                            )
                                        }
                                    },
                                },
                                {
                                    "name": CONF_SLUG,
                                    "selector": {
                                        "text": {"default": DEFAULT_SLUG}
                                    },
                                },
                                {
                                    "name": CONF_BRANCH,
                                    "selector": {
                                        "text": {
                                            "default": DEFAULT_BRANCH
                                        }
                                    },
                                },
                                {
                                    "name": CONF_TOKEN,
                                    "selector": {
                                        "text": {"type": "password"}
                                    },
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
        return self.async_show_form(
            step_id="init", data_schema=schema
        )