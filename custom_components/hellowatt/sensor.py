"""Sensor platform for HelloWatt."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfTemperature, UnitOfMass, CURRENCY_EURO
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

# Define sensor configurations
SENSOR_TYPES = {
    "electricity": {
        "name": "Electricity Daily",
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:lightning-bolt",
    },
    "electricity_peak": {
        "name": "Electricity Peak Hours Daily",
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:weather-sunny",
    },
    "electricity_off_peak": {
        "name": "Electricity Off-Peak Hours Daily",
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:weather-night",
    },
    "electricity_yesterday": {
        "name": "Electricity Day Before",
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:calendar-minus",
    },
    "electricity_weekly": {
        "name": "Electricity Weekly",
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:calendar-week",
    },
    "gas": {
        "name": "Gas Daily",
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:fire",
    },
    "gas_yesterday": {
        "name": "Gas Day Before",
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:fire-circle",
    },
    "gas_weekly": {
        "name": "Gas Weekly",
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:fire-alert",
    },
    "temperature": {
        "name": "Temperature",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": None,
    },
    "electricity_co2": {
        "name": "Electricity CO2 Emissions Daily",
        "device_class": SensorDeviceClass.WEIGHT,
        "unit": UnitOfMass.KILOGRAMS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:molecule-co2",
    },
    "gas_co2": {
        "name": "Gas CO2 Emissions Daily",
        "device_class": SensorDeviceClass.WEIGHT,
        "unit": UnitOfMass.KILOGRAMS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:molecule-co2",
    },
    "electricity_cost": {
        "name": "Electricity Cost Daily",
        "device_class": SensorDeviceClass.MONETARY,
        "unit": CURRENCY_EURO,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:currency-eur",
    },
    "electricity_cost_consumption": {
        "name": "Electricity Cost Consumption Daily",
        "device_class": SensorDeviceClass.MONETARY,
        "unit": CURRENCY_EURO,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:cash",
    },
    "electricity_cost_subscription": {
        "name": "Electricity Cost Subscription Daily",
        "device_class": SensorDeviceClass.MONETARY,
        "unit": CURRENCY_EURO,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:cash-clock",
    },
    "gas_cost": {
        "name": "Gas Cost Daily",
        "device_class": SensorDeviceClass.MONETARY,
        "unit": CURRENCY_EURO,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:currency-eur",
    },
    "gas_cost_consumption": {
        "name": "Gas Cost Consumption Daily",
        "device_class": SensorDeviceClass.MONETARY,
        "unit": CURRENCY_EURO,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:cash",
    },
    "gas_cost_subscription": {
        "name": "Gas Cost Subscription Daily",
        "device_class": SensorDeviceClass.MONETARY,
        "unit": CURRENCY_EURO,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:cash-clock",
    },
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HelloWatt sensor."""
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]

    entities = []

    # Create sensors for each PDL
    for pdl, coordinator in coordinators.items():
        # Add all sensor types
        for sensor_key, sensor_config in SENSOR_TYPES.items():
            entities.append(
                HelloWattSensor(
                    coordinator,
                    pdl,
                    sensor_key,
                    sensor_config["name"],
                    sensor_config["device_class"],
                    sensor_config["unit"],
                    sensor_config["state_class"],
                    sensor_config["icon"],
                )
            )

    async_add_entities(entities)


class HelloWattSensor(CoordinatorEntity, SensorEntity):
    """Representation of a HelloWatt Sensor."""

    def __init__(self, coordinator, pdl, key_id, name, device_class, unit, state_class, icon):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._pdl = pdl
        self._key_id = key_id
        self._attr_name = f"{name}"
        self._attr_unique_id = f"{DOMAIN}_{pdl}_{key_id}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        # Get contract information from coordinator data
        contract_provider = self.coordinator.data.get("contract_provider")
        contract_offer = self.coordinator.data.get("contract_offer")

        device_info = DeviceInfo(
            identifiers={(DOMAIN, self._pdl)},
            name=f"HelloWatt {self._pdl}",
            manufacturer="HelloWatt",
            model="Energy Monitor",
            configuration_url="https://www.hellowatt.fr/mon-compte/",
        )

        # Add contract information as device attributes if available
        if contract_provider or contract_offer:
            device_info["sw_version"] = f"{contract_provider or 'Unknown'} - {contract_offer or 'Unknown'}"

        return device_info

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key_id)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Entity is available if coordinator has data and the specific sensor value exists
        return (
            super().available
            and self.coordinator.data is not None
            and self._key_id in self.coordinator.data
        )