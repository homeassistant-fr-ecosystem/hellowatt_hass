"""Sensor platform for HelloWatt."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTemperature, UnitOfMass, CURRENCY_EURO
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import HelloWattCoordinator

# Define sensor configurations with metadata
SENSOR_TYPES: dict[str, dict[str, Any]] = {
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
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HelloWatt sensor platform.

    Creates sensor entities for all configured PDLs and all sensor types
    (electricity, gas, temperature, costs, CO2).

    Args:
        hass: Home Assistant instance
        entry: Config entry for this integration
        async_add_entities: Callback to add entities to Home Assistant
    """
    coordinators: dict[str, HelloWattCoordinator] = hass.data[DOMAIN][entry.entry_id][
        "coordinators"
    ]

    entities: list[HelloWattSensor] = []

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


class HelloWattSensor(CoordinatorEntity[HelloWattCoordinator], SensorEntity):
    """Representation of a HelloWatt Sensor.

    Each sensor represents a specific data point (electricity, gas, cost, etc.)
    for a particular PDL (Point de Livraison).
    """

    def __init__(
        self,
        coordinator: HelloWattCoordinator,
        pdl: str,
        key_id: str,
        name: str,
        device_class: SensorDeviceClass | None,
        unit: str | None,
        state_class: SensorStateClass | None,
        icon: str | None,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: Data coordinator for this PDL
            pdl: Point de Livraison identifier
            key_id: Sensor key in coordinator data (e.g., 'electricity', 'gas')
            name: Human-readable sensor name
            device_class: Home Assistant device class
            unit: Unit of measurement
            state_class: State class for statistics
            icon: MDI icon identifier
        """
        super().__init__(coordinator)
        self._pdl: str = pdl
        self._key_id: str = key_id
        self._attr_name: str = name
        self._attr_unique_id: str = f"{DOMAIN}_{pdl}_{key_id}"
        self._attr_device_class: SensorDeviceClass | None = device_class
        self._attr_state_class: SensorStateClass | None = state_class
        self._attr_native_unit_of_measurement: str | None = unit
        self._attr_icon: str | None = icon

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity.

        Groups all sensors for a PDL under a single device, including
        contract information if available.
        """
        # Get contract information from coordinator data
        contract_provider: str | None = self.coordinator.data.get("contract_provider")
        contract_offer: str | None = self.coordinator.data.get("contract_offer")

        device_info = DeviceInfo(
            identifiers={(DOMAIN, self._pdl)},
            name=f"HelloWatt {self._pdl}",
            manufacturer="HelloWatt",
            model="Energy Monitor",
            configuration_url="https://www.hellowatt.fr/mon-compte/",
        )

        # Add contract information as software version if available
        if contract_provider or contract_offer:
            device_info["sw_version"] = (
                f"{contract_provider or 'Unknown'} - {contract_offer or 'Unknown'}"
            )

        return device_info

    @property
    def native_value(self) -> float | int | str | None:
        """Return the current state of the sensor.

        Returns:
            Sensor value from coordinator data, or None if not available
        """
        return self.coordinator.data.get(self._key_id)

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Entity is available only if:
        - Coordinator is available (connected to API)
        - Coordinator has data
        - The specific sensor key exists in coordinator data

        Returns:
            True if entity is available, False otherwise
        """
        return (
            super().available
            and self.coordinator.data is not None
            and self._key_id in self.coordinator.data
        )