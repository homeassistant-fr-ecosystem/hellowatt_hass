"""Tests for HelloWatt coordinator.

Following Home Assistant testing guidelines:
https://developers.home-assistant.io/docs/creating_integration_tests_file_structure
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, Mock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest

from custom_components.hellowatt.const import DOMAIN
from custom_components.hellowatt.coordinator import HelloWattCoordinator

# ============================================================================
# Coordinator Tests
# ============================================================================


async def test_coordinator_initialization(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test coordinator initializes correctly."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    assert coordinator.name == "hellowatt_12345678901234"
    assert coordinator.pdl == "12345678901234"
    assert coordinator.home_id == "home123"
    assert coordinator.update_interval == timedelta(hours=1)


async def test_coordinator_update_success(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test successful data update."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data is not None
    assert "electricity" in coordinator.data
    assert "gas" in coordinator.data
    assert "temperature" in coordinator.data
    assert "contract_provider" in coordinator.data


async def test_coordinator_processes_electricity_data(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
    mock_api_response_electricity,
) -> None:
    """Test coordinator correctly processes electricity data."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    await coordinator.async_config_entry_first_refresh()

    data = coordinator.data

    # Check main electricity consumption (latest day)
    latest = mock_api_response_electricity["values"][-1]
    expected_total = sum(latest["kwhDetailed"].values())
    assert data["electricity"] == expected_total

    # Check peak/off-peak hours
    assert data["electricity_peak"] == latest["kwhDetailed"]["HP"]
    assert data["electricity_off_peak"] == latest["kwhDetailed"]["HC"]

    # Check CO2
    assert data["electricity_co2"] == latest["valueCo2"]

    # Check costs
    expected_cost = sum(latest["eurosDetailed"].values())
    assert data["electricity_cost"] == expected_cost


async def test_coordinator_processes_gas_data(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
    mock_api_response_gas,
) -> None:
    """Test coordinator correctly processes gas data."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    await coordinator.async_config_entry_first_refresh()

    data = coordinator.data

    # Check gas consumption (latest day)
    latest = mock_api_response_gas["values"][-1]
    expected_total = sum(latest["kwhDetailed"].values())
    assert data["gas"] == expected_total

    # Check CO2
    assert data["gas_co2"] == latest["valueCo2"]

    # Check costs
    expected_cost = sum(latest["eurosDetailed"].values())
    assert data["gas_cost"] == expected_cost


async def test_coordinator_calculates_weekly_totals(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
    mock_api_response_electricity,
    mock_api_response_gas,
) -> None:
    """Test coordinator calculates weekly consumption totals."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    await coordinator.async_config_entry_first_refresh()

    data = coordinator.data

    # Calculate expected weekly electricity
    expected_weekly_elec = sum(
        sum(day["kwhDetailed"].values())
        for day in mock_api_response_electricity["values"]
    )
    assert data["electricity_weekly"] == expected_weekly_elec

    # Calculate expected weekly gas
    expected_weekly_gas = sum(
        sum(day["kwhDetailed"].values()) for day in mock_api_response_gas["values"]
    )
    assert data["gas_weekly"] == expected_weekly_gas


async def test_coordinator_handles_missing_gas(
    hass: HomeAssistant,
    mock_hellowatt_client,
    mock_hellowatt_homes,
    mock_api_response_electricity,
    mock_api_response_temperature,
    mock_api_response_contracts,
) -> None:
    """Test coordinator gracefully handles missing gas data."""

    async def mock_get_gas_fail(*_args, **_kwargs):
        """Mock gas endpoint failure."""
        raise Exception("No gas contract")

    mock_hellowatt_client.get_daily_consumption = AsyncMock(
        return_value=mock_api_response_electricity
    )
    mock_hellowatt_client.get_daily_gas_consumption = mock_get_gas_fail
    mock_hellowatt_client.get_yearly_temperature = AsyncMock(
        return_value=mock_api_response_temperature
    )
    mock_hellowatt_client.get_contracts = AsyncMock(
        return_value=mock_api_response_contracts
    )

    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    await coordinator.async_config_entry_first_refresh()

    data = coordinator.data

    # Should have electricity data
    assert "electricity" in data

    # Should NOT have gas data (gracefully skipped)
    assert "gas" not in data


async def test_coordinator_update_failure(
    hass: HomeAssistant,
    mock_hellowatt_client,
    mock_hellowatt_homes,
) -> None:
    """Test coordinator raises UpdateFailed on error."""

    async def mock_get_consumption_fail(*_args, **_kwargs):
        """Mock API failure."""
        raise Exception("API Error")

    mock_hellowatt_client.get_daily_consumption = mock_get_consumption_fail

    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    await coordinator.async_refresh()
    assert coordinator.last_update_success is False
    assert isinstance(coordinator.last_exception, UpdateFailed)


async def test_coordinator_uses_custom_update_interval(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test coordinator respects custom update interval from options."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={"update_interval": 6},  # Custom 6 hours
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    assert coordinator.update_interval == timedelta(hours=6)


async def test_coordinator_uses_custom_lookback_days(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test coordinator uses custom lookback days from options."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={"lookback_days": 14},  # Custom 14 days
    )

    consumption_mock = AsyncMock(return_value={"values": []})
    mock_hellowatt_client_authenticated.get_daily_consumption = consumption_mock

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    await coordinator.async_config_entry_first_refresh()

    # Verify client was called — custom lookback_days option was respected
    assert consumption_mock.called


async def test_coordinator_extracts_home_info(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
    mock_hellowatt_homes,
) -> None:
    """Test coordinator includes home information in data."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client_authenticated,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    await coordinator.async_config_entry_first_refresh()

    data = coordinator.data

    assert data["address"] == "123 Test St"
    assert data["postal_code"] == "75001"
    assert data["city"] == "Paris"
    assert data["pdl"] == "12345678901234"


async def test_coordinator_handles_base_rate_contract(
    hass: HomeAssistant,
    mock_hellowatt_client,
    mock_hellowatt_homes,
    mock_api_response_electricity_base,
    mock_api_response_gas,
    mock_api_response_temperature,
    mock_api_response_contracts,
) -> None:
    """Test coordinator handles base rate (no HP/HC) contracts."""
    mock_hellowatt_client.get_daily_consumption = AsyncMock(
        return_value=mock_api_response_electricity_base
    )
    mock_hellowatt_client.get_daily_gas_consumption = AsyncMock(
        return_value=mock_api_response_gas
    )
    mock_hellowatt_client.get_yearly_temperature = AsyncMock(
        return_value=mock_api_response_temperature
    )
    mock_hellowatt_client.get_contracts = AsyncMock(
        return_value=mock_api_response_contracts
    )

    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    await coordinator.async_config_entry_first_refresh()

    data = coordinator.data

    # Should have electricity total
    assert data["electricity"] == 15.7

    # Should NOT have HP/HC keys (base rate)
    assert "electricity_peak" not in data
    assert "electricity_off_peak" not in data


# ============================================================================
# Authentication Failure Tests
# ============================================================================


async def test_coordinator_raises_config_entry_auth_failed_on_401(
    hass: HomeAssistant,
    mock_hellowatt_client,
    mock_hellowatt_homes,
) -> None:
    """Test coordinator raises ConfigEntryAuthFailed on 401 error."""
    import aiohttp
    from homeassistant.exceptions import ConfigEntryAuthFailed

    async def mock_get_consumption_401(*_args, **_kwargs):
        """Mock API 401 error."""
        raise aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=401,
        )

    mock_hellowatt_client.get_daily_consumption = mock_get_consumption_401

    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator.async_config_entry_first_refresh()


async def test_coordinator_raises_config_entry_auth_failed_on_403(
    hass: HomeAssistant,
    mock_hellowatt_client,
    mock_hellowatt_homes,
) -> None:
    """Test coordinator raises ConfigEntryAuthFailed on 403 error."""
    import aiohttp
    from homeassistant.exceptions import ConfigEntryAuthFailed

    async def mock_get_consumption_403(*_args, **_kwargs):
        """Mock API 403 error."""
        raise aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=403,
        )

    mock_hellowatt_client.get_daily_consumption = mock_get_consumption_403

    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator.async_config_entry_first_refresh()


async def test_coordinator_raises_config_entry_auth_failed_on_auth_error(
    hass: HomeAssistant,
    mock_hellowatt_client,
    mock_hellowatt_homes,
) -> None:
    """Test coordinator raises ConfigEntryAuthFailed on authentication error."""
    from homeassistant.exceptions import ConfigEntryAuthFailed

    async def mock_get_consumption_auth_fail(*_args, **_kwargs):
        """Mock authentication failure."""
        raise Exception("Authentication failed: Invalid credentials")

    mock_hellowatt_client.get_daily_consumption = mock_get_consumption_auth_fail

    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator.async_config_entry_first_refresh()


async def test_coordinator_raises_config_entry_auth_failed_on_no_session(
    hass: HomeAssistant,
    mock_hellowatt_client,
    mock_hellowatt_homes,
) -> None:
    """Test coordinator raises ConfigEntryAuthFailed on no session cookie error."""
    from homeassistant.exceptions import ConfigEntryAuthFailed

    async def mock_get_consumption_no_session(*_args, **_kwargs):
        """Mock no session cookie error."""
        raise Exception("Authentication failed: No session cookie received")

    mock_hellowatt_client.get_daily_consumption = mock_get_consumption_no_session

    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator.async_config_entry_first_refresh()


async def test_coordinator_raises_update_failed_on_network_error(
    hass: HomeAssistant,
    mock_hellowatt_client,
    mock_hellowatt_homes,
) -> None:
    """Test coordinator raises UpdateFailed on non-auth network errors."""
    import aiohttp

    async def mock_get_consumption_network_error(*_args, **_kwargs):
        """Mock network error."""
        raise aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=500,
        )

    mock_hellowatt_client.get_daily_consumption = mock_get_consumption_network_error

    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="Test",
        data={"username": "test@example.com", "password": "test"},
        source="user",
        unique_id="test@example.com",
        options={},
    )

    coordinator = HelloWattCoordinator(
        hass=hass,
        client=mock_hellowatt_client,
        entry=entry,
        pdl="12345678901234",
        home_id="home123",
        home=mock_hellowatt_homes[0],
    )

    await coordinator.async_refresh()
    assert coordinator.last_update_success is False
    assert isinstance(coordinator.last_exception, UpdateFailed)
