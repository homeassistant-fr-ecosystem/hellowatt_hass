"""DataUpdateCoordinator for HelloWatt."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .client import HelloWattApiClient
from .const import (
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_TEMPERATURE_LOOKBACK_DAYS,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
    LOGGER,
)


class HelloWattCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching HelloWatt data.

    Coordinates data updates for a single home/PDL, fetching electricity,
    gas, temperature, and contract information from the HelloWatt API.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: HelloWattApiClient,
        entry: ConfigEntry,
        pdl: str,
        home_id: str,
        home: dict[str, Any],
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            client: Authenticated HelloWatt API client
            entry: Config entry for this integration
            pdl: Point de Livraison (delivery point) identifier
            home_id: Home identifier from HelloWatt API
            home: Home data dictionary containing address and area info
        """
        # Get update interval from options, fallback to default
        update_hours = entry.options.get(
            "update_interval", DEFAULT_UPDATE_INTERVAL_HOURS
        )

        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_{pdl}",
            update_interval=timedelta(hours=update_hours),
        )
        self.client: HelloWattApiClient = client
        self.entry: ConfigEntry = entry
        self.pdl: str = pdl
        self.home_id: str = home_id
        self.home: dict[str, Any] = home

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from HelloWatt API.

        Fetches the last 7 days of data to ensure we have the latest available
        values. Due to energy provider delays, the most recent data is typically
        from yesterday (D-1).

        Returns:
            Dictionary containing all sensor data including electricity, gas,
            temperature, contract info, and address details

        Raises:
            UpdateFailed: If API communication fails
        """
        try:
            # Fetch last N days to ensure we have data
            # Get lookback days from options, fallback to default
            lookback_days = self.entry.options.get(
                "lookback_days", DEFAULT_LOOKBACK_DAYS
            )
            end_date = dt_util.now()
            start_date = end_date - timedelta(days=lookback_days)

            # Fetch electricity consumption
            data_conso = await self.client.get_daily_consumption(
                self.home_id, start_date, end_date
            )

            # Try to fetch gas consumption (may fail if no gas contract)
            try:
                data_gas = await self.client.get_daily_gas_consumption(
                    self.home_id, start_date, end_date
                )
            except Exception as err:
                LOGGER.debug("Gas fetch failed (no contract or API error): %s", err)
                data_gas = None

            # Fetch temperature (last year for monthly data)
            start_date_temp = end_date - timedelta(
                days=DEFAULT_TEMPERATURE_LOOKBACK_DAYS
            )
            data_temp = await self.client.get_yearly_temperature(
                self.home_id, start_date_temp, end_date
            )

            # Fetch contracts
            contracts = await self.client.get_contracts(self.home_id)

            result = {}

            # Process electricity consumption data
            # Note: API returns historical data, latest available is typically yesterday (D-1)
            values_conso = data_conso.get("values", [])
            if values_conso:
                # Latest available day (typically yesterday/D-1)
                latest_conso = values_conso[-1]
                kwh_detailed = latest_conso.get("kwhDetailed", {})
                result["electricity"] = sum(kwh_detailed.values())

                # Extract CO2 emissions if available
                if "valueCo2" in latest_conso:
                    result["electricity_co2"] = latest_conso.get("valueCo2")

                # Extract cost data if available
                euros_detailed = latest_conso.get("eurosDetailed", {})
                if euros_detailed:
                    result["electricity_cost"] = sum(euros_detailed.values())
                    # Separate subscription and consumption costs
                    if "subscription" in euros_detailed:
                        result["electricity_cost_subscription"] = euros_detailed.get(
                            "subscription", 0
                        )
                    # Calculate consumption cost (total - subscription)
                    consumption_cost = sum(
                        v for k, v in euros_detailed.items() if k != "subscription"
                    )
                    if consumption_cost != 0:
                        result["electricity_cost_consumption"] = consumption_cost

                # Extract peak/off-peak hours only if they exist (HP/HC contracts)
                # Don't add them for "base" contracts
                if "HP" in kwh_detailed:
                    result["electricity_peak"] = kwh_detailed.get("HP", 0)
                if "HC" in kwh_detailed:
                    result["electricity_off_peak"] = kwh_detailed.get("HC", 0)

                # Day before latest (typically D-2)
                if len(values_conso) >= 2:
                    yesterday_conso = values_conso[-2]
                    yesterday_kwh = yesterday_conso.get("kwhDetailed", {})
                    result["electricity_yesterday"] = sum(yesterday_kwh.values())

                # Calculate weekly total (last 7 days available)
                weekly_total = sum(
                    sum(day.get("kwhDetailed", {}).values()) for day in values_conso
                )
                result["electricity_weekly"] = weekly_total

            # Process gas consumption data
            # Note: API returns historical data, latest available is typically yesterday (D-1)
            if data_gas:
                values_gas = data_gas.get("values", [])
                if values_gas:
                    # Latest available day (typically yesterday/D-1)
                    latest_gas = values_gas[-1]
                    kwh_detailed_gas = latest_gas.get("kwhDetailed", {})
                    result["gas"] = sum(kwh_detailed_gas.values())

                    # Extract CO2 emissions if available
                    if "valueCo2" in latest_gas:
                        result["gas_co2"] = latest_gas.get("valueCo2")

                    # Extract cost data if available
                    euros_detailed_gas = latest_gas.get("eurosDetailed", {})
                    if euros_detailed_gas:
                        result["gas_cost"] = sum(euros_detailed_gas.values())
                        # Separate subscription and consumption costs
                        if "subscription" in euros_detailed_gas:
                            result["gas_cost_subscription"] = euros_detailed_gas.get(
                                "subscription", 0
                            )
                        # Calculate consumption cost (total - subscription)
                        consumption_cost_gas = sum(
                            v
                            for k, v in euros_detailed_gas.items()
                            if k != "subscription"
                        )
                        if consumption_cost_gas != 0:
                            result["gas_cost_consumption"] = consumption_cost_gas

                    # Day before latest (typically D-2)
                    if len(values_gas) >= 2:
                        yesterday_gas = values_gas[-2]
                        yesterday_kwh_gas = yesterday_gas.get("kwhDetailed", {})
                        result["gas_yesterday"] = sum(yesterday_kwh_gas.values())

                    # Calculate weekly total (last 7 days available)
                    weekly_total_gas = sum(
                        sum(day.get("kwhDetailed", {}).values()) for day in values_gas
                    )
                    result["gas_weekly"] = weekly_total_gas

            # Process temperature
            values_temp = data_temp.get("values", [])
            if values_temp:
                latest_temp = values_temp[-1]
                result["temperature"] = latest_temp.get("valueCelsius")

            # Process contracts
            if contracts:
                # Find active contract or fallback to the first one
                active_contract = next(
                    (c for c in contracts if c.get("contractState") == "actual"),
                    contracts[0],
                )
                if active_contract:
                    result["contract_provider"] = active_contract.get(
                        "provider", {}
                    ).get("name")
                    result["contract_offer"] = active_contract.get("offer", {}).get(
                        "name"
                    )

            # Process home info
            result["address"] = self.home.get("address")
            result["postal_code"] = self.home.get("area", {}).get("postalCode")
            result["city"] = self.home.get("area", {}).get("name")
            result["pdl"] = self.pdl

            return result

        except aiohttp.ClientResponseError as err:
            # Handle 403/401 as authentication failures
            if err.status in (401, 403):
                raise ConfigEntryAuthFailed(
                    "Authentication failed. Please reauthenticate."
                ) from err
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            error_str = str(err).lower()
            # Check if the error is authentication-related
            if "authentication failed" in error_str or "no session cookie" in error_str:
                raise ConfigEntryAuthFailed(
                    "Authentication failed. Please reauthenticate."
                ) from err
            raise UpdateFailed(f"Error communicating with API: {err}") from err
