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

    def __init__(self, hass: HomeAssistant, client: HelloWattApiClient) -> None:
        """Initialize."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )
        self.client = client

    async def _async_update_data(self):
        """Fetch data from HelloWatt API."""
        try:
            # Fetch last 7 days to ensure we have data
            end_date = dt_util.now()
            start_date = end_date - timedelta(days=7)

            data_conso = await self.client.get_daily_consumption(start_date, end_date)

            # Fetch temperature (last 365 days for monthly data)
            start_date_temp = end_date - timedelta(days=365)
            data_temp = await self.client.get_yearly_temperature(start_date_temp, end_date)

            # Fetch contracts
            contracts = await self.client.get_contracts()

            # Fetch homes
            homes = await self.client.get_homes()

            result = {}

            # Process data to find the latest value
            values_conso = data_conso.get("values", [])
            if values_conso:
                latest_conso = values_conso[-1]
                kwh_detailed = latest_conso.get("kwhDetailed", {})
                result["electricity"] = sum(kwh_detailed.values())

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

            # Process homes
            if homes:
                # Find home matching the configured PDL
                home = next(
                    (h for h in homes if h.get("enedisHome", {}).get("pdl") == self.client.pdl),
                    None
                )
                if not home and homes:
                    home = homes[0]

                if home:
                    result["address"] = home.get("address")
                    result["postal_code"] = home.get("area", {}).get("postalCode")
                    result["city"] = home.get("area", {}).get("name")

            return result

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")