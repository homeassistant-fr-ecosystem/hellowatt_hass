"""Tests for HelloWatt constants."""

from custom_components.hellowatt.const import (
    API_URL,
    CONF_REFRESH_INTERVAL,
    DEFAULT_NAME,
    DOMAIN,
    LOGGER,
)


def test_domain():
    """Test domain constant."""
    assert DOMAIN == "hellowatt"


def test_default_name():
    """Test default name constant."""
    assert DEFAULT_NAME == "HelloWatt"


def test_api_url():
    """Test API URL constant."""
    assert API_URL == "https://www.hellowatt.fr/api"


def test_conf_refresh_interval():
    """Test refresh interval config constant."""
    assert CONF_REFRESH_INTERVAL == "refresh_interval"


def test_logger_exists():
    """Test logger is properly initialized."""
    assert LOGGER is not None
    assert LOGGER.name == "custom_components.hellowatt"
