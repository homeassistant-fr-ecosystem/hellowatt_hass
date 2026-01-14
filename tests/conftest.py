"""Pytest fixtures for HelloWatt tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import aiohttp
import pytest


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession."""
    session = Mock(spec=aiohttp.ClientSession)
    session.cookie_jar = Mock()
    session.cookie_jar.__iter__ = Mock(return_value=iter([]))
    return session


@pytest.fixture
def mock_hellowatt_client(mock_aiohttp_session):
    """Mock HelloWatt API client."""
    from custom_components.hellowatt.client import HelloWattApiClient

    client = HelloWattApiClient(
        session=mock_aiohttp_session,
        username="test@example.com",
        password="test_password",
    )
    client._homes = [
        {
            "id": "home123",
            "address": "123 Test St",
            "area": {"postalCode": "75001", "name": "Paris"},
            "enedisHome": {"pdl": "12345678901234"},
        }
    ]
    return client


@pytest.fixture
def mock_api_response_electricity() -> dict[str, Any]:
    """Mock electricity consumption API response."""
    return {
        "values": [
            {
                "datetime": "2024-01-01T00:00:00Z",
                "kwhDetailed": {"HP": 10.5, "HC": 5.2},
                "eurosDetailed": {"consumption": 2.5, "subscription": 0.5},
                "valueCo2": 1.2,
            },
            {
                "datetime": "2024-01-02T00:00:00Z",
                "kwhDetailed": {"HP": 12.0, "HC": 6.0},
                "eurosDetailed": {"consumption": 3.0, "subscription": 0.5},
                "valueCo2": 1.5,
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
            }
        ]
    }


@pytest.fixture
def mock_api_response_temperature() -> dict[str, Any]:
    """Mock temperature API response."""
    return {"values": [{"datetime": "2024-01-01T00:00:00Z", "valueCelsius": 15.5}]}


@pytest.fixture
def mock_api_response_contracts() -> list[dict[str, Any]]:
    """Mock contracts API response."""
    return [
        {
            "contractState": "actual",
            "provider": {"name": "Test Provider"},
            "offer": {"name": "Test Offer"},
        }
    ]
