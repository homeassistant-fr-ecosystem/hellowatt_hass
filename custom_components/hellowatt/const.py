"""Constants for the HelloWatt integration."""

from logging import Logger, getLogger

# Logger instance for the integration
LOGGER: Logger = getLogger(__package__)

# Integration domain identifier
DOMAIN: str = "hellowatt"

# Default name for the integration
DEFAULT_NAME: str = "HelloWatt"

# Configuration option keys
CONF_REFRESH_INTERVAL: str = "refresh_interval"

# HelloWatt API base URL
API_URL: str = "https://www.hellowatt.fr/api"

# ==============================================================================
# Data Refresh and Update Settings
# ==============================================================================

# Default update interval in hours (how often to fetch new data)
DEFAULT_UPDATE_INTERVAL_HOURS: int = 1

# Lookback period in days (how far back to fetch historical data)
DEFAULT_LOOKBACK_DAYS: int = 7

# Temperature data lookback in days (yearly temperature data)
DEFAULT_TEMPERATURE_LOOKBACK_DAYS: int = 365

# Data availability offset (API typically has data up to D-2)
DATA_AVAILABILITY_OFFSET_DAYS: int = 2
