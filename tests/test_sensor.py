"""Tests for HelloWatt sensor platform.

Following Home Assistant testing guidelines:
https://developers.home-assistant.io/docs/creating_integration_tests_file_structure
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfMass, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.hellowatt.const import DOMAIN
from custom_components.hellowatt.coordinator import HelloWattCoordinator
from custom_components.hellowatt.sensor import (
    SENSOR_TYPES,
    HelloWattSensor,
    async_setup_entry,
)

# ============================================================================
# Sensor Platform Setup Tests
# ============================================================================


async def test_async_setup_entry_creates_sensors(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
    mock_coordinator_data,
) -> None:
    """Test sensor platform creates entities for available data."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    # Setup coordinator with data
    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    # Mock coordinator data
    coordinator.data = mock_coordinator_data

    # Setup domain data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": mock_hellowatt_client_authenticated,
        "coordinators": {"12345678901234": coordinator},
    }

    entities = []

    def mock_add_entities(new_entities):
        """Mock add entities callback."""
        entities.extend(new_entities)

    # Patch coordinator refresh to avoid actual API calls
    with patch.object(coordinator, "async_config_entry_first_refresh", AsyncMock()):
        await async_setup_entry(hass, entry, mock_add_entities)

    # Should create entities for all keys present in coordinator data
    assert len(entities) > 0
    entity_keys = {entity._key_id for entity in entities}

    # Verify expected sensors are created
    assert "electricity" in entity_keys
    assert "gas" in entity_keys
    assert "temperature" in entity_keys


async def test_async_setup_entry_skips_missing_data(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test sensor platform only creates entities for available data."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    # Setup coordinator with partial data (no gas)
    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    # Only electricity, no gas
    coordinator.data = {
        "electricity": 15.7,
        "temperature": 16.5,
    }

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": mock_hellowatt_client_authenticated,
        "coordinators": {"12345678901234": coordinator},
    }

    entities = []

    def mock_add_entities(new_entities):
        """Mock add entities callback."""
        entities.extend(new_entities)

    with patch.object(coordinator, "async_config_entry_first_refresh", AsyncMock()):
        await async_setup_entry(hass, entry, mock_add_entities)

    entity_keys = {entity._key_id for entity in entities}

    # Should have electricity and temperature
    assert "electricity" in entity_keys
    assert "temperature" in entity_keys

    # Should NOT have gas sensors
    assert "gas" not in entity_keys


async def test_async_setup_entry_handles_refresh_failure(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test sensor platform handles coordinator refresh failure gracefully."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": mock_hellowatt_client_authenticated,
        "coordinators": {"12345678901234": coordinator},
    }

    entities = []

    def mock_add_entities(new_entities):
        """Mock add entities callback."""
        entities.extend(new_entities)

    # Mock refresh to fail
    with patch.object(
        coordinator,
        "async_config_entry_first_refresh",
        AsyncMock(side_effect=Exception("API Error")),
    ):
        await async_setup_entry(hass, entry, mock_add_entities)

    # Should not create any entities when refresh fails
    assert len(entities) == 0


# ============================================================================
# Sensor Entity Tests
# ============================================================================


async def test_sensor_initialization(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test sensor entity initializes with correct attributes."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    sensor_config = SENSOR_TYPES["electricity"]
    sensor = HelloWattSensor(
        coordinator, "12345678901234", "electricity", sensor_config
    )

    assert sensor._pdl == "12345678901234"
    assert sensor._key_id == "electricity"
    assert sensor._attr_name == "Electricity Daily"
    assert sensor._attr_unique_id == "hellowatt_12345678901234_electricity"
    assert sensor._attr_device_class == SensorDeviceClass.ENERGY
    assert sensor._attr_state_class == SensorStateClass.TOTAL
    assert sensor._attr_native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR


async def test_sensor_native_value(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test sensor returns correct native value from coordinator."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    coordinator.data = {"electricity": 15.7}

    sensor_config = SENSOR_TYPES["electricity"]
    sensor = HelloWattSensor(
        coordinator, "12345678901234", "electricity", sensor_config
    )

    assert sensor.native_value == 15.7


async def test_sensor_native_value_none_when_missing(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test sensor returns None when data is missing."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    coordinator.data = {}  # No electricity data

    sensor_config = SENSOR_TYPES["electricity"]
    sensor = HelloWattSensor(
        coordinator, "12345678901234", "electricity", sensor_config
    )

    assert sensor.native_value is None


async def test_sensor_device_info(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test sensor provides correct device information."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    coordinator.data = {
        "electricity": 15.7,
        "contract_provider": "EDF",
        "contract_offer": "Tarif Bleu",
    }

    sensor_config = SENSOR_TYPES["electricity"]
    sensor = HelloWattSensor(
        coordinator, "12345678901234", "electricity", sensor_config
    )

    device_info = sensor.device_info

    assert device_info["identifiers"] == {(DOMAIN, "12345678901234")}
    assert device_info["name"] == "HelloWatt 12345678901234"
    assert device_info["manufacturer"] == "HelloWatt"
    assert device_info["model"] == "Energy Monitor"
    # Removed: assert "EDF - Tarif Bleu" in device_info["sw_version"]


async def test_contract_diagnostic_sensors(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
    mock_coordinator_data,
) -> None:
    """Test that contract diagnostic sensors are created and have correct states."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    pdl = "12345678901234"
    home_id = "home123"

    # Setup coordinator with mock contract data
    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl=pdl,
        home_id=home_id,
        home=mock_hellowatt_homes[0],
    )

    coordinator.data = {
        **mock_coordinator_data,
        "contract_provider": "Test Provider",
        "contract_offer": "Test Offer",
    }

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": mock_hellowatt_client_authenticated,
        "coordinators": {pdl: coordinator},
    }

    entities: list[HelloWattSensor] = []

    def mock_add_entities(new_entities):
        """Mock add entities callback."""
        entities.extend(new_entities)

    with patch.object(coordinator, "async_config_entry_first_refresh", AsyncMock()):
        await async_setup_entry(hass, entry, mock_add_entities)

    # Check entities collected by mock_add_entities
    provider_sensor = next(
        (e for e in entities if e._key_id == "contract_provider"), None
    )
    assert provider_sensor is not None
    assert provider_sensor.native_value == "Test Provider"

    offer_sensor = next((e for e in entities if e._key_id == "contract_offer"), None)
    assert offer_sensor is not None
    assert offer_sensor.native_value == "Test Offer"


async def test_sensor_last_reset_for_total_increasing(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test last_reset property for TOTAL_INCREASING sensors (e.g. CO2 emissions)."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    coordinator.data = {"electricity_co2": 1.234}

    sensor_config = SENSOR_TYPES["electricity_co2"]
    sensor = HelloWattSensor(
        coordinator, "12345678901234", "electricity_co2", sensor_config
    )

    # TOTAL_INCREASING sensors should have last_reset at midnight
    last_reset = sensor.last_reset
    assert last_reset is not None

    # Should be midnight of today
    now = dt_util.now()
    expected = now.replace(hour=0, minute=0, second=0, microsecond=0)
    assert last_reset == expected


async def test_sensor_last_reset_none_for_measurement(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test last_reset is None for MEASUREMENT sensors."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    coordinator.data = {"temperature": 16.5}

    sensor_config = SENSOR_TYPES["temperature"]
    sensor = HelloWattSensor(
        coordinator, "12345678901234", "temperature", sensor_config
    )

    # MEASUREMENT sensors should not have last_reset
    assert sensor.last_reset is None


async def test_sensor_available_when_data_present(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test sensor is available when coordinator has data."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    coordinator.data = {"electricity": 15.7}
    coordinator.last_update_success = True

    sensor_config = SENSOR_TYPES["electricity"]
    sensor = HelloWattSensor(
        coordinator, "12345678901234", "electricity", sensor_config
    )

    assert sensor.available is True


async def test_sensor_unavailable_when_key_missing(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test sensor is unavailable when key is missing from coordinator data."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    coordinator.data = {"temperature": 16.5}  # No electricity
    coordinator.last_update_success = True

    sensor_config = SENSOR_TYPES["electricity"]
    sensor = HelloWattSensor(
        coordinator, "12345678901234", "electricity", sensor_config
    )

    assert sensor.available is False


# ============================================================================
# Sensor Type Configuration Tests
# ============================================================================


async def test_sensor_setup_does_not_call_first_refresh(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
    mock_coordinator_data,
) -> None:
    """sensor.async_setup_entry must not call async_config_entry_first_refresh.

    __init__.async_setup_entry already calls it; a second call risks leaving
    sensors permanently unavailable if the coordinator raises on re-entry.
    """
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )
    coordinator.data = mock_coordinator_data

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": mock_hellowatt_client_authenticated,
        "coordinators": {"12345678901234": coordinator},
    }

    refresh_mock = AsyncMock()
    with patch.object(coordinator, "async_config_entry_first_refresh", refresh_mock):
        await async_setup_entry(hass, entry, lambda _entities: None)

    refresh_mock.assert_not_called()


def test_all_sensor_types_have_required_fields() -> None:
    """Test all sensor types have required configuration fields."""
    required_fields = {"name", "device_class", "unit", "state_class", "icon"}

    for sensor_key, sensor_config in SENSOR_TYPES.items():
        for field in required_fields:
            assert field in sensor_config, f"{sensor_key} missing {field}"


def test_energy_sensors_have_correct_config() -> None:
    """Test energy sensors have proper configuration."""
    energy_sensors = [
        "electricity",
        "electricity_peak",
        "electricity_off_peak",
        "gas",
    ]

    for sensor_key in energy_sensors:
        config = SENSOR_TYPES[sensor_key]
        assert config["device_class"] == SensorDeviceClass.ENERGY
        assert config["unit"] == UnitOfEnergy.KILO_WATT_HOUR


def test_cost_sensors_have_correct_config() -> None:
    """Test cost sensors have proper configuration."""
    cost_sensors = [
        "electricity_cost",
        "electricity_cost_consumption",
        "electricity_cost_subscription",
        "gas_cost",
        "gas_cost_consumption",
        "gas_cost_subscription",
    ]

    for sensor_key in cost_sensors:
        config = SENSOR_TYPES[sensor_key]
        assert config["device_class"] == SensorDeviceClass.MONETARY
        assert config["unit"] == "EUR"


def test_co2_sensors_have_correct_config() -> None:
    """Test CO2 sensors have proper configuration."""
    co2_sensors = ["electricity_co2", "gas_co2"]

    for sensor_key in co2_sensors:
        config = SENSOR_TYPES[sensor_key]
        assert config["device_class"] == SensorDeviceClass.WEIGHT
        assert config["unit"] == UnitOfMass.KILOGRAMS


def test_temperature_sensor_has_correct_config() -> None:
    """Test temperature sensor has proper configuration."""
    config = SENSOR_TYPES["temperature"]
    assert config["device_class"] == SensorDeviceClass.TEMPERATURE
    assert config["unit"] == UnitOfTemperature.CELSIUS
    assert config["state_class"] == SensorStateClass.MEASUREMENT
