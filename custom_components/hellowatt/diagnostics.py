"""Diagnostics support for HelloWatt integration.

Provides diagnostic information for troubleshooting issues.
https://developers.home-assistant.io/docs/core/integration_diagnostics
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    This provides comprehensive debugging information about the integration
    setup, coordinators, and entities for user support and troubleshooting.

    Args:
        hass: Home Assistant instance
        entry: Config entry to get diagnostics for

    Returns:
        Dictionary containing diagnostic information
    """
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data is None:
        return {"error": "Integration data not found — setup may have failed"}

    # Redact sensitive information
    diagnostics_data: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "unique_id": entry.unique_id,
            "version": entry.version,
            "domain": entry.domain,
            "source": entry.source,
            "state": entry.state.value,
        },
        "options": dict(entry.options),
        "coordinators": {},
        "entities": {},
        "devices": {},
    }

    # Get entity and device registries
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    # Collect coordinator diagnostics
    coordinators_dict = data.get("coordinators", {})

    for pdl, coordinator in coordinators_dict.items():
        # Basic coordinator info
        coord_info: dict[str, Any] = {
            "pdl": pdl,
            "home_id": coordinator.home_id,
            "update_interval_seconds": coordinator.update_interval.total_seconds(),
            "last_update_success": coordinator.last_update_success,
            "last_update_success_time": (
                coordinator.last_update_success_time.isoformat()
                if coordinator.last_update_success_time
                else None
            ),
        }

        # Add coordinator data summary (without sensitive info)
        if coordinator.data:
            coord_info["data_keys"] = list(coordinator.data.keys())
            coord_info["sensors_available"] = len(coordinator.data)

            # Add sample values for key sensors (useful for debugging)
            coord_info["sample_data"] = {
                "electricity": coordinator.data.get("electricity"),
                "gas": coordinator.data.get("gas"),
                "temperature": coordinator.data.get("temperature"),
                "contract_provider": coordinator.data.get("contract_provider"),
                "contract_offer": coordinator.data.get("contract_offer"),
                "address": coordinator.data.get("address"),
                "postal_code": coordinator.data.get("postal_code"),
                "city": coordinator.data.get("city"),
            }

            # Energy sensor availability
            coord_info["energy_sensors"] = {
                "has_electricity": "electricity" in coordinator.data,
                "has_electricity_peak": "electricity_peak" in coordinator.data,
                "has_electricity_off_peak": "electricity_off_peak" in coordinator.data,
                "has_gas": "gas" in coordinator.data,
            }
        else:
            coord_info["data_keys"] = []
            coord_info["sensors_available"] = 0

        diagnostics_data["coordinators"][pdl] = coord_info

    # Collect entity diagnostics
    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)

    for entity in entities:
        entity_info = {
            "entity_id": entity.entity_id,
            "unique_id": entity.unique_id,
            "platform": entity.platform,
            "device_class": entity.device_class,
            "original_name": entity.original_name,
            "disabled": entity.disabled,
            "disabled_by": entity.disabled_by.value if entity.disabled_by else None,
        }

        # Get entity state if available
        if state := hass.states.get(entity.entity_id):
            entity_info["state"] = state.state
            entity_info["attributes"] = dict(state.attributes)
            entity_info["last_changed"] = state.last_changed.isoformat()
            entity_info["last_updated"] = state.last_updated.isoformat()

        diagnostics_data["entities"][entity.entity_id] = entity_info

    # Collect device diagnostics
    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)

    for device in devices:
        device_info = {
            "id": device.id,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "sw_version": device.sw_version,
            "identifiers": list(device.identifiers),
            "configuration_url": device.configuration_url,
        }

        diagnostics_data["devices"][device.id] = device_info

    # Add integration statistics
    diagnostics_data["statistics"] = {
        "total_coordinators": len(coordinators_dict),
        "total_entities": len(entities),
        "total_devices": len(devices),
        "disabled_entities": sum(1 for e in entities if e.disabled),
    }

    return diagnostics_data


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a specific device.

    This provides device-specific debugging information for a particular
    PDL (Point de Livraison).

    Args:
        hass: Home Assistant instance
        entry: Config entry
        device: Device entry to get diagnostics for

    Returns:
        Dictionary containing device diagnostic information
    """
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data is None:
        return {"error": "Integration data not found — setup may have failed"}
    coordinators_dict = data.get("coordinators", {})

    # Find the PDL for this device
    pdl = None
    for identifier_domain, identifier in device.identifiers:
        if identifier_domain == DOMAIN:
            pdl = identifier
            break

    if not pdl or pdl not in coordinators_dict:
        return {
            "error": "Device not found or no coordinator available",
            "device_id": device.id,
            "device_name": device.name,
        }

    coordinator = coordinators_dict[pdl]

    # Get entity registry
    entity_registry = er.async_get(hass)

    # Find entities for this device
    device_entities = [
        e
        for e in er.async_entries_for_device(entity_registry, device.id)
        if e.config_entry_id == entry.entry_id
    ]

    device_diagnostics = {
        "device": {
            "id": device.id,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "sw_version": device.sw_version,
        },
        "pdl": pdl,
        "coordinator": {
            "home_id": coordinator.home_id,
            "update_interval_seconds": coordinator.update_interval.total_seconds(),
            "last_update_success": coordinator.last_update_success,
            "last_update_success_time": (
                coordinator.last_update_success_time.isoformat()
                if coordinator.last_update_success_time
                else None
            ),
        },
        "entities": {},
    }

    # Add coordinator data for this device
    if coordinator.data:
        device_diagnostics["coordinator"]["data_summary"] = {
            "total_sensors": len(coordinator.data),
            "available_sensors": list(coordinator.data.keys()),
        }

        # Add all sensor values for this specific device
        device_diagnostics["coordinator"]["sensor_values"] = dict(coordinator.data)

    # Add entity details
    for entity in device_entities:
        entity_info = {
            "entity_id": entity.entity_id,
            "unique_id": entity.unique_id,
            "platform": entity.platform,
            "device_class": entity.device_class,
            "original_name": entity.original_name,
            "disabled": entity.disabled,
        }

        if state := hass.states.get(entity.entity_id):
            entity_info["state"] = state.state
            entity_info["unit_of_measurement"] = state.attributes.get(
                "unit_of_measurement"
            )
            entity_info["device_class"] = state.attributes.get("device_class")
            entity_info["state_class"] = state.attributes.get("state_class")
            entity_info["last_changed"] = state.last_changed.isoformat()

        device_diagnostics["entities"][entity.entity_id] = entity_info

    device_diagnostics["statistics"] = {
        "total_entities": len(device_entities),
        "enabled_entities": sum(1 for e in device_entities if not e.disabled),
        "disabled_entities": sum(1 for e in device_entities if e.disabled),
    }

    return device_diagnostics
