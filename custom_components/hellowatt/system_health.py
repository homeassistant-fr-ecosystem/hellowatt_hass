"""System health for HelloWatt integration.

Provides system health monitoring information for the integration.
https://developers.home-assistant.io/docs/core/integration-system-health
"""

from __future__ import annotations

from typing import Any

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .const import API_URL, DOMAIN


@callback
def async_register(
    _hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register system health callbacks.

    This function is called by Home Assistant's system health component
    to register health check callbacks for this integration.

    Args:
        _hass: Home Assistant instance
        register: System health registration instance
    """
    register.async_register_info(async_system_health_info)


async def async_system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Get system health information.

    Returns health status information about the HelloWatt integration,
    including API connectivity and number of configured accounts.

    Args:
        hass: Home Assistant instance

    Returns:
        Dictionary containing system health information
    """
    # Check API endpoint reachability
    api_reachable = await system_health.async_check_can_reach_url(hass, API_URL)

    # Count configured HelloWatt accounts (config entries)
    configured_accounts = len(hass.data.get(DOMAIN, {}))

    # Count total coordinators across all accounts
    total_coordinators = 0
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if isinstance(entry_data, dict):
            coordinators = entry_data.get("coordinators", {})
            total_coordinators += len(coordinators)

    return {
        "api_endpoint_reachable": api_reachable,
        "configured_accounts": configured_accounts,
        "total_pdl_coordinators": total_coordinators,
    }
