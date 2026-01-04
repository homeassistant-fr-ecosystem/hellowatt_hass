"""The HelloWatt integration."""

from __future__ import annotations

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .client import HelloWattApiClient
from .const import DOMAIN
from .coordinator import HelloWattCoordinator
from .importer import (
    SERVICE_CLEAR_SCHEMA,
    SERVICE_CLEAR_STATISTICS,
    SERVICE_IMPORT_HISTORICAL,
    SERVICE_IMPORT_SCHEMA,
    async_clear_statistics,
    async_import_historical_data,
)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HelloWatt from a config entry."""

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    # Create a dedicated session with cookie jar for this integration
    session = async_create_clientsession(
        hass, cookie_jar=aiohttp.CookieJar(unsafe=True)
    )
    client = HelloWattApiClient(session, username, password)
    await client.authenticate()

    # Create coordinators for each home/PDL
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"client": client, "coordinators": {}}

    for home in client.homes:
        pdl = home.get("enedisHome", {}).get("pdl")
        home_id = home.get("id")
        if pdl and home_id:
            coordinator = HelloWattCoordinator(hass, client, entry, pdl, home_id, home)
            await coordinator.async_config_entry_first_refresh()
            hass.data[DOMAIN][entry.entry_id]["coordinators"][pdl] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register the services with wrapper functions
    async def async_handle_import_historical(call):
        """Wrapper for import historical data service."""
        await async_import_historical_data(hass, entry, call)

    async def async_handle_clear_statistics(call):
        """Wrapper for clear statistics service."""
        await async_clear_statistics(hass, entry, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_HISTORICAL,
        async_handle_import_historical,
        schema=SERVICE_IMPORT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_STATISTICS,
        async_handle_clear_statistics,
        schema=SERVICE_CLEAR_SCHEMA,
    )

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change.

    Args:
        hass: Home Assistant instance
        entry: Config entry that was updated
    """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Unregister services if no more entries
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_IMPORT_HISTORICAL)
            hass.services.async_remove(DOMAIN, SERVICE_CLEAR_STATISTICS)

    return unload_ok
