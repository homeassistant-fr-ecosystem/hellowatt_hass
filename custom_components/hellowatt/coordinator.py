"""DataUpdateCoordinator for HelloWatt."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER
from .client import HelloWattApiClient

class HelloWattCoordinator(DataUpdateCoordinator):
    """Class to manage fetching HelloWatt data."""

    def __init__(self, hass: HomeAssistant, client: HelloWattApiClient, pdl: str, home_id: str, home: dict) -> None:
        """Initialize."""
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_{pdl}",
            update_interval=timedelta(hours=1),
        )
        self.client = client
        self.pdl = pdl
        self.home_id = home_id
        self.home = home

    async def _async_update_data(self):
        """Fetch data from HelloWatt API."""
        try:
            # Fetch last 7 days to ensure we have data
            end_date = dt_util.now()
            start_date = end_date - timedelta(days=7)

            # Fetch electricity consumption
            data_conso = await self.client.get_daily_consumption(self.home_id, start_date, end_date)

            # Try to fetch gas consumption (may fail if no gas contract)
            try:
                data_gas = await self.client.get_daily_gas_consumption(self.home_id, start_date, end_date)
            except Exception:
                data_gas = None

            # Fetch temperature (last 365 days for monthly data)
            start_date_temp = end_date - timedelta(days=365)
            data_temp = await self.client.get_yearly_temperature(self.home_id, start_date_temp, end_date)

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
                    sum(day.get("kwhDetailed", {}).values())
                    for day in values_conso
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

                    # Day before latest (typically D-2)
                    if len(values_gas) >= 2:
                        yesterday_gas = values_gas[-2]
                        yesterday_kwh_gas = yesterday_gas.get("kwhDetailed", {})
                        result["gas_yesterday"] = sum(yesterday_kwh_gas.values())

                    # Calculate weekly total (last 7 days available)
                    weekly_total_gas = sum(
                        sum(day.get("kwhDetailed", {}).values())
                        for day in values_gas
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
                    contracts[0]
                )
                if active_contract:
                    result["contract_provider"] = active_contract.get("provider", {}).get("name")
                    result["contract_offer"] = active_contract.get("offer", {}).get("name")

            # Process home info
            result["address"] = self.home.get("address")
            result["postal_code"] = self.home.get("area", {}).get("postalCode")
            result["city"] = self.home.get("area", {}).get("name")
            result["pdl"] = self.pdl

            return result

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")