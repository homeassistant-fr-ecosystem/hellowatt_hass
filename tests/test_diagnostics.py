"""Tests for HelloWatt diagnostics.

Following Home Assistant testing guidelines:
https://developers.home-assistant.io/docs/creating_integration_tests_file_structure
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hellowatt.const import DOMAIN
from custom_components.hellowatt.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)

PDL = "12345678901234"


def _make_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={"username": "test@example.com", "password": "test"},
        unique_id="test@example.com",
        options={"update_interval": 1},
    )
    entry.add_to_hass(hass)
    return entry


def _make_coordinator(data: dict | None) -> Mock:
    coordinator = Mock()
    coordinator.home_id = "home123"
    coordinator.update_interval = timedelta(hours=1)
    coordinator.last_update_success = True
    coordinator.last_update_success_time = None
    coordinator.data = data
    return coordinator


# ============================================================================
# Config Entry Diagnostics Tests
# ============================================================================


async def test_async_get_config_entry_diagnostics_no_data(
    hass: HomeAssistant,
) -> None:
    """Test diagnostics returns an error when integration data is missing."""
    entry = _make_entry(hass)

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result == {"error": "Integration data not found — setup may have failed"}


async def test_async_get_config_entry_diagnostics_with_data(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test diagnostics returns full details when integration data is present."""
    entry = _make_entry(hass)

    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, PDL)},
        name=f"HelloWatt {PDL}",
        manufacturer="HelloWatt",
        model="Energy Monitor",
    )
    entity = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"{DOMAIN}_{PDL}_electricity",
        config_entry=entry,
        device_id=device.id,
    )
    hass.states.async_set(
        entity.entity_id,
        "15.7",
        {"unit_of_measurement": "kWh", "device_class": "energy"},
    )

    coordinator_data = {
        "electricity": 15.7,
        "electricity_peak": 10.5,
        "electricity_off_peak": 5.2,
        "gas": 25.0,
        "temperature": 15.5,
        "contract_provider": "EDF",
        "contract_offer": "Tarif Bleu",
        "address": "123 Test St",
        "postal_code": "75001",
        "city": "Paris",
    }
    coordinator = _make_coordinator(coordinator_data)

    hass.data[DOMAIN] = {
        entry.entry_id: {
            "client": Mock(),
            "coordinators": {PDL: coordinator},
        }
    }

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["title"] == "HelloWatt (test@example.com)"
    assert result["entry"]["domain"] == DOMAIN

    coord_info = result["coordinators"][PDL]
    assert coord_info["pdl"] == PDL
    assert coord_info["home_id"] == "home123"
    assert coord_info["sensors_available"] == len(coordinator_data)
    assert coord_info["sample_data"]["electricity"] == 15.7
    assert coord_info["energy_sensors"]["has_electricity"] is True
    assert coord_info["energy_sensors"]["has_gas"] is True

    entity_info = result["entities"][entity.entity_id]
    assert entity_info["unique_id"] == f"{DOMAIN}_{PDL}_electricity"
    assert entity_info["state"] == "15.7"

    device_info = result["devices"][device.id]
    assert device_info["manufacturer"] == "HelloWatt"

    assert result["statistics"]["total_coordinators"] == 1
    assert result["statistics"]["total_entities"] == 1
    assert result["statistics"]["total_devices"] == 1
    assert result["statistics"]["disabled_entities"] == 0


async def test_async_get_config_entry_diagnostics_coordinator_no_data(
    hass: HomeAssistant,
) -> None:
    """Test diagnostics handles a coordinator without data yet."""
    entry = _make_entry(hass)
    coordinator = _make_coordinator(None)

    hass.data[DOMAIN] = {
        entry.entry_id: {
            "client": Mock(),
            "coordinators": {PDL: coordinator},
        }
    }

    result = await async_get_config_entry_diagnostics(hass, entry)

    coord_info = result["coordinators"][PDL]
    assert coord_info["data_keys"] == []
    assert coord_info["sensors_available"] == 0
    assert "sample_data" not in coord_info


# ============================================================================
# Device Diagnostics Tests
# ============================================================================


async def test_async_get_device_diagnostics_no_integration_data(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test device diagnostics returns an error when integration data is missing."""
    entry = _make_entry(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, PDL)},
        name=f"HelloWatt {PDL}",
    )

    result = await async_get_device_diagnostics(hass, entry, device)

    assert result == {"error": "Integration data not found — setup may have failed"}


async def test_async_get_device_diagnostics_no_matching_coordinator(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test device diagnostics returns an error when no coordinator matches the PDL."""
    entry = _make_entry(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, PDL)},
        name=f"HelloWatt {PDL}",
    )

    hass.data[DOMAIN] = {
        entry.entry_id: {"client": Mock(), "coordinators": {}},
    }

    result = await async_get_device_diagnostics(hass, entry, device)

    assert result["error"] == "Device not found or no coordinator available"
    assert result["device_id"] == device.id


async def test_async_get_device_diagnostics_with_coordinator(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test device diagnostics returns full details for a matched coordinator."""
    entry = _make_entry(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, PDL)},
        name=f"HelloWatt {PDL}",
        manufacturer="HelloWatt",
        model="Energy Monitor",
    )
    entity = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"{DOMAIN}_{PDL}_gas",
        config_entry=entry,
        device_id=device.id,
    )
    hass.states.async_set(
        entity.entity_id,
        "25.0",
        {"unit_of_measurement": "kg", "device_class": "gas", "state_class": "total"},
    )

    coordinator_data = {"gas": 25.0, "electricity": 15.7}
    coordinator = _make_coordinator(coordinator_data)

    hass.data[DOMAIN] = {
        entry.entry_id: {
            "client": Mock(),
            "coordinators": {PDL: coordinator},
        }
    }

    result = await async_get_device_diagnostics(hass, entry, device)

    assert result["pdl"] == PDL
    assert result["device"]["manufacturer"] == "HelloWatt"
    assert result["coordinator"]["home_id"] == "home123"
    assert result["coordinator"]["data_summary"]["total_sensors"] == 2
    assert result["coordinator"]["sensor_values"] == coordinator_data

    entity_info = result["entities"][entity.entity_id]
    assert entity_info["unique_id"] == f"{DOMAIN}_{PDL}_gas"
    assert entity_info["state"] == "25.0"
    assert entity_info["unit_of_measurement"] == "kg"

    assert result["statistics"]["total_entities"] == 1
    assert result["statistics"]["enabled_entities"] == 1
    assert result["statistics"]["disabled_entities"] == 0
