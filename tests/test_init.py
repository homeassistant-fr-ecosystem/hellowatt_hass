"""Tests for HelloWatt integration setup.

Following Home Assistant testing guidelines:
https://developers.home-assistant.io/docs/creating_integration_tests_file_structure
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.hellowatt import (
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.hellowatt.const import DOMAIN

# ============================================================================
# Integration Setup Tests
# ============================================================================


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_setup_entry_success(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
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

    with (
        patch("custom_components.hellowatt.async_create_clientsession"),
        patch("custom_components.hellowatt.HelloWattApiClient") as mock_client_class,
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        mock_client_class.return_value = mock_hellowatt_client_authenticated
        mock_hellowatt_client_authenticated.authenticate = AsyncMock()

        result = await async_setup_entry(hass, entry)

        assert result is True
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]
        assert "client" in hass.data[DOMAIN][entry.entry_id]
        assert "coordinators" in hass.data[DOMAIN][entry.entry_id]

        # Verify client was created and authenticated
        mock_client_class.assert_called_once()
        mock_hellowatt_client_authenticated.authenticate.assert_called_once()


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_setup_entry_creates_coordinators(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
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

    with (
        patch("custom_components.hellowatt.async_create_clientsession"),
        patch("custom_components.hellowatt.HelloWattApiClient") as mock_client_class,
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
        patch(
            "custom_components.hellowatt.HelloWattCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_client_class.return_value = mock_hellowatt_client_authenticated
        mock_hellowatt_client_authenticated.authenticate = AsyncMock()

        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        await async_setup_entry(hass, entry)

        # Should create coordinator for each home with PDL
        # mock_hellowatt_homes has 2 homes with PDLs
        assert mock_coordinator_class.call_count == 2


async def test_async_setup_entry_auth_failure(
    hass: HomeAssistant,
    mock_hellowatt_client,
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

    with (
        patch("custom_components.hellowatt.async_create_clientsession"),
        patch("custom_components.hellowatt.HelloWattApiClient") as mock_client_class,
    ):
        mock_client_class.return_value = mock_hellowatt_client
        mock_hellowatt_client.authenticate = AsyncMock(
            side_effect=Exception("Authentication failed")
        )

        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, entry)


async def test_async_setup_entry_no_session_cookie(
    hass: HomeAssistant,
    mock_hellowatt_client,
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

    with (
        patch("custom_components.hellowatt.async_create_clientsession"),
        patch("custom_components.hellowatt.HelloWattApiClient") as mock_client_class,
    ):
        mock_client_class.return_value = mock_hellowatt_client
        mock_hellowatt_client.authenticate = AsyncMock(
            side_effect=Exception("No session cookie received")
        )

        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, entry)


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_setup_entry_registers_services(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
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

    with (
        patch("custom_components.hellowatt.async_create_clientsession"),
        patch("custom_components.hellowatt.HelloWattApiClient") as mock_client_class,
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
        patch(
            "custom_components.hellowatt.HelloWattCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_client_class.return_value = mock_hellowatt_client_authenticated
        mock_hellowatt_client_authenticated.authenticate = AsyncMock()

        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        await async_setup_entry(hass, entry)

        # Verify services are registered
        assert hass.services.has_service(DOMAIN, "import_historical_data")
        assert hass.services.has_service(DOMAIN, "clear_statistics")


# ============================================================================
# Integration Unload Tests
# ============================================================================


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_unload_entry_success(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
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

    # Setup first
    with (
        patch("custom_components.hellowatt.async_create_clientsession"),
        patch("custom_components.hellowatt.HelloWattApiClient") as mock_client_class,
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
        patch(
            "custom_components.hellowatt.HelloWattCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_client_class.return_value = mock_hellowatt_client_authenticated
        mock_hellowatt_client_authenticated.authenticate = AsyncMock()

        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        await async_setup_entry(hass, entry)

    # Now unload
    with patch.object(hass.config_entries, "async_unload_platforms", return_value=True):
        result = await async_unload_entry(hass, entry)

        assert result is True
        assert entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_unload_entry_removes_services_when_last_entry(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
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

    # Setup
    with (
        patch("custom_components.hellowatt.async_create_clientsession"),
        patch("custom_components.hellowatt.HelloWattApiClient") as mock_client_class,
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
        patch(
            "custom_components.hellowatt.HelloWattCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_client_class.return_value = mock_hellowatt_client_authenticated
        mock_hellowatt_client_authenticated.authenticate = AsyncMock()

        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        await async_setup_entry(hass, entry)

    # Services should be registered
    assert hass.services.has_service(DOMAIN, "import_historical_data")

    # Unload
    with patch.object(hass.config_entries, "async_unload_platforms", return_value=True):
        await async_unload_entry(hass, entry)

    # Services should be removed
    assert not hass.services.has_service(DOMAIN, "import_historical_data")
    assert not hass.services.has_service(DOMAIN, "clear_statistics")


@pytest.mark.usefixtures("mock_hellowatt_homes")
async def test_async_unload_entry_keeps_services_when_other_entries_exist(
    hass: HomeAssistant,
    mock_hellowatt_client_authenticated,
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
        unique_id="test1@example.com",
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
        unique_id="test2@example.com",
        options={},
    )

    # Setup both entries
    with (
        patch("custom_components.hellowatt.async_create_clientsession"),
        patch("custom_components.hellowatt.HelloWattApiClient") as mock_client_class,
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
        patch(
            "custom_components.hellowatt.HelloWattCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_client_class.return_value = mock_hellowatt_client_authenticated
        mock_hellowatt_client_authenticated.authenticate = AsyncMock()

        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        await async_setup_entry(hass, entry1)
        await async_setup_entry(hass, entry2)

    # Unload first entry
    with patch.object(hass.config_entries, "async_unload_platforms", return_value=True):
        await async_unload_entry(hass, entry1)

    # Services should still exist (entry2 still loaded)
    assert hass.services.has_service(DOMAIN, "import_historical_data")
    assert hass.services.has_service(DOMAIN, "clear_statistics")


# ============================================================================
# Integration Reload Tests
# ============================================================================


@pytest.mark.usefixtures("mock_hellowatt_client_authenticated", "mock_hellowatt_homes")
async def test_async_reload_entry(
    hass: HomeAssistant,
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

    with patch.object(hass.config_entries, "async_reload") as mock_reload:
        await async_reload_entry(hass, entry)

        mock_reload.assert_called_once_with(entry.entry_id)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


async def test_async_setup_entry_handles_homes_without_pdl(
    hass: HomeAssistant,
    mock_hellowatt_client,
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

    # Mock homes without PDL
    homes_without_pdl = [
        {
            "id": "home123",
            "address": "123 Test St",
            "area": {"postalCode": "75001", "name": "Paris"},
            # Missing enedisHome with PDL
        }
    ]

    with (
        patch("custom_components.hellowatt.async_create_clientsession"),
        patch("custom_components.hellowatt.HelloWattApiClient") as mock_client_class,
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
        patch(
            "custom_components.hellowatt.HelloWattCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_client_class.return_value = mock_hellowatt_client
        mock_hellowatt_client.authenticate = AsyncMock()
        mock_hellowatt_client._homes = homes_without_pdl

        await async_setup_entry(hass, entry)

        # Should not create coordinators for homes without PDL
        mock_coordinator_class.assert_not_called()


async def test_async_setup_entry_handles_empty_homes(
    hass: HomeAssistant,
    mock_hellowatt_client,
) -> None:
    """Test setup logs a warning when account has no homes."""
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

    with (
        patch("custom_components.hellowatt.async_create_clientsession"),
        patch("custom_components.hellowatt.HelloWattApiClient") as mock_client_class,
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ),
    ):
        mock_client_class.return_value = mock_hellowatt_client
        mock_hellowatt_client.authenticate = AsyncMock()
        mock_hellowatt_client._homes = []

        with patch("custom_components.hellowatt.LOGGER") as mock_logger:
            result = await async_setup_entry(hass, entry)

            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "no homes" in warning_msg.lower() or "0" in warning_msg

        assert result is True
        assert len(hass.data[DOMAIN][entry.entry_id]["coordinators"]) == 0
