"""The HelloWatt integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, time
from typing import Any
import zoneinfo

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import voluptuous as vol

from .client import HelloWattApiClient
from .const import DATA_AVAILABILITY_OFFSET_DAYS, DOMAIN, LOGGER
from .coordinator import HelloWattCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_IMPORT_HISTORICAL = "import_historical_data"
SERVICE_CLEAR_STATISTICS = "clear_statistics"

SERVICE_IMPORT_SCHEMA = vol.Schema(
    {
        vol.Required("start_date"): cv.date,
        vol.Optional("end_date"): cv.date,
        vol.Optional("pdl"): cv.string,
    }
)

SERVICE_CLEAR_SCHEMA = vol.Schema(
    {
        vol.Optional("pdl"): cv.string,
    }
)


async def _import_statistics(
    hass: HomeAssistant,
    pdl: str,
    energy_type: str,
    data: dict[str, Any],
) -> int:
    """Import statistics data into Home Assistant.

    Processes consumption data from the API and imports it into Home Assistant's
    statistics database for long-term storage and energy dashboard integration.

    Args:
        hass: Home Assistant instance
        pdl: Point de Livraison identifier
        energy_type: Type of energy ('electricity' or 'gas')
        data: API response containing consumption values and metadata

    Returns:
        Number of sensor types successfully imported

    Raises:
        Exception: If statistics import fails (logged but not propagated)
    """
    from homeassistant.components.recorder.statistics import async_import_statistics

    if not data or "values" not in data:
        return 0

    values = data.get("values", [])
    if not values:
        return 0

    # Prepare statistics for each sensor type
    statistics: dict[str, list[dict[str, Any]]] = {
        f"{energy_type}": [],  # Daily total
        f"{energy_type}_co2": [],  # CO2 emissions
        f"{energy_type}_cost": [],  # Total cost
        f"{energy_type}_cost_consumption": [],  # Consumption cost
        f"{energy_type}_cost_subscription": [],  # Subscription cost
    }

    # Add HP/HC statistics for electricity
    if energy_type == "electricity":
        statistics[f"{energy_type}_peak"] = []
        statistics[f"{energy_type}_off_peak"] = []

    for day_data in values:
        timestamp = day_data.get("datetime")
        if not timestamp:
            continue

        # Parse the date
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        kwh_detailed = day_data.get("kwhDetailed", {})
        total_kwh = sum(kwh_detailed.values())

        # Add daily total
        statistics[f"{energy_type}"].append(
            {
                "start": dt,
                "state": total_kwh,
                "sum": total_kwh,
            }
        )

        # Add CO2 if available
        if "valueCo2" in day_data:
            statistics[f"{energy_type}_co2"].append(
                {
                    "start": dt,
                    "state": day_data["valueCo2"],
                    "sum": day_data["valueCo2"],
                }
            )

        # Add cost data if available
        euros_detailed = day_data.get("eurosDetailed", {})
        if euros_detailed:
            total_cost = sum(euros_detailed.values())
            statistics[f"{energy_type}_cost"].append(
                {
                    "start": dt,
                    "state": total_cost,
                    "sum": total_cost,
                }
            )

            # Subscription cost
            subscription_cost = euros_detailed.get("subscription", 0)
            if subscription_cost > 0:
                statistics[f"{energy_type}_cost_subscription"].append(
                    {
                        "start": dt,
                        "state": subscription_cost,
                        "sum": subscription_cost,
                    }
                )

            # Consumption cost (total - subscription)
            consumption_cost = sum(
                v for k, v in euros_detailed.items() if k != "subscription"
            )
            if consumption_cost > 0:
                statistics[f"{energy_type}_cost_consumption"].append(
                    {
                        "start": dt,
                        "state": consumption_cost,
                        "sum": consumption_cost,
                    }
                )

        # Add HP/HC for electricity
        if energy_type == "electricity":
            if "HP" in kwh_detailed:
                statistics[f"{energy_type}_peak"].append(
                    {
                        "start": dt,
                        "state": kwh_detailed["HP"],
                        "sum": kwh_detailed["HP"],
                    }
                )
            if "HC" in kwh_detailed:
                statistics[f"{energy_type}_off_peak"].append(
                    {
                        "start": dt,
                        "state": kwh_detailed["HC"],
                        "sum": kwh_detailed["HC"],
                    }
                )

    # Import statistics for each sensor
    sensors_imported = 0
    for sensor_key, stats_data in statistics.items():
        if not stats_data:
            continue

        statistic_id = f"{DOMAIN}:{pdl}_{sensor_key}"

        # Determine metadata based on sensor type
        # Note: unit_class is required since HA 2026.11
        if "co2" in sensor_key:
            metadata = {
                "has_mean": False,
                "has_sum": True,
                "name": f"HelloWatt {pdl} - {sensor_key}",
                "source": DOMAIN,
                "statistic_id": statistic_id,
                "unit_of_measurement": "kg",
                "unit_class": "mass",
            }
        elif "cost" in sensor_key:
            metadata = {
                "has_mean": False,
                "has_sum": True,
                "name": f"HelloWatt {pdl} - {sensor_key}",
                "source": DOMAIN,
                "statistic_id": statistic_id,
                "unit_of_measurement": "EUR",
            }
        else:
            metadata = {
                "has_mean": False,
                "has_sum": True,
                "name": f"HelloWatt {pdl} - {sensor_key}",
                "source": DOMAIN,
                "statistic_id": statistic_id,
                "unit_of_measurement": "kWh",
                "unit_class": "energy",
            }

        try:
            # Use async_import_statistics which properly handles existing metadata
            # and avoids UNIQUE constraint errors
            result = await async_import_statistics(hass, metadata, stats_data)

            if result:
                sensors_imported += 1
                LOGGER.debug(
                    "Imported %d statistics for %s",
                    len(stats_data),
                    statistic_id,
                )
            else:
                LOGGER.debug(
                    "No new statistics imported for %s (may already exist)",
                    statistic_id,
                )
        except Exception as err:
            # Log at warning level so user can see the issue
            LOGGER.warning(
                "Failed to import statistics for %s: %s",
                statistic_id,
                str(err),
            )
            import traceback

            LOGGER.debug("Full traceback: %s", traceback.format_exc())

    return sensors_imported


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HelloWatt from a config entry."""

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    # Create a dedicated session with cookie jar for this integration
    session = async_create_clientsession(
        hass, cookie_jar=aiohttp.CookieJar(unsafe=True)
    )
    client = HelloWattApiClient(session, username, password)
    await client.authenticate()

    # Create coordinators for each home/PDL
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"client": client, "coordinators": {}}

    for home in client.homes:
        pdl = home.get("enedisHome", {}).get("pdl")
        home_id = home.get("id")
        if pdl and home_id:
            coordinator = HelloWattCoordinator(hass, client, entry, pdl, home_id, home)
            await coordinator.async_config_entry_first_refresh()
            hass.data[DOMAIN][entry.entry_id]["coordinators"][pdl] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async def async_import_historical_data(call: ServiceCall) -> None:
        """Handle the import historical data service call."""
        from dateutil.relativedelta import relativedelta

        start_date = call.data["start_date"]
        target_pdl = call.data.get("pdl")

        # Limit end_date to account for data availability
        # API typically has data available up to D-N days ago
        today = datetime.now().date()
        from datetime import timedelta

        max_available_date = today - timedelta(days=DATA_AVAILABILITY_OFFSET_DAYS)

        # Default to max available date instead of today
        end_date = call.data.get("end_date", max_available_date)

        if end_date > max_available_date:
            LOGGER.info(
                "End date %s is too recent (data typically available up to D-2), automatically adjusted to %s",
                end_date,
                max_available_date,
            )
            end_date = max_available_date

        LOGGER.info(
            "Importing historical data from %s to %s for PDL: %s (adjusted end_date: %s, today: %s, max_available: %s)",
            start_date,
            end_date,
            target_pdl or "all",
            end_date,
            today,
            max_available_date,
        )

        coordinators_dict = hass.data[DOMAIN][entry.entry_id]["coordinators"]

        # Filter coordinators by PDL if specified
        if target_pdl:
            coordinators_to_process = {
                pdl: coord
                for pdl, coord in coordinators_dict.items()
                if pdl == target_pdl
            }
        else:
            coordinators_to_process = coordinators_dict

        for pdl, coordinator in coordinators_to_process.items():
            try:
                LOGGER.info("Fetching historical data for PDL %s", pdl)

                # Import month by month to avoid API overload
                current_start = start_date
                total_months = 0

                while current_start <= end_date:
                    # Calculate end of current month
                    month_end = min(
                        datetime(current_start.year, current_start.month, 1).date()
                        + relativedelta(months=1)
                        - relativedelta(days=1),
                        end_date,
                    )

                    # Convert to datetime for API call with timezone
                    # Use 23:59:59 instead of datetime.max.time() to avoid microseconds
                    # Use Europe/Paris timezone for French energy data
                    tz = zoneinfo.ZoneInfo("Europe/Paris")
                    start_datetime = datetime.combine(
                        current_start, time(0, 0, 0), tzinfo=tz
                    )
                    end_datetime = datetime.combine(
                        month_end, time(23, 59, 59), tzinfo=tz
                    )

                    elec_sensors = 0
                    gas_sensors = 0

                    try:
                        # Fetch electricity data for this month
                        electricity_data = await client.get_daily_consumption(
                            coordinator.home_id, start_datetime, end_datetime
                        )

                        # Log data received for debugging
                        if electricity_data and "values" in electricity_data:
                            LOGGER.debug(
                                "Received %d days of electricity data for %s",
                                len(electricity_data["values"]),
                                current_start.strftime("%Y-%m"),
                            )
                        else:
                            LOGGER.warning(
                                "No electricity data received for %s (PDL %s)",
                                current_start.strftime("%Y-%m"),
                                pdl,
                            )

                        # Import electricity statistics
                        elec_sensors = await _import_statistics(
                            hass,
                            pdl,
                            "electricity",
                            electricity_data,
                        )
                    except Exception as elec_err:
                        import traceback

                        LOGGER.warning(
                            "Error importing electricity data for %s (PDL %s): %s",
                            current_start.strftime("%Y-%m"),
                            pdl,
                            elec_err,
                        )
                        LOGGER.debug(
                            "Full traceback for electricity import error: %s",
                            traceback.format_exc(),
                        )

                    try:
                        # Fetch gas data for this month if available
                        gas_data = await client.get_daily_gas_consumption(
                            coordinator.home_id, start_datetime, end_datetime
                        )

                        # Import gas statistics
                        gas_sensors = await _import_statistics(
                            hass,
                            pdl,
                            "gas",
                            gas_data,
                        )
                    except Exception as gas_err:
                        # Gas data not available (likely no gas contract)
                        LOGGER.debug(
                            "Skipping gas data import for %s (PDL %s): %s",
                            current_start.strftime("%Y-%m"),
                            pdl,
                            str(gas_err),
                        )

                    total_months += 1

                    # Calculate progress percentage
                    total_months_to_import = (
                        (end_date.year - start_date.year) * 12
                        + (end_date.month - start_date.month)
                        + 1
                    )
                    progress_pct = int((total_months / total_months_to_import) * 100)

                    # Log progress every month with sensor count and percentage
                    LOGGER.info(
                        "Progress: %d%% - Imported %s for PDL %s (%d electricity sensors, %d gas sensors)",
                        progress_pct,
                        current_start.strftime("%Y-%m"),
                        pdl,
                        elec_sensors,
                        gas_sensors,
                    )

                    # Add delay between months to reduce database load and prevent recorder warnings
                    # This helps prevent "logging too frequently" warnings from recorder
                    await asyncio.sleep(0.5)

                    # Move to next month
                    current_start = (
                        datetime(current_start.year, current_start.month, 1)
                        + relativedelta(months=1)
                    ).date()

                LOGGER.info(
                    "Completed: Successfully imported %d months of historical data for PDL %s",
                    total_months,
                    pdl,
                )

            except Exception as err:
                LOGGER.error("Error importing data for PDL %s: %s", pdl, err)

    async def async_clear_statistics(call: ServiceCall) -> None:
        """Handle the clear statistics service call.

        This clears both the statistics data AND metadata to remove old invalid entries.
        """
        target_pdl = call.data.get("pdl")

        coordinators_dict = hass.data[DOMAIN][entry.entry_id]["coordinators"]

        # Filter coordinators by PDL if specified
        if target_pdl:
            coordinators_to_process = {
                pdl: coord
                for pdl, coord in coordinators_dict.items()
                if pdl == target_pdl
            }
        else:
            coordinators_to_process = coordinators_dict

        # Build list of PDLs to clear
        pdls_to_clear = list(coordinators_to_process.keys())

        LOGGER.info(
            "Clearing all HelloWatt statistics for PDL(s): %s", ", ".join(pdls_to_clear)
        )

        from homeassistant.components.recorder import get_instance

        # Clear statistics data and metadata using recorder session
        def _clear_statistics_with_metadata():
            """Clear statistics and metadata in a recorder session."""
            from homeassistant.components.recorder.models import (
                Statistics,
                StatisticsMeta,
                StatisticsShortTerm,
            )
            from homeassistant.components.recorder.util import session_scope
            from sqlalchemy import delete

            with session_scope(hass=hass, read_only=False) as session:
                # Find ALL statistics metadata that starts with hellowatt: and contains any of our PDLs
                # This catches both current format and any old/malformed entries
                all_metadata = (
                    session.query(StatisticsMeta)
                    .filter(StatisticsMeta.source == DOMAIN)
                    .all()
                )

                metadata_ids_to_delete = []
                stats_found = []

                for meta in all_metadata:
                    stat_id = meta.statistic_id
                    # Check if this statistic_id contains any of our target PDLs
                    # This handles both "hellowatt:PDL_sensor" and any malformed variants
                    for pdl in pdls_to_clear:
                        if pdl in stat_id:
                            metadata_ids_to_delete.append(meta.id)
                            stats_found.append(stat_id)
                            break

                if metadata_ids_to_delete:
                    LOGGER.info(
                        "Found %d metadata entries to delete: %s",
                        len(metadata_ids_to_delete),
                        ", ".join(stats_found),
                    )

                    # Delete statistics data first (both long-term and short-term)
                    deleted_stats = session.execute(
                        delete(Statistics).where(
                            Statistics.metadata_id.in_(metadata_ids_to_delete)
                        )
                    ).rowcount

                    deleted_short = session.execute(
                        delete(StatisticsShortTerm).where(
                            StatisticsShortTerm.metadata_id.in_(metadata_ids_to_delete)
                        )
                    ).rowcount

                    # Then delete metadata
                    deleted_meta = session.execute(
                        delete(StatisticsMeta).where(
                            StatisticsMeta.id.in_(metadata_ids_to_delete)
                        )
                    ).rowcount

                    session.commit()

                    LOGGER.info(
                        "Deleted %d metadata entries, %d long-term statistics, and %d short-term statistics",
                        deleted_meta,
                        deleted_stats,
                        deleted_short,
                    )
                    return deleted_meta
                LOGGER.info("No metadata entries found to delete")
                return 0

        deleted_count = await get_instance(hass).async_add_executor_job(
            _clear_statistics_with_metadata
        )

        if deleted_count > 0:
            LOGGER.info(
                "Successfully cleared all statistics and metadata. Please restart Home Assistant before importing new data."
            )
        else:
            LOGGER.info("No statistics found to clear")

    # Register the services
    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_HISTORICAL,
        async_import_historical_data,
        schema=SERVICE_IMPORT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_STATISTICS,
        async_clear_statistics,
        schema=SERVICE_CLEAR_SCHEMA,
    )

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change.

    Args:
        hass: Home Assistant instance
        entry: Config entry that was updated
    """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Unregister services if no more entries
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_IMPORT_HISTORICAL)
            hass.services.async_remove(DOMAIN, SERVICE_CLEAR_STATISTICS)

    return unload_ok
