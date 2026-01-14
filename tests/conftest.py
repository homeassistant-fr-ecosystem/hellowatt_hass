"""Pytest fixtures for HelloWatt tests.

This module provides fixtures following Home Assistant testing best practices.
See: https://developers.home-assistant.io/docs/creating_integration_tests_file_structure
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant

from custom_components.hellowatt.const import DOMAIN

# Import pytest plugins from Home Assistant
pytest_plugins = "pytest_homeassistant_custom_component"


# ============================================================================
# Home Assistant Core Fixtures
# ============================================================================


@pytest.fixture
def mock_config_entry() -> dict[str, Any]:
    """Mock config entry data."""
    return {
        "username": "test@example.com",
        "password": "test_password",
    }


@pytest.fixture
def mock_options() -> dict[str, Any]:
    """Mock options data."""
    return {
        "update_interval": 1,
        "lookback_days": 7,
    }


# ============================================================================
# API Client Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession."""
    session = Mock(spec=aiohttp.ClientSession)
    session.cookie_jar = Mock()

    # Mock cookie jar with CSRF token
    csrf_cookie = Mock()
    csrf_cookie.key = "csrftoken"
    csrf_cookie.value = "test_csrf_token"

    session_cookie = Mock()
    session_cookie.key = "sessionid"
    session_cookie.value = "test_session_id"

    session.cookie_jar.__iter__ = Mock(return_value=iter([csrf_cookie, session_cookie]))

    return session


@pytest.fixture
def mock_hellowatt_homes() -> list[dict[str, Any]]:
    """Mock HelloWatt homes/PDL data."""
    return [
        {
            "id": "home123",
            "address": "123 Test St",
            "area": {"postalCode": "75001", "name": "Paris"},
            "enedisHome": {"pdl": "12345678901234"},
        },
        {
            "id": "home456",
            "address": "456 Test Ave",
            "area": {"postalCode": "69001", "name": "Lyon"},
            "enedisHome": {"pdl": "98765432109876"},
        },
    ]


@pytest.fixture
def mock_api_response_electricity() -> dict[str, Any]:
    """Mock electricity consumption API response."""
    return {
        "values": [
            {
                "datetime": "2024-01-01T00:00:00Z",
                "kwhDetailed": {"HP": 10.5, "HC": 5.2},
                "eurosDetailed": {"HP": 1.8, "HC": 0.7, "subscription": 0.5},
                "valueCo2": 1.2,
            },
            {
                "datetime": "2024-01-02T00:00:00Z",
                "kwhDetailed": {"HP": 12.0, "HC": 6.0},
                "eurosDetailed": {"HP": 2.0, "HC": 0.8, "subscription": 0.5},
                "valueCo2": 1.5,
            },
            {
                "datetime": "2024-01-03T00:00:00Z",
                "kwhDetailed": {"HP": 11.0, "HC": 5.5},
                "eurosDetailed": {"HP": 1.9, "HC": 0.75, "subscription": 0.5},
                "valueCo2": 1.3,
            },
        ]
    }


@pytest.fixture
def mock_api_response_electricity_base() -> dict[str, Any]:
    """Mock electricity consumption for base rate contract."""
    return {
        "values": [
            {
                "datetime": "2024-01-01T00:00:00Z",
                "kwhDetailed": {"base": 15.7},
                "eurosDetailed": {"consumption": 2.5, "subscription": 0.5},
                "valueCo2": 1.2,
            },
        ]
    }


@pytest.fixture
def mock_api_response_gas() -> dict[str, Any]:
    """Mock gas consumption API response."""
    return {
        "values": [
            {
                "datetime": "2024-01-01T00:00:00Z",
                "kwhDetailed": {"total": 25.0},
                "eurosDetailed": {"consumption": 5.0, "subscription": 0.8},
                "valueCo2": 2.5,
            },
            {
                "datetime": "2024-01-02T00:00:00Z",
                "kwhDetailed": {"total": 28.0},
                "eurosDetailed": {"consumption": 5.6, "subscription": 0.8},
                "valueCo2": 2.8,
            },
        ]
    }


@pytest.fixture
def mock_api_response_temperature() -> dict[str, Any]:
    """Mock temperature API response."""
    return {
        "values": [
            {"datetime": "2024-01-01T00:00:00Z", "valueCelsius": 15.5},
            {"datetime": "2024-01-02T00:00:00Z", "valueCelsius": 16.2},
        ]
    }


@pytest.fixture
def mock_api_response_contracts() -> list[dict[str, Any]]:
    """Mock contracts API response."""
    return [
        {
            "contractState": "actual",
            "provider": {"name": "EDF"},
            "offer": {"name": "Tarif Bleu"},
        }
    ]


@pytest.fixture
def mock_hellowatt_client(
    mock_aiohttp_session,
    mock_hellowatt_homes,
):
    """Mock HelloWatt API client with authenticated state."""
    from custom_components.hellowatt.client import HelloWattApiClient

    client = HelloWattApiClient(
        session=mock_aiohttp_session,
        username="test@example.com",
        password="test_password",
    )
    client._homes = mock_hellowatt_homes
    return client


@pytest.fixture
def mock_hellowatt_client_authenticated(
    mock_hellowatt_client,
    mock_api_response_electricity,
    mock_api_response_gas,
    mock_api_response_temperature,
    mock_api_response_contracts,
):
    """Mock fully authenticated client with all API methods mocked."""

    async def mock_authenticate():
        """Mock authenticate method."""
        pass

    async def mock_get_daily_consumption(*args, **kwargs):
        """Mock electricity consumption."""
        return mock_api_response_electricity

    async def mock_get_daily_gas_consumption(*args, **kwargs):
        """Mock gas consumption."""
        return mock_api_response_gas

    async def mock_get_yearly_temperature(*args, **kwargs):
        """Mock temperature."""
        return mock_api_response_temperature

    async def mock_get_contracts(*args, **kwargs):
        """Mock contracts."""
        return mock_api_response_contracts

    async def mock_get_homes(*args, **kwargs):
        """Mock homes list."""
        return mock_hellowatt_client._homes

    mock_hellowatt_client.authenticate = mock_authenticate
    mock_hellowatt_client.get_daily_consumption = mock_get_daily_consumption
    mock_hellowatt_client.get_daily_gas_consumption = mock_get_daily_gas_consumption
    mock_hellowatt_client.get_yearly_temperature = mock_get_yearly_temperature
    mock_hellowatt_client.get_contracts = mock_get_contracts
    mock_hellowatt_client.get_homes = mock_get_homes

    return mock_hellowatt_client


# ============================================================================
# Coordinator Fixtures
# ============================================================================


@pytest.fixture
def mock_coordinator_data() -> dict[str, Any]:
    """Mock coordinator data structure."""
    return {
        "electricity": 15.7,
        "electricity_peak": 10.5,
        "electricity_off_peak": 5.2,
        "electricity_yesterday": 14.8,
        "electricity_weekly": 110.5,
        "electricity_co2": 1.2,
        "electricity_cost": 3.0,
        "electricity_cost_consumption": 2.5,
        "electricity_cost_subscription": 0.5,
        "gas": 25.0,
        "gas_yesterday": 24.0,
        "gas_weekly": 175.0,
        "gas_co2": 2.5,
        "gas_cost": 5.8,
        "gas_cost_consumption": 5.0,
        "gas_cost_subscription": 0.8,
        "temperature": 15.5,
        "contract_provider": "EDF",
        "contract_offer": "Tarif Bleu",
        "address": "123 Test St",
        "postal_code": "75001",
        "city": "Paris",
        "pdl": "12345678901234",
    }


# ============================================================================
# Integration Setup Fixtures
# ============================================================================


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    mock_config_entry,
) -> Generator[None, None, None]:
    """Set up the HelloWatt integration for testing."""
    from homeassistant.setup import async_setup_component

    # Mock the client creation
    with patch(
        "custom_components.hellowatt.HelloWattApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.homes = [
            {
                "id": "home123",
                "address": "123 Test St",
                "area": {"postalCode": "75001", "name": "Paris"},
                "enedisHome": {"pdl": "12345678901234"},
            }
        ]
        mock_client.authenticate = AsyncMock()
        mock_client.get_daily_consumption = AsyncMock(
            return_value={"values": [{"datetime": "2024-01-01T00:00:00Z", "kwhDetailed": {"HP": 10, "HC": 5}, "valueCo2": 1.0, "eurosDetailed": {"HP": 1.5, "HC": 0.5, "subscription": 0.3}}]}
        )
        mock_client.get_daily_gas_consumption = AsyncMock(
            return_value={"values": [{"datetime": "2024-01-01T00:00:00Z", "kwhDetailed": {"total": 20}, "valueCo2": 2.0, "eurosDetailed": {"consumption": 4.0, "subscription": 0.5}}]}
        )
        mock_client.get_yearly_temperature = AsyncMock(
            return_value={"values": [{"datetime": "2024-01-01T00:00:00Z", "valueCelsius": 15}]}
        )
        mock_client.get_contracts = AsyncMock(
            return_value=[{"contractState": "actual", "provider": {"name": "EDF"}, "offer": {"name": "Tarif Bleu"}}]
        )

        mock_client_class.return_value = mock_client

        # Setup component
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        yield

        # Cleanup
        await hass.async_stop()


# ============================================================================
# Mock Response Helpers
# ============================================================================


@pytest.fixture
def mock_aiohttp_response():
    """Create a mock aiohttp response."""

    def _create_response(status: int = 200, json_data: Any = None, text: str = ""):
        """Create a mock response with given parameters."""
        response = AsyncMock()
        response.status = status
        response.headers = {}

        if json_data is not None:
            response.json = AsyncMock(return_value=json_data)

        response.text = AsyncMock(return_value=text)
        response.raise_for_status = Mock()

        return response

    return _create_response
