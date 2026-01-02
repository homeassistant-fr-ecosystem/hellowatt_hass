"""Sensor platform for HelloWatt."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HelloWattCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HelloWatt sensor."""
    coordinator: HelloWattCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        HelloWattSensor(
            coordinator,
            "electricity",
            "Electricity Consumption",
            SensorDeviceClass.ENERGY,
            UnitOfEnergy.KILO_WATT_HOUR,
            SensorStateClass.TOTAL,
        ),
        HelloWattSensor(
            coordinator,
            "temperature",
            "Temperature",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            SensorStateClass.MEASUREMENT,
        ),
        HelloWattSensor(
            coordinator,
            "contract_provider",
            "Contract Provider",
            None,
            None,
            None,
        ),
        HelloWattSensor(
            coordinator,
            "contract_offer",
            "Contract Offer",
            None,
            None,
            None,
        ),
        HelloWattSensor(
            coordinator,
            "address",
            "Address",
            None,
            None,
            None,
        ),
        HelloWattSensor(
            coordinator,
            "postal_code",
            "Postal Code",
            None,
            None,
            None,
        ),
        HelloWattSensor(
            coordinator,
            "city",
            "City",
            None,
            None,
            None,
        ),
    ]

    async_add_entities(entities)


class HelloWattSensor(CoordinatorEntity, SensorEntity):
    """Representation of a HelloWatt Sensor."""

    def __init__(self, coordinator, key_id, name, device_class, unit, state_class):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key_id = key_id
        self._attr_name = f"HelloWatt {name}"
        self._attr_unique_id = f"{DOMAIN}_{key_id}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key_id)