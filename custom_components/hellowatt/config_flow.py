"""Config flow for HelloWatt integration."""

from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import voluptuous as vol

from .client import HelloWattApiClient
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

    async def _validate_credentials(
        self, username: str, password: str
    ) -> tuple[bool, str | None]:
        """Validate HelloWatt credentials by attempting authentication.

        Args:
            username: HelloWatt account email
            password: HelloWatt account password

        Returns:
            Tuple of (success: bool, error_key: str | None)
        """
        session = async_create_clientsession(
            self.hass, cookie_jar=aiohttp.CookieJar(unsafe=True)
        )
        client = HelloWattApiClient(session, username, password)

        try:
            await client.authenticate()
            return (True, None)
        except aiohttp.ClientError:
            return (False, "cannot_connect")
        except TimeoutError:
            return (False, "timeout")
        except Exception as err:
            error_str = str(err).lower()
            # Check for authentication-specific errors
            if "authentication failed" in error_str:
                return (False, "invalid_auth")
            if "no session cookie" in error_str:
                return (False, "invalid_auth")
            # Generic API error
            return (False, "api_error")

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

            # Validate credentials before creating entry
            success, error_key = await self._validate_credentials(
                username, user_input[CONF_PASSWORD]
            )

            if not success:
                errors["base"] = error_key or "unknown"
            else:
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

    async def async_step_reauth(
        self, _user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauthentication initiation."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauthentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            username = entry.data[CONF_USERNAME]

            success, error_key = await self._validate_credentials(
                username, user_input[CONF_PASSWORD]
            )

            if not success:
                errors["base"] = error_key or "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )


class HelloWattOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle HelloWatt options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_update_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_HOURS
        )
        current_lookback_days = self.config_entry.options.get(
            CONF_LOOKBACK_DAYS, DEFAULT_LOOKBACK_DAYS
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=current_update_interval,
                    ): vol.All(int, vol.Range(min=1, max=24)),
                    vol.Optional(
                        CONF_LOOKBACK_DAYS,
                        default=current_lookback_days,
                    ): vol.All(int, vol.Range(min=3, max=30)),
                }
            ),
        )
