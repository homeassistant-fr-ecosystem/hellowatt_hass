# HelloWatt Home Assistant Integration

A custom Home Assistant integration for monitoring your energy consumption data from HelloWatt, a French energy monitoring service.

## Features

This integration provides real-time access to your energy consumption data:

### Electricity Monitoring
- Daily electricity consumption (kWh)
- Peak hours (HP) and off-peak hours (HC) consumption for dual-rate contracts
- Yesterday's consumption
- Weekly consumption total
- CO2 emissions tracking
- Cost breakdown (total, consumption, and subscription costs)

### Gas Monitoring
- Daily gas consumption (kWh)
- Yesterday's consumption
- Weekly consumption total
- CO2 emissions tracking
- Cost breakdown (total, consumption, and subscription costs)

### Additional Features
- Temperature monitoring
- Historical data import service
- Multi-home/PDL support
- Automatic session management with re-authentication
- Device information with contract details

## Installation

### Manual Installation

1. Copy the `custom_components/hellowatt` directory to your Home Assistant `custom_components` folder:
   ```
   <config_directory>/custom_components/hellowatt/
   ```

2. Restart Home Assistant

3. Go to Configuration > Integrations

4. Click the + button and search for "HelloWatt"

5. Enter your HelloWatt credentials (email and password)

### HACS Installation (when available)

This integration is not yet available in HACS. Follow the manual installation steps above.

## Configuration

### Initial Setup

1. Navigate to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "HelloWatt"
4. Enter your HelloWatt account credentials:
   - Email: Your HelloWatt account email
   - Password: Your HelloWatt account password

The integration will automatically discover all homes (PDLs) associated with your account and create sensors for each.

## Sensors

The integration creates the following sensors for each PDL (Point de Livraison):

### Electricity Sensors
| Sensor | Description | Unit | State Class |
|--------|-------------|------|-------------|
| `sensor.electricity_daily` | Today's electricity consumption | kWh | total_increasing |
| `sensor.electricity_peak_hours_daily` | Peak hours consumption (HP contracts) | kWh | total_increasing |
| `sensor.electricity_off_peak_hours_daily` | Off-peak hours consumption (HC contracts) | kWh | total_increasing |
| `sensor.electricity_day_before` | Yesterday's consumption | kWh | total_increasing |
| `sensor.electricity_weekly` | Last 7 days consumption | kWh | total_increasing |
| `sensor.electricity_co2_emissions_daily` | Daily CO2 emissions | kg | total_increasing |
| `sensor.electricity_cost_daily` | Total daily electricity cost | EUR | total |
| `sensor.electricity_cost_consumption_daily` | Consumption cost only | EUR | total |
| `sensor.electricity_cost_subscription_daily` | Subscription cost | EUR | total |

### Gas Sensors
| Sensor | Description | Unit | State Class |
|--------|-------------|------|-------------|
| `sensor.gas_daily` | Today's gas consumption | kWh | total_increasing |
| `sensor.gas_day_before` | Yesterday's consumption | kWh | total_increasing |
| `sensor.gas_weekly` | Last 7 days consumption | kWh | total_increasing |
| `sensor.gas_co2_emissions_daily` | Daily CO2 emissions | kg | total_increasing |
| `sensor.gas_cost_daily` | Total daily gas cost | EUR | total |
| `sensor.gas_cost_consumption_daily` | Consumption cost only | EUR | total |
| `sensor.gas_cost_subscription_daily` | Subscription cost | EUR | total |

### Other Sensors
| Sensor | Description | Unit | State Class |
|--------|-------------|------|-------------|
| `sensor.temperature` | Current temperature | °C | measurement |

## Services

### hellowatt.import_historical_data

Import historical consumption data from HelloWatt into Home Assistant's long-term statistics.

**Parameters:**
- `start_date` (required): Start date for import (YYYY-MM-DD)
- `end_date` (optional): End date for import (YYYY-MM-DD), defaults to 2 days ago
- `pdl` (optional): Specific PDL to import data for, leave empty to import all PDLs

**Example:**
```yaml
service: hellowatt.import_historical_data
data:
  start_date: "2023-01-01"
  end_date: "2024-12-31"
  pdl: "12345678901234"
```

**Notes:**
- Data is imported month by month to avoid API rate limits
- The API typically has data available up to D-2 (2 days ago)
- Historical data is imported into Home Assistant's statistics database
- Supports both electricity and gas data where available

## Data Update

- The integration polls the HelloWatt API every hour
- Data represents consumption from the previous day (D-1), as energy providers typically report with a 1-day delay
- Automatic re-authentication handles session expiration

## Device Information

Each PDL appears as a separate device in Home Assistant with the following information:
- Manufacturer: HelloWatt
- Model: Energy Monitor
- Software Version: Contract provider and offer name
- Configuration URL: Direct link to HelloWatt account dashboard

## Architecture

### Components

#### [\_\_init\_\_.py](custom_components/hellowatt/__init__.py)
Main integration setup and historical data import service:
- Entry setup and teardown
- API client initialization with cookie-based session management
- Multi-PDL coordinator creation
- Historical data import service registration
- Statistics import functionality

#### [client.py](custom_components/hellowatt/client.py)
HelloWatt API client:
- Session-based authentication with CSRF token handling
- Automatic session refresh on 403 errors
- Methods for fetching consumption data (electricity and gas)
- Temperature and contract data retrieval
- Comprehensive error logging

#### [coordinator.py](custom_components/hellowatt/coordinator.py)
Data update coordinator:
- Hourly data refresh
- Fetches 7 days of historical data for reliability
- Processes electricity, gas, and temperature data
- Extracts contract information
- Error handling with `UpdateFailed` exceptions

#### [sensor.py](custom_components/hellowatt/sensor.py)
Sensor platform implementation:
- Dynamic sensor creation based on available data
- Device grouping by PDL
- Support for energy, cost, and CO2 sensors
- Proper Home Assistant entity configuration

#### [config_flow.py](custom_components/hellowatt/config_flow.py)
Configuration flow:
- User-friendly setup via UI
- Username and password collection
- Unique ID based on username to prevent duplicates

#### [const.py](custom_components/hellowatt/const.py)
Constants and configuration:
- Domain definition
- API URL
- Logger configuration

## API Integration

The integration communicates with the HelloWatt API:
- Base URL: `https://www.hellowatt.fr/api`
- Authentication: Cookie-based session with CSRF tokens
- Endpoints used:
  - `/homes` - List available homes/PDLs
  - `/homes/{home_id}/sge_measures/conso_daily` - Electricity consumption
  - `/homes/{home_id}/adict_measures/conso_daily` - Gas consumption
  - `/homes/{home_id}/temperature_measures/yearly` - Temperature data
  - `/homes/{home_id}/contracts` - Contract information

## Troubleshooting

### Sensors showing "Unavailable"
- Check that your HelloWatt account has active energy contracts
- Verify that data is available for your PDL on the HelloWatt website
- Check Home Assistant logs for authentication errors

### Missing peak/off-peak sensors
- These sensors only appear for dual-rate (HP/HC) electricity contracts
- Base rate contracts will only show the total consumption sensor

### Gas sensors not appearing
- Gas sensors only appear if you have an active gas contract
- The integration gracefully handles missing gas data

### Historical import service fails
- Ensure end_date is at least 2 days in the past (API limitation)
- Check that you have sufficient data available on HelloWatt's website
- Review logs for specific API errors

## Development

### File Structure
```
custom_components/hellowatt/
├── __init__.py           # Integration setup and services
├── client.py             # API client
├── config_flow.py        # Configuration UI
├── const.py              # Constants
├── coordinator.py        # Data update coordinator
├── manifest.json         # Integration metadata
├── sensor.py             # Sensor entities
├── services.yaml         # Service definitions
└── strings.json          # UI strings
```

### Key Design Patterns
- **CoordinatorEntity**: Efficient state management and updates
- **Async/Await**: Non-blocking API calls
- **Session Management**: Automatic re-authentication on expiry
- **Multi-home Support**: Separate coordinator per PDL
- **External Statistics**: Long-term historical data storage

## Contributing

Contributions are welcome. Please ensure:
- Code follows Home Assistant coding standards
- All sensors have proper device classes and units
- Changes are tested with real HelloWatt accounts
- Documentation is updated

## License

This integration is provided as-is. Please check the LICENSE file for details.

## Credits

Developed for use with the HelloWatt energy monitoring service (https://www.hellowatt.fr/).

## Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by HelloWatt. Use at your own risk.
