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