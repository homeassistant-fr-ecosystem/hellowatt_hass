"""Config flow for HelloWatt integration."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import DEFAULT_LOOKBACK_DAYS, DEFAULT_UPDATE_INTERVAL_HOURS, DOMAIN

# Configuration option keys
CONF_UPDATE_INTERVAL = "update_interval"
CONF_LOOKBACK_DAYS = "lookback_days"


class HelloWattConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for HelloWatt.

    This config flow guides users through setting up their HelloWatt
    account credentials for the integration.
    """

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HelloWattOptionsFlowHandler:
        """Get the options flow handler for this integration.

        Args:
            config_entry: The config entry to create options flow for

        Returns:
            Options flow handler instance
        """
        return HelloWattOptionsFlowHandler(config_entry)

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
            # Normalize username (email) for comparison
            username = user_input[CONF_USERNAME].lower().strip()

            # Check if this account already exists by comparing username in existing entries
            for entry in self._async_current_entries():
                existing_username = entry.data.get(CONF_USERNAME, "").lower().strip()
                if existing_username == username:
                    return self.async_abort(reason="already_configured")

            # Set unique ID to prevent duplicates
            await self.async_set_unique_id(username)
            self._abort_if_unique_id_configured()

            # Create entry with username as title for clarity
            return self.async_create_entry(
                title=f"HelloWatt ({username})", data=user_input
            )

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


class HelloWattOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle HelloWatt options flow.

    Allows users to configure integration settings after initial setup,
    such as update interval and data lookback period.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow.

        Args:
            config_entry: The config entry to handle options for
        """
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow initialization.

        Displays a form allowing users to configure update interval
        and data lookback period.

        Args:
            user_input: User-provided options data, or None for initial form

        Returns:
            FlowResult with either a form to display or entry update result
        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_HOURS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
                    vol.Optional(
                        CONF_LOOKBACK_DAYS,
                        default=self.config_entry.options.get(
                            CONF_LOOKBACK_DAYS, DEFAULT_LOOKBACK_DAYS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=3, max=30)),
                }
            ),
        )
