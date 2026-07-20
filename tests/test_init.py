"""Tests for HelloWatt integration setup.

Following Home Assistant testing guidelines:
https://developers.home-assistant.io/docs/creating_integration_tests_file_structure
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import integration_platform # Import for async_unload_platforms
from homeassistant.helpers.aiohttp_client import async_create_clientsession # Import the function being patched
import pytest

from custom_components.hellowatt import (
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.hellowatt import PLATFORMS
from custom_components.hellowatt.client import HelloWattApiClient # Import for Mock(spec=...)
from custom_components.hellowatt.const import DOMAIN

# ============================================================================
# Integration Setup Tests
# ============================================================================


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_setup_entry_success(
    hass: HomeAssistant,
    mock_aiohttp_session,
    mock_hellowatt_homes,
) -> None:
    """Test successful integration setup."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        unique_id="test@example.com",
        options={},
    )

    mock_client = Mock(spec=HelloWattApiClient)
    mock_client._session = mock_aiohttp_session
    mock_client.authenticate = AsyncMock()
    mock_client.get_homes = AsyncMock(return_value=mock_hellowatt_homes)
    mock_client.get_daily_consumption = AsyncMock(return_value={}) # Default mock
    mock_client.get_daily_gas_consumption = AsyncMock(return_value={}) # Default mock
    mock_client.get_yearly_temperature = AsyncMock(return_value={}) # Default mock
    mock_client.get_contracts = AsyncMock(return_value=[]) # Default mock


    with (
        patch("homeassistant.helpers.aiohttp_client.async_create_clientsession", return_value=mock_aiohttp_session),
        patch("custom_components.hellowatt.client.HelloWattApiClient") as mock_client_class,
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups") as mock_forward_setups,
    ):
        mock_client_class.return_value = mock_client
        mock_forward_setups.return_value = None

        result = await async_setup_entry(hass, entry)

        assert result is True
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]
        assert "client" in hass.data[DOMAIN][entry.entry_id]
        assert "coordinators" in hass.data[DOMAIN][entry.entry_id]

        mock_client_class.assert_called_once_with(
            session=mock_aiohttp_session,
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )
        mock_client.authenticate.assert_called_once()
        mock_forward_setups.assert_called_once_with(hass, entry, PLATFORMS)


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_setup_entry_creates_coordinators(
    hass: HomeAssistant,
    mock_aiohttp_session,
    mock_hellowatt_homes,
) -> None:
    """Test setup creates coordinators for each PDL."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        unique_id="test@example.com",
        options={},
    )

    mock_client = Mock(spec=HelloWattApiClient)
    mock_client._session = mock_aiohttp_session
    mock_client.authenticate = AsyncMock()
    mock_client.get_homes = AsyncMock(return_value=mock_hellowatt_homes)
    mock_client.get_daily_consumption = AsyncMock(return_value={})
    mock_client.get_daily_gas_consumption = AsyncMock(return_value={})
    mock_client.get_yearly_temperature = AsyncMock(return_value={})
    mock_client.get_contracts = AsyncMock(return_value=[])


    with (
        patch("homeassistant.helpers.aiohttp_client.async_create_clientsession", return_value=mock_aiohttp_session),
        patch("custom_components.hellowatt.client.HelloWattApiClient") as mock_client_class,
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups") as mock_forward_setups,
        patch(
            "custom_components.hellowatt.coordinator.HelloWattCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_client_class.return_value = mock_client
        mock_forward_setups.return_value = None

        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        await async_setup_entry(hass, entry)

        assert mock_coordinator_class.call_count == len(mock_hellowatt_homes)
        mock_forward_setups.assert_called_once_with(hass, entry, PLATFORMS)


async def test_async_setup_entry_auth_failure(
    hass: HomeAssistant,
    mock_aiohttp_session,
) -> None:
    """Test setup fails gracefully on authentication error."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "wrong_password",
        },
        source="user",
        unique_id="test@example.com",
        options={},
    )

    mock_client = Mock(spec=HelloWattApiClient)
    mock_client._session = mock_aiohttp_session
    mock_client.authenticate = AsyncMock(side_effect=Exception("Authentication failed"))


    with (
        patch("homeassistant.helpers.aiohttp_client.async_create_clientsession", return_value=mock_aiohttp_session),
        patch("custom_components.hellowatt.client.HelloWattApiClient") as mock_client_class,
    ):
        mock_client_class.return_value = mock_client

        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, entry)

        mock_client_class.assert_called_once_with(
            session=mock_aiohttp_session,
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )
        mock_client.authenticate.assert_called_once()


async def test_async_setup_entry_no_session_cookie(
    hass: HomeAssistant,
    mock_aiohttp_session,
) -> None:
    """Test setup fails when no session cookie is received."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        unique_id="test@example.com",
        options={},
    )

    mock_client = Mock(spec=HelloWattApiClient)
    mock_client._session = mock_aiohttp_session
    mock_client.authenticate = AsyncMock(side_effect=Exception("No session cookie received"))


    with (
        patch("homeassistant.helpers.aiohttp_client.async_create_clientsession", return_value=mock_aiohttp_session),
        patch("custom_components.hellowatt.client.HelloWattApiClient") as mock_client_class,
    ):
        mock_client_class.return_value = mock_client

        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, entry)

        mock_client_class.assert_called_once_with(
            session=mock_aiohttp_session,
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )
        mock_client.authenticate.assert_called_once()


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_setup_entry_registers_services(
    hass: HomeAssistant,
    mock_aiohttp_session,
    mock_hellowatt_homes,
) -> None:
    """Test setup registers integration services."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        unique_id="test@example.com",
        options={},
    )

    mock_client = Mock(spec=HelloWattApiClient)
    mock_client._session = mock_aiohttp_session
    mock_client.authenticate = AsyncMock()
    mock_client.get_homes = AsyncMock(return_value=mock_hellowatt_homes)
    mock_client.get_daily_consumption = AsyncMock(return_value={})
    mock_client.get_daily_gas_consumption = AsyncMock(return_value={})
    mock_client.get_yearly_temperature = AsyncMock(return_value={})
    mock_client.get_contracts = AsyncMock(return_value=[])


    with (
        patch("homeassistant.helpers.aiohttp_client.async_create_clientsession", return_value=mock_aiohttp_session),
        patch("custom_components.hellowatt.client.HelloWattApiClient") as mock_client_class,
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups") as mock_forward_setups,
        patch(
            "custom_components.hellowatt.coordinator.HelloWattCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_client_class.return_value = mock_client
        mock_forward_setups.return_value = None

        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        await async_setup_entry(hass, entry)

        assert hass.services.has_service(DOMAIN, "import_historical_data")
        assert hass.services.has_service(DOMAIN, "clear_statistics")
        mock_client_class.assert_called_once_with(
            session=mock_aiohttp_session,
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )
        mock_client.authenticate.assert_called_once()
        mock_forward_setups.assert_called_once_with(hass, entry, PLATFORMS)


# ============================================================================
# Integration Unload Tests
# ============================================================================


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_unload_entry_success(
    hass: HomeAssistant,
    mock_aiohttp_session,
    mock_hellowatt_homes,
) -> None:
    """Test successful integration unload."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        unique_id="test@example.com",
        options={},
    )

    mock_client = Mock(spec=HelloWattApiClient)
    mock_client._session = mock_aiohttp_session
    mock_client.authenticate = AsyncMock()
    mock_client.get_homes = AsyncMock(return_value=mock_hellowatt_homes)
    mock_client.get_daily_consumption = AsyncMock(return_value={})
    mock_client.get_daily_gas_consumption = AsyncMock(return_value={})
    mock_client.get_yearly_temperature = AsyncMock(return_value={})
    mock_client.get_contracts = AsyncMock(return_value=[])


    with (
        patch("homeassistant.helpers.aiohttp_client.async_create_clientsession", return_value=mock_aiohttp_session),
        patch("custom_components.hellowatt.client.HelloWattApiClient") as mock_client_class,
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups") as mock_forward_setups,
        patch(
            "custom_components.hellowatt.coordinator.HelloWattCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_client_class.return_value = mock_client
        mock_forward_setups.return_value = None

        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        await async_setup_entry(hass, entry)

    with patch("homeassistant.helpers.integration_platform.async_unload_platforms", return_value=True) as mock_unload_platforms:
        result = await async_unload_entry(hass, entry)

        assert result is True
        assert entry.entry_id not in hass.data[DOMAIN]
        mock_unload_platforms.assert_called_once_with(hass, entry)


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_unload_entry_removes_services_when_last_entry(
    hass: HomeAssistant,
    mock_aiohttp_session,
    mock_hellowatt_homes,
) -> None:
    """Test unload removes services when it's the last entry."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        unique_id="test@example.com",
        options={},
    )

    mock_client = Mock(spec=HelloWattApiClient)
    mock_client._session = mock_aiohttp_session
    mock_client.authenticate = AsyncMock()
    mock_client.get_homes = AsyncMock(return_value=mock_hellowatt_homes)
    mock_client.get_daily_consumption = AsyncMock(return_value={})
    mock_client.get_daily_gas_consumption = AsyncMock(return_value={})
    mock_client.get_yearly_temperature = AsyncMock(return_value={})
    mock_client.get_contracts = AsyncMock(return_value=[])

    with (
        patch("homeassistant.helpers.aiohttp_client.async_create_clientsession", return_value=mock_aiohttp_session),
        patch("custom_components.hellowatt.client.HelloWattApiClient") as mock_client_class,
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups") as mock_forward_setups,
        patch(
            "custom_components.hellowatt.coordinator.HelloWattCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_client_class.return_value = mock_client
        mock_forward_setups.return_value = None

        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        await async_setup_entry(hass, entry)

    assert hass.services.has_service(DOMAIN, "import_historical_data")

    with patch("homeassistant.helpers.integration_platform.async_unload_platforms", return_value=True) as mock_unload_platforms:
        await async_unload_entry(hass, entry)

    assert not hass.services.has_service(DOMAIN, "import_historical_data")
    assert not hass.services.has_service(DOMAIN, "clear_statistics")
    mock_unload_platforms.assert_called_once_with(hass, entry)


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_unload_entry_keeps_services_when_other_entries_exist(
    hass: HomeAssistant,
    mock_aiohttp_session,
    mock_hellowatt_homes,
) -> None:
    """Test unload keeps services when other entries still exist."""
    entry1 = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test1@example.com)",
        data={
            CONF_USERNAME: "test1@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        unique_id="test1@example.example",
        options={},
    )

    entry2 = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test2@example.com)",
        data={
            CONF_USERNAME: "test2@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        unique_id="test2@example.example",
        options={},
    )

    mock_client_entry1 = Mock(spec=HelloWattApiClient)
    mock_client_entry1._session = mock_aiohttp_session
    mock_client_entry1.authenticate = AsyncMock()
    mock_client_entry1.get_homes = AsyncMock(return_value=mock_hellowatt_homes)
    mock_client_entry1.get_daily_consumption = AsyncMock(return_value={})
    mock_client_entry1.get_daily_gas_consumption = AsyncMock(return_value={})
    mock_client_entry1.get_yearly_temperature = AsyncMock(return_value={})
    mock_client_entry1.get_contracts = AsyncMock(return_value=[])

    mock_client_entry2 = Mock(spec=HelloWattApiClient)
    mock_client_entry2._session = mock_aiohttp_session
    mock_client_entry2.authenticate = AsyncMock()
    mock_client_entry2.get_homes = AsyncMock(return_value=mock_hellowatt_homes)
    mock_client_entry2.get_daily_consumption = AsyncMock(return_value={})
    mock_client_entry2.get_daily_gas_consumption = AsyncMock(return_value={})
    mock_client_entry2.get_yearly_temperature = AsyncMock(return_value={})
    mock_client_entry2.get_contracts = AsyncMock(return_value=[])


    with (
        patch("homeassistant.helpers.aiohttp_client.async_create_clientsession", return_value=mock_aiohttp_session),
        patch("custom_components.hellowatt.client.HelloWattApiClient") as mock_client_class,
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups") as mock_forward_setups,
        patch(
            "custom_components.hellowatt.coordinator.HelloWattCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_client_class.side_effect = [mock_client_entry1, mock_client_entry2] # For multiple setups
        mock_forward_setups.return_value = None

        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        await async_setup_entry(hass, entry1)
        await async_setup_entry(hass, entry2)

    with patch("homeassistant.helpers.integration_platform.async_unload_platforms", return_value=True) as mock_unload_platforms:
        await async_unload_entry(hass, entry1)

    assert hass.services.has_service(DOMAIN, "import_historical_data")
    assert hass.services.has_service(DOMAIN, "clear_statistics")
    mock_unload_platforms.assert_called_once_with(hass, entry1)


# ============================================================================
# Integration Reload Tests
# ============================================================================


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_reload_entry(
    hass: HomeAssistant,
    mock_aiohttp_session,
    mock_hellowatt_homes,
) -> None:
    """Test entry reload."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        unique_id="test@example.com",
        options={},
    )

    hass.config_entries._entries[entry.entry_id] = entry

    mock_client = Mock(spec=HelloWattApiClient)
    mock_client._session = mock_aiohttp_session
    mock_client.authenticate = AsyncMock()
    mock_client.get_homes = AsyncMock(return_value=mock_hellowatt_homes)
    mock_client.get_daily_consumption = AsyncMock(return_value={})
    mock_client.get_daily_gas_consumption = AsyncMock(return_value={})
    mock_client.get_yearly_temperature = AsyncMock(return_value={})
    mock_client.get_contracts = AsyncMock(return_value=[])

    with (
        patch("homeassistant.helpers.aiohttp_client.async_create_clientsession", return_value=mock_aiohttp_session),
        patch("custom_components.hellowatt.client.HelloWattApiClient") as mock_client_class,
        patch.object(hass.config_entries, "async_reload") as mock_reload,
    ):
        mock_client_class.return_value = mock_client
        await async_reload_entry(hass, entry)

        mock_reload.assert_called_once_with(entry.entry_id)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_setup_entry_handles_homes_without_pdl(
    hass: HomeAssistant,
    mock_aiohttp_session,
    mock_hellowatt_homes,
) -> None:
    """Test setup skips homes without PDL."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        unique_id="test@example.com",
        options={},
    )

    homes_without_pdl = [
        {
            "id": "home123",
            "address": "123 Test St",
            "area": {"postalCode": "75001", "name": "Paris"},
            # Missing enedisHome with PDL
        }
    ]

    mock_client = Mock(spec=HelloWattApiClient)
    mock_client._session = mock_aiohttp_session
    mock_client.authenticate = AsyncMock()
    mock_client.get_homes = AsyncMock(return_value=homes_without_pdl) # Mock get_homes


    with (
        patch("homeassistant.helpers.aiohttp_client.async_create_clientsession", return_value=mock_aiohttp_session),
        patch("custom_components.hellowatt.client.HelloWattApiClient") as mock_client_class,
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups") as mock_forward_setups,
        patch(
            "custom_components.hellowatt.coordinator.HelloWattCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_client_class.return_value = mock_client
        mock_forward_setups.return_value = None

        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator


        await async_setup_entry(hass, entry)

        mock_coordinator_class.assert_not_called()
        mock_client_class.assert_called_once_with(
            session=mock_aiohttp_session,
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )
        mock_client.authenticate.assert_called_once()
        mock_forward_setups.assert_called_once_with(hass, entry, PLATFORMS)


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_setup_entry_handles_empty_homes(
    hass: HomeAssistant,
    mock_aiohttp_session,
) -> None:
    """Test setup handles account with no homes."""
    entry = ConfigEntry(
        minor_version=1,
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        unique_id="test@example.com",
        options={},
    )

    mock_client = Mock(spec=HelloWattApiClient)
    mock_client._session = mock_aiohttp_session
    mock_client.authenticate = AsyncMock()
    mock_client.get_homes = AsyncMock(return_value=[]) # Mock get_homes to return empty list


    with (
        patch("homeassistant.helpers.aiohttp_client.async_create_clientsession", return_value=mock_aiohttp_session),
        patch("custom_components.hellowatt.client.HelloWattApiClient") as mock_client_class,
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups") as mock_forward_setups,
    ):
        mock_client_class.return_value = mock_client
        mock_forward_setups.return_value = None

        result = await async_setup_entry(hass, entry)

        assert result is True
        assert len(hass.data[DOMAIN][entry.entry_id]["coordinators"]) == 0
        mock_client_class.assert_called_once_with(
            session=mock_aiohttp_session,
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )
        mock_client.authenticate.assert_called_once()
        mock_forward_setups.assert_called_once_with(hass, entry, PLATFORMS)