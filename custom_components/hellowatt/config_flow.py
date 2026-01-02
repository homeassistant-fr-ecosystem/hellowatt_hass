"""Config flow for HelloWatt integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class HelloWattConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HelloWatt.

    This config flow guides users through setting up their HelloWatt
    account credentials for the integration.
    """

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial configuration step.

        Prompts the user for HelloWatt account credentials and creates
        a config entry if validation succeeds.

        Args:
            user_input: User-provided configuration data, or None for initial form

        Returns:
            FlowResult with either a form to display or entry creation result
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Use username as unique ID to prevent duplicate entries
            await self.async_set_unique_id(user_input[CONF_USERNAME])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="HelloWatt", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )