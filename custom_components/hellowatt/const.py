"""Constants for the HelloWatt integration."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "hellowatt"
DEFAULT_NAME = "HelloWatt"
CONF_REFRESH_INTERVAL = "refresh_interval"
API_URL = "https://www.hellowatt.fr/api"