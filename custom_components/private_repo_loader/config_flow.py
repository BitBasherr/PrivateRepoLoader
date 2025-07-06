"""Config- & options-flow (UI)."""
from __future__ import annotations
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
    CONF_PAT,
    CONF_REPOS,
    CONF_URL,
    CONF_SLUG,
    CONF_BRANCH,
    DEFAULT_BRANCH,
    DEFAULT_SLUG,
)


class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Initial flow – asks only for the PAT."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="Private Repo Loader",
                data={},                       # no direct data
                options={                      # stored in .storage
                    CONF_PAT: user_input[CONF_PAT],
                    CONF_REPOS: [],
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_PAT): selector(
                    {"text": {"type": "password"}}
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    # ------------------------------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return OptionsFlow(entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Add / edit list of managed private repositories."""

    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.entry.options.get(CONF_REPOS, [])

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_REPOS,
                    default=current
                    or [
                        {
                            CONF_URL: "https://github.com/<owner>/<repo>",
                            CONF_SLUG: DEFAULT_SLUG,
                            CONF_BRANCH: DEFAULT_BRANCH,
                        }
                    ],
                ): selector(
                    {
                        "add_dict": {
                            "key_selector": {"text": {}},        # URL
                            "value_selector": {
                                "object": {
                                    "keys": [
                                        {
                                            "name": CONF_SLUG,
                                            "selector": {"text": {}},
                                        },
                                        {
                                            "name": CONF_BRANCH,
                                            "selector": {
                                                "text": {
                                                    "default": DEFAULT_BRANCH
                                                }
                                            },
                                        },
                                    ]
                                }
                            },
                        }
                    }
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
