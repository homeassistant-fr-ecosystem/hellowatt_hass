# Developer Documentation

## Technical Overview

This document provides technical details for developers who want to understand, modify, or contribute to the HelloWatt Home Assistant integration.

## Architecture

### Component Flow

```
User Configuration (config_flow.py)
         ↓
Entry Setup (__init__.py)
         ↓
API Client Creation (client.py)
         ↓
Coordinator Setup (coordinator.py) [one per PDL]
         ↓
Sensor Creation (sensor.py) [multiple per coordinator]
```

### Authentication Flow

1. User enters credentials in config flow
2. `HelloWattApiClient.authenticate()` is called:
   - GET request to `/accounts/login/` to obtain CSRF token
   - POST credentials with CSRF token
   - Session cookie stored in ClientSession cookie jar
3. CSRF token extracted from cookie and added to headers for subsequent requests
4. On 403 errors, automatic re-authentication occurs

### Data Update Cycle

Every hour (configurable in [coordinator.py:25](custom_components/hellowatt/coordinator.py#L25)):

1. `HelloWattCoordinator._async_update_data()` executes
2. Fetches last 7 days of data (for reliability)
3. Processes latest available day (typically D-1)
4. Extracts:
   - Energy consumption (electricity/gas)
   - CO2 emissions
   - Cost breakdown
   - Temperature
   - Contract information
5. Updates all sensors via CoordinatorEntity pattern

## Key Classes

### HelloWattApiClient

**Location**: [client.py](custom_components/hellowatt/client.py)

**Purpose**: Handles all API communication with HelloWatt

**Key Methods**:
- `authenticate()`: Performs login and stores session
- `get_daily_consumption()`: Fetches electricity data
- `get_daily_gas_consumption()`: Fetches gas data
- `get_yearly_temperature()`: Fetches temperature data
- `get_contracts()`: Fetches contract information
- `_get_headers()`: Constructs headers with CSRF token

**Session Management**:
```python
# Cookie jar with unsafe=True required for cross-domain cookies
session = async_create_clientsession(
    hass,
    cookie_jar=aiohttp.CookieJar(unsafe=True)
)
```

**Error Handling**:
- 403 errors trigger automatic re-authentication
- Prevents recursive authentication with `_authenticating` flag
- Detailed error logging with response content

### HelloWattCoordinator

**Location**: [coordinator.py](custom_components/hellowatt/coordinator.py)

**Purpose**: Manages data fetching and distribution to sensors

**Extends**: `DataUpdateCoordinator`

**Update Interval**: 1 hour

**Data Structure Returned**:
```python
{
    "electricity": float,              # kWh total
    "electricity_peak": float,         # kWh (HP contracts only)
    "electricity_off_peak": float,     # kWh (HC contracts only)
    "electricity_yesterday": float,    # kWh
    "electricity_weekly": float,       # kWh
    "electricity_co2": float,          # kg
    "electricity_cost": float,         # EUR
    "electricity_cost_consumption": float,  # EUR
    "electricity_cost_subscription": float, # EUR
    "gas": float,                      # kWh
    "gas_yesterday": float,            # kWh
    "gas_weekly": float,               # kWh
    "gas_co2": float,                  # kg
    "gas_cost": float,                 # EUR
    "gas_cost_consumption": float,     # EUR
    "gas_cost_subscription": float,    # EUR
    "temperature": float,              # °C
    "contract_provider": str,          # active contract provider name (e.g. "EDF")
    "contract_offer": str,             # active contract offer name (e.g. "Tarif Bleu")
    "address": str,                    # home street address
    "postal_code": str,                # home postal code
    "city": str,                       # home city name
    "pdl": str,                        # PDL identifier (mirrors the coordinator key)
}
```

**Data Processing Logic**:
- Latest available day is typically index -1 (D-1)
- Day before is index -2 (D-2)
- Weekly total sums all available days in the 7-day window
- HP/HC sensors only created when data exists (not for base contracts)

### HelloWattSensor

**Location**: [sensor.py](custom_components/hellowatt/sensor.py)

**Purpose**: Individual sensor entity

**Extends**: `CoordinatorEntity`, `SensorEntity`

**Sensor Configuration**: Defined in `SENSOR_TYPES` dictionary at [sensor.py:17](custom_components/hellowatt/sensor.py#L17)

**Key Properties**:
- `device_info`: Groups sensors by PDL device
- `native_value`: Extracts value from coordinator data
- `available`: Checks if sensor data exists in coordinator

**Unique ID Format**: `hellowatt_{pdl}_{sensor_key}`

### importer.py

**Location**: [importer.py](custom_components/hellowatt/importer.py)

**Purpose**: All historical data import and statistics management — extracted from `__init__.py` to keep the entry module focused on setup.

**Key functions**:
- `async_import_historical_data(hass, call)`: Service handler. Validates and adjusts date range (limits to D-2), loads existing cumulative sums at the boundary, then iterates month-by-month calling `_import_statistics()` for electricity and gas.
- `async_clear_statistics(hass, call)`: Service handler. Lists all statistic IDs matching the PDL(s) and removes them via the recorder instance.
- `async _import_statistics(hass, pdl, energy_type, data, cumulative_sums=None) -> int`: Converts API `values` list to `StatisticData` objects for energy, CO2, cost, subscription, consumption, and HP/HC sensors. Clamps all negative values to 0 before accumulation.
- `_fetch_with_retry(fetch_coro_factory, max_retries=3, base_delay=5.0)`: Wraps any coroutine factory with up to 3 retries and exponential backoff (5s, 10s, 20s) on 5xx / gateway errors.
- `_load_existing_sums(hass, pdl, start_date)`: Queries the recorder for the last cumulative sum per sensor key strictly before `start_date`, so a partial re-import continues from the correct running total instead of restarting from zero.

**Service names**:
- `SERVICE_IMPORT_HISTORICAL = "import_historical_data"`
- `SERVICE_CLEAR_STATISTICS = "clear_statistics"`

### diagnostics.py

**Location**: [diagnostics.py](custom_components/hellowatt/diagnostics.py)

**Purpose**: Integration diagnostics for troubleshooting, conforming to the [HA diagnostics spec](https://developers.home-assistant.io/docs/core/integration_diagnostics).

**Functions**:
- `async_get_config_entry_diagnostics(hass, entry)`: Returns entry metadata (title, unique_id, state), current options, per-PDL coordinator status (home_id, update interval, last update time, available sensor keys, HP/HC detection), all entity states and attributes, and device info. Credentials are never included.
- `async_get_device_diagnostics(hass, entry, device)`: Returns coordinator and entity data scoped to a single PDL device. Includes all current sensor values.

**Access**: Settings > Devices & Services > HelloWatt > three-dot menu > **Download Diagnostics**

### system_health.py

**Location**: [system_health.py](custom_components/hellowatt/system_health.py)

**Purpose**: System health reporting conforming to the [HA system health spec](https://developers.home-assistant.io/docs/core/integration-system-health).

**Exposes** (visible in Settings > System > System Information):
- `api_endpoint_reachable`: whether `https://www.hellowatt.fr/api` is reachable
- `configured_accounts`: number of config entries loaded
- `total_pdl_coordinators`: total PDL coordinators across all entries

## API Endpoints

### Base URL
```
https://www.hellowatt.fr/api
```

### Authentication
```
POST https://www.hellowatt.fr/accounts/login/
Headers:
  User-Agent: Mozilla/5.0...
  Referer: https://www.hellowatt.fr/accounts/login/
Body:
  login: <email>
  password: <password>
  csrfmiddlewaretoken: <token>
```

### Get Homes
```
GET /homes
Headers:
  Accept: application/json; version=1.48
  X-Requested-With: XMLHttpRequest
  x-csrftoken: <token>
```

**Response**:
```json
[
  {
    "id": "home_id_123",
    "address": "123 Rue Example",
    "area": {
      "postalCode": "75001",
      "name": "Paris"
    },
    "enedisHome": {
      "pdl": "12345678901234"
    }
  }
]
```

### Get Daily Consumption (Electricity)
```
GET /homes/{home_id}/sge_measures/conso_daily
Params:
  startDate: 2024-01-01T00:00:00
  endDate: 2024-01-07T23:59:59
```

**Response**:
```json
{
  "values": [
    {
      "datetime": "2024-01-01T00:00:00Z",
      "kwhDetailed": {
        "HP": 15.5,
        "HC": 8.2
      },
      "valueCo2": 2.5,
      "eurosDetailed": {
        "HP": 2.33,
        "HC": 0.98,
        "subscription": 0.42
      }
    }
  ]
}
```

### Get Daily Consumption (Gas)
```
GET /homes/{home_id}/adict_measures/conso_daily
Params:
  startDate: 2024-01-01T00:00:00
  endDate: 2024-01-07T23:59:59
```

### Get Temperature
```
GET /homes/{home_id}/temperature_measures/yearly
Params:
  startDate: 2023-01-01T00:00:00
  endDate: 2024-01-01T23:59:59
```

### Get Contracts
```
GET /homes/{home_id}/contracts
```

**Response**:
```json
[
  {
    "contractState": "actual",
    "provider": {
      "name": "EDF"
    },
    "offer": {
      "name": "Tarif Bleu"
    }
  }
]
```

## Historical Data Import

### Service Implementation

**Location**: [importer.py](custom_components/hellowatt/importer.py)

**Service Name**: `hellowatt.import_historical_data`

**Processing Flow**:
1. Validate and adjust date range (limits to D-2)
2. Split import into monthly chunks
3. For each month:
   - Fetch electricity data
   - Import to statistics via `_import_statistics()`
   - Fetch gas data (if available)
   - Import to statistics
4. Log progress and errors

### Statistics Import

**Function**: `_import_statistics()` in [importer.py](custom_components/hellowatt/importer.py)

**Purpose**: Converts API data to Home Assistant statistics format

**Data Transformation**:
```python
# API format
{
  "datetime": "2024-01-01T00:00:00Z",
  "kwhDetailed": {"HP": 15.5, "HC": 8.2},
  "valueCo2": 2.5,
  "eurosDetailed": {"HP": 2.33, "HC": 0.98, "subscription": 0.42}
}

# Statistics format
{
  "start": datetime(2024, 1, 1),
  "state": 23.7,  # sum of kwhDetailed values
  "sum": 23.7
}
```

**Statistic IDs**: `hellowatt:{pdl}_{sensor_key}`

**Metadata**:
- Energy sensors: unit = "kWh", has_sum = True
- CO2 sensors: unit = "kg", has_sum = True
- Cost sensors: unit = "EUR", has_sum = True

### Statistics Clearing

**Service Name**: `hellowatt.clear_statistics`

**Processing Flow**:
1. Collect all PDL identifiers to clear (filtered by `pdl` parameter if provided)
2. Call `list_statistic_ids()` via the recorder executor to find all matching statistic IDs
3. Filter IDs that contain both the PDL string and the domain (`hellowatt`) or `sensor.hellowatt_{pdl}`
4. Call `instance.async_clear_statistics(ids_to_delete)` — queues the task on the recorder thread
5. Log the cleared IDs; user must restart HA to see the Energy Dashboard updated

## Configuration Flow

**Location**: [config_flow.py](custom_components/hellowatt/config_flow.py)

**Version**: 1

**Steps**:
1. `async_step_user`: Collects username and password
2. Sets unique ID to username (prevents duplicate entries)
3. Creates config entry titled "HelloWatt"

**Future Enhancements**:
- Add authentication validation
- Support for custom update intervals
- Options flow for reconfiguration

## Error Handling

### Authentication Errors
- Form errors returned in JSON response
- Session cookie validation
- Prevents recursive authentication attempts

### API Errors
- 403: Triggers re-authentication and retry
- Other errors: Logged with response content (limited to 500 chars)
- `UpdateFailed` exception raises sensor unavailability

### Data Availability
- Missing gas data handled gracefully (no error)
- Missing HP/HC data results in no peak/off-peak sensors
- Sensors marked unavailable if data key missing

## Testing Considerations

### Manual Testing Checklist
- [ ] Single PDL account
- [ ] Multiple PDL account
- [ ] Base rate electricity contract (no HP/HC)
- [ ] Dual rate electricity contract (HP/HC)
- [ ] Account with gas contract
- [ ] Account without gas contract
- [ ] Historical import with various date ranges
- [ ] Session expiration and re-authentication
- [ ] Network errors and recovery

### Test Data
Create test accounts with:
1. Electricity only (base rate)
2. Electricity only (HP/HC rate)
3. Electricity + Gas
4. Multiple homes/PDLs

## Performance Optimization

### Current Optimizations
- Single coordinator per PDL (not per sensor)
- 1-hour update interval (reduces API load)
- Fetches 7 days of data (reduces missing data issues)
- Monthly chunking for historical imports
- Graceful degradation for missing data

### Potential Improvements
- Cache contract data (rarely changes)
- Incremental statistics import (track last imported date)
- Configurable update interval
- Parallel historical imports for multiple PDLs

## Adding New Sensors

To add a new sensor type:

1. Add configuration to `SENSOR_TYPES` in [sensor.py:17](custom_components/hellowatt/sensor.py#L17):
```python
"new_sensor": {
    "name": "New Sensor Name",
    "device_class": SensorDeviceClass.ENERGY,
    "unit": UnitOfEnergy.KILO_WATT_HOUR,
    "state_class": SensorStateClass.TOTAL_INCREASING,
    "icon": "mdi:lightning-bolt",
}
```

2. Extract data in `HelloWattCoordinator._async_update_data()`:
```python
result["new_sensor"] = latest_conso.get("newField")
```

3. Update historical import if needed in `_import_statistics()`:
```python
statistics["new_sensor"] = []
# ... process and append data
```

## Debugging

### Enable Debug Logging

Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.hellowatt: debug
```

### Useful Log Messages
- Authentication success/failure
- API response errors with status codes
- Statistics import counts
- Coordinator update failures

### Inspecting API Responses
Check logs for error messages with response content:
```
API error for https://www.hellowatt.fr/api/homes/123/sge_measures/conso_daily:
status=403, response={"detail": "Authentication credentials were not provided."}
```

## Common Issues

### Issue: Sensors stuck at same value
**Cause**: API returns D-1 data, updates once per day
**Solution**: This is expected behavior

### Issue: Cost sensors missing
**Cause**: Contract doesn't include cost tracking
**Solution**: Check HelloWatt website for cost data availability

### Issue: Re-authentication loops
**Cause**: Invalid credentials or API changes
**Solution**: Check authentication error messages, verify credentials

### Issue: Historical import incomplete
**Cause**: API data availability limits or rate limiting
**Solution**: Import smaller date ranges, check API status

## Security Considerations

### Credentials Storage
- Stored in Home Assistant's secure storage
- Never logged or exposed in debug output

### API Communication
- HTTPS only
- Session cookies with HttpOnly flag
- CSRF token validation

### Input Validation
- Date range validation in service calls
- PDL format should be validated (future enhancement)

## Contributing Guidelines

1. **Code Style**: Follow Home Assistant's style guide
2. **Type Hints**: Use type hints for all function signatures
3. **Logging**: Use appropriate log levels (ERROR, WARNING, INFO, DEBUG)
4. **Error Handling**: Never expose sensitive data in errors
5. **Testing**: Test with real HelloWatt accounts before submitting
6. **Documentation**: Update both README.md and this file
7. **Commits**: Use clear, descriptive commit messages

## Future Enhancements

### Planned Features
- [ ] Support for real-time consumption (if API supports it)
- [ ] Energy dashboard integration improvements
- [ ] Monthly/yearly aggregated sensors
- [ ] Configurable update intervals
- [ ] Authentication validation in config flow
- [ ] Options flow for reconfiguration
- [ ] Unit tests with mocked API
- [ ] Support for multiple contract types

### API Enhancements Needed
- Real-time data endpoints
- Bulk historical data export
- WebSocket for live updates
- Dedicated API key authentication

## Version History

### 1.0.0 (Current)
- Initial release
- Multi-PDL support
- Electricity and gas monitoring
- Historical data import service
- CO2 and cost tracking
- Automatic re-authentication
