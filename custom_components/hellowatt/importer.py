"""Import historical data for HelloWatt."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, time
import logging
import traceback
import zoneinfo

import voluptuous as vol
from dateutil.relativedelta import relativedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
)
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
try:
    from homeassistant.components.recorder.models import StatisticMeanType
except ImportError:
    class StatisticMeanType:
        ARITHMETIC = "arithmetic"

from .const import DOMAIN

LOGGER = logging.getLogger(__name__)

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
    data: dict,
    cumulative_sums: dict[str, float] | None = None,
) -> int:
    """Import statistics data into Home Assistant.

    Returns the number of sensor types imported.
    """
    if not data or "values" not in data:
        return 0

    values = data.get("values", [])
    if not values:
        return 0

    # Prepare statistics for each sensor type
    statistics = {
        energy_type: [],  # Daily total
        f"{energy_type}_co2": [],  # CO2 emissions
        f"{energy_type}_cost": [],  # Total cost
        f"{energy_type}_cost_consumption": [],  # Consumption cost
        f"{energy_type}_cost_subscription": [],  # Subscription cost
    }

    # Add HP/HC statistics for electricity
    if energy_type == "electricity":
        statistics[f"{energy_type}_peak"] = []
        statistics[f"{energy_type}_off_peak"] = []

    # Initialize cumulative sums if not provided
    if cumulative_sums is None:
        cumulative_sums = {}

    # Ensure keys exist for this energy_type
    for key in [
        energy_type,
        f"{energy_type}_co2",
        f"{energy_type}_cost",
        f"{energy_type}_cost_consumption",
        f"{energy_type}_cost_subscription",
        f"{energy_type}_peak",
        f"{energy_type}_off_peak",
    ]:
        if key not in cumulative_sums:
            cumulative_sums[key] = 0.0

    for day_data in values:
        timestamp = day_data.get("datetime")
        if not timestamp:
            continue

        # Parse the date
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except Exception:
            continue

        endDt = dt.replace(hour=23, minute=59, second=59)

        kwh_detailed = day_data.get("kwhDetailed", {})
        total_kwh = sum(kwh_detailed.values())

        # Update cumulative sum
        cumulative_sums[energy_type] += total_kwh

        # Add daily total
        statistics[energy_type].append(
            StatisticData(
                start=dt,
                end=endDt,
                state=total_kwh,
                sum=cumulative_sums[energy_type],
            )
        )

        # Add CO2 if available
        if "valueCo2" in day_data:
            val_co2 = day_data["valueCo2"]
            cumulative_sums[f"{energy_type}_co2"] += val_co2
            statistics[f"{energy_type}_co2"].append(
                StatisticData(
                    start=dt,
                    end=endDt,
                    state=val_co2,
                    sum=cumulative_sums[f"{energy_type}_co2"],
                )
            )

        # Add cost data if available
        euros_detailed = day_data.get("eurosDetailed", {})
        if euros_detailed:
            total_cost = sum(euros_detailed.values())
            cumulative_sums[f"{energy_type}_cost"] += total_cost
            statistics[f"{energy_type}_cost"].append(
                StatisticData(
                    start=dt,
                    end=endDt,
                    state=total_cost,
                    sum=cumulative_sums[f"{energy_type}_cost"],
                )
            )

            # Subscription cost
            subscription_cost = euros_detailed.get("subscription", 0)
            if subscription_cost > 0:
                cumulative_sums[f"{energy_type}_cost_subscription"] += subscription_cost
                statistics[f"{energy_type}_cost_subscription"].append(
                   StatisticData(
                        start=dt,
                        end=endDt,
                        state=subscription_cost,
                        sum=cumulative_sums[f"{energy_type}_cost_subscription"],
                   )
                )

            # Consumption cost (total - subscription)
            consumption_cost = sum(v for k, v in euros_detailed.items() if k != "subscription")
            if consumption_cost > 0:
                cumulative_sums[f"{energy_type}_cost_consumption"] += consumption_cost
                statistics[f"{energy_type}_cost_consumption"].append(
                    StatisticData(
                        start=dt,
                        end=endDt,
                        state=consumption_cost,
                        sum=cumulative_sums[f"{energy_type}_cost_consumption"],
                    )
                )

        # Add HP/HC for electricity
        if energy_type == "electricity":
            if "HP" in kwh_detailed:
                val_hp = kwh_detailed["HP"]
                cumulative_sums[f"{energy_type}_peak"] += val_hp
                statistics[f"{energy_type}_peak"].append(
                    StatisticData(
                        start=dt,
                        end=endDt,
                        state=val_hp,
                        sum=cumulative_sums[f"{energy_type}_peak"],
                    )
                )
            if "HC" in kwh_detailed:
                val_hc = kwh_detailed["HC"]
                cumulative_sums[f"{energy_type}_off_peak"] += val_hc
                statistics[f"{energy_type}_off_peak"].append(
                    StatisticData(
                        start=dt,
                        end=endDt,
                        state=val_hc,
                        sum=cumulative_sums[f"{energy_type}_off_peak"],
                    )
                )

    # Get entity registry
    registry = er.async_get(hass)

    # Import statistics for each sensor
    sensors_imported = 0
    for sensor_key, stats_data in statistics.items():
        if not stats_data:
            continue

        # Find the entity ID
        unique_id = f"{DOMAIN}_{pdl}_{sensor_key}"
        entity_id = registry.async_get_entity_id(Platform.SENSOR, DOMAIN, unique_id)

        if not entity_id:
            LOGGER.debug("Entity not found for unique_id %s, skipping import", unique_id)
            continue

        statistic_id = entity_id

        # Determine metadata based on sensor type
        # Note: unit_class is required since HA 2026.11
        if "co2" in sensor_key:
            metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=None,
                source="recorder",
                statistic_id=statistic_id,
                unit_of_measurement="kg",
                unit_class="mass",
                mean_type=StatisticMeanType.ARITHMETIC,
            )
        elif "cost" in sensor_key:
            metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=None,
                source="recorder",
                statistic_id=statistic_id,
                unit_of_measurement="EUR",
                unit_class=None,
                mean_type=StatisticMeanType.ARITHMETIC,
            )
        else:
            metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=None,
                source="recorder",
                statistic_id=statistic_id,
                unit_of_measurement="kWh",
                unit_class="energy",
                mean_type=StatisticMeanType.ARITHMETIC,
            )

        try:
            # Use async_import_statistics which properly handles existing metadata
            # and avoids UNIQUE constraint errors
            result = async_import_statistics(hass, metadata, stats_data)

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
            LOGGER.debug("Full traceback: %s", traceback.format_exc())

    return sensors_imported


async def async_import_historical_data(hass: HomeAssistant, entry: ConfigEntry, call: ServiceCall) -> None:
    """Handle the import historical data service call."""
    start_date = call.data["start_date"]
    target_pdl = call.data.get("pdl")

    # Limit end_date to account for data availability
    # API typically has data available up to D-2 (2 days ago)
    today = datetime.now().date()
    max_available_date = today - timedelta(days=2)

    # Default to max available date instead of today
    end_date = call.data.get("end_date", max_available_date)

    if end_date > max_available_date:
        LOGGER.info(
            "End date %s is too recent (data typically available up to D-2), automatically adjusted to %s",
            end_date,
            max_available_date
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

    data = hass.data[DOMAIN][entry.entry_id]
    client = data["client"]
    coordinators_dict = data["coordinators"]

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
            # Find home_id for this PDL
            home_id = next(
                (h.get("id") for h in client.homes if h.get("enedisHome", {}).get("pdl") == pdl),
                None
            )
            if not home_id:
                LOGGER.error("Could not find home_id for PDL %s", pdl)
                continue

            LOGGER.info("Fetching historical data for PDL %s", pdl)

            # Import month by month to avoid API overload
            current_start = start_date
            total_months = 0

            # Initialize cumulative sums for this PDL to persist across months
            pdl_cumulative_sums = {}

            while current_start <= end_date:
                # Calculate end of current month
                month_end = min(
                    datetime(current_start.year, current_start.month, 1).date() + relativedelta(months=1) - relativedelta(days=1),
                    end_date
                )

                # Convert to datetime for API call with timezone
                # Use 23:59:59 instead of datetime.max.time() to avoid microseconds
                # Use Europe/Paris timezone for French energy data
                tz = zoneinfo.ZoneInfo("Europe/Paris")
                start_datetime = datetime.combine(current_start, time(0, 0, 0), tzinfo=tz)
                end_datetime = datetime.combine(month_end, time(23, 59, 59), tzinfo=tz)

                elec_sensors = 0
                gas_sensors = 0

                try:
                    # Fetch electricity data for this month
                    electricity_data = await client.get_daily_consumption(
                        home_id, start_datetime, end_datetime
                    )

                    # Log data received for debugging
                    if electricity_data and "values" in electricity_data:
                        LOGGER.debug(
                            "Received %d days of electricity data for %s",
                            len(electricity_data["values"]),
                            current_start.strftime("%Y-%m")
                        )
                    else:
                        LOGGER.warning(
                            "No electricity data received for %s (PDL %s)",
                            current_start.strftime("%Y-%m"),
                            pdl
                        )

                    # Import electricity statistics
                    elec_sensors = await _import_statistics(
                        hass,
                        pdl,
                        "electricity",
                        electricity_data,
                        cumulative_sums=pdl_cumulative_sums,
                    )
                except Exception as elec_err:
                    LOGGER.warning(
                        "Error importing electricity data for %s (PDL %s): %s",
                        current_start.strftime("%Y-%m"),
                        pdl,
                        elec_err
                    )
                    LOGGER.debug(
                        "Full traceback for electricity import error: %s",
                        traceback.format_exc()
                    )

                try:
                    # Fetch gas data for this month if available
                    # Note: get_daily_gas_consumption might not be implemented in client yet
                    if hasattr(client, "get_daily_gas_consumption"):
                        gas_data = await client.get_daily_gas_consumption(
                            home_id, start_datetime, end_datetime
                        )

                        # Import gas statistics
                        gas_sensors = await _import_statistics(
                            hass,
                            pdl,
                            "gas",
                            gas_data,
                            cumulative_sums=pdl_cumulative_sums,
                        )
                except Exception as gas_err:
                    # Gas data not available (likely no gas contract)
                    LOGGER.debug(
                        "Skipping gas data import for %s (PDL %s): %s",
                        current_start.strftime("%Y-%m"),
                        pdl,
                        str(gas_err)
                    )

                total_months += 1

                # Calculate progress percentage
                total_months_to_import = (
                    (end_date.year - start_date.year) * 12 +
                    (end_date.month - start_date.month) + 1
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
                current_start = (datetime(current_start.year, current_start.month, 1) + relativedelta(months=1)).date()

            LOGGER.info(
                "Completed: Successfully imported %d months of historical data for PDL %s",
                total_months,
                pdl
            )

        except Exception as err:
            LOGGER.error("Error importing data for PDL %s: %s", pdl, err)


async def async_clear_statistics(hass: HomeAssistant, entry: ConfigEntry, call: ServiceCall) -> None:
    """Handle the clear statistics service call.

    This clears both the statistics data AND metadata to remove old invalid entries.
    """
    target_pdl = call.data.get("pdl")

    data = hass.data[DOMAIN][entry.entry_id]
    coordinators_dict = data["coordinators"]

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
        "Clearing all HelloWatt statistics for PDL(s): %s",
        ", ".join(pdls_to_clear)
    )

    # Clear statistics data and metadata using recorder session
    def _clear_statistics_with_metadata():
        """Clear statistics and metadata in a recorder session."""
        from homeassistant.components.recorder.util import session_scope
        from sqlalchemy import delete
        try:
            from homeassistant.components.recorder.db_schema import StatisticsMeta, Statistics, StatisticsShortTerm
        except ImportError:
            from homeassistant.components.recorder.models import StatisticsMeta, Statistics, StatisticsShortTerm

        with session_scope(hass=hass, read_only=False) as session:
            # Find ALL statistics metadata that starts with hellowatt: and contains any of our PDLs
            # This catches both current format and any old/malformed entries
            all_metadata = session.query(StatisticsMeta).filter(
                StatisticsMeta.source == DOMAIN
            ).all()

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
                    ", ".join(stats_found)
                )

                # Delete statistics data first (both long-term and short-term)
                deleted_stats = session.execute(
                    delete(Statistics).where(Statistics.metadata_id.in_(metadata_ids_to_delete))
                ).rowcount

                deleted_short = session.execute(
                    delete(StatisticsShortTerm).where(StatisticsShortTerm.metadata_id.in_(metadata_ids_to_delete))
                ).rowcount

                # Then delete metadata
                deleted_meta = session.execute(
                    delete(StatisticsMeta).where(StatisticsMeta.id.in_(metadata_ids_to_delete))
                ).rowcount

                session.commit()

                LOGGER.info(
                    "Deleted %d metadata entries, %d long-term statistics, and %d short-term statistics",
                    deleted_meta,
                    deleted_stats,
                    deleted_short
                )
                return deleted_meta
            else:
                LOGGER.info("No metadata entries found to delete")
                return 0

    deleted_count = await get_instance(hass).async_add_executor_job(_clear_statistics_with_metadata)

    if deleted_count > 0:
        LOGGER.info("Successfully cleared all statistics and metadata. Please restart Home Assistant before importing new data.")
    else:
        LOGGER.info("No statistics found to clear")
