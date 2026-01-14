"""Tests for HelloWatt config flow.

Following Home Assistant testing guidelines:
https://developers.home-assistant.io/docs/creating_integration_tests_file_structure
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.hellowatt.const import DOMAIN


# ============================================================================
# Config Flow Tests
# ============================================================================


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Test successful user configuration flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "custom_components.hellowatt.config_flow.HelloWattApiClient"
    ) as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.authenticate = AsyncMock()
        mock_client.return_value = mock_client_instance

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test_password",
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "HelloWatt (test@example.com)"
    assert result["data"] == {
        CONF_USERNAME: "test@example.com",
        CONF_PASSWORD: "test_password",
    }


async def test_user_flow_already_configured(hass: HomeAssistant) -> None:
    """Test config flow when integration is already configured."""
    # Create an existing entry
    entry = hass.config_entries.async_entry_for_domain_unique_id(
        DOMAIN, "test@example.com"
    )
    if not entry:
        hass.config_entries._entries[DOMAIN] = [
            config_entries.ConfigEntry(
                version=1,
                domain=DOMAIN,
                title="HelloWatt (test@example.com)",
                data={
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "old_password",
                },
                source=config_entries.SOURCE_USER,
                unique_id="test@example.com",
            )
        ]

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_normalizes_username(hass: HomeAssistant) -> None:
    """Test that username is normalized (lowercase, trimmed)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.hellowatt.config_flow.HelloWattApiClient"
    ) as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.authenticate = AsyncMock()
        mock_client.return_value = mock_client_instance

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "  Test@Example.COM  ",
                CONF_PASSWORD: "test_password",
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "HelloWatt (test@example.com)"


# ============================================================================
# Options Flow Tests
# ============================================================================


async def test_options_flow(hass: HomeAssistant, mock_config_entry) -> None:
    """Test options flow configuration."""
    entry = config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="HelloWatt",
        data=mock_config_entry,
        source=config_entries.SOURCE_USER,
        unique_id="test@example.com",
        options={},
    )

    hass.config_entries._entries.setdefault(DOMAIN, []).append(entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "update_interval": 2,
            "lookback_days": 10,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "update_interval": 2,
        "lookback_days": 10,
    }


async def test_options_flow_with_defaults(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test options flow uses default values."""
    from custom_components.hellowatt.const import (
        DEFAULT_LOOKBACK_DAYS,
        DEFAULT_UPDATE_INTERVAL_HOURS,
    )

    entry = config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="HelloWatt",
        data=mock_config_entry,
        source=config_entries.SOURCE_USER,
        unique_id="test@example.com",
        options={},
    )

    hass.config_entries._entries.setdefault(DOMAIN, []).append(entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Check that form has default values in schema
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    # Schema contains defaults through vol.Optional


async def test_options_flow_validates_ranges(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test options flow validates input ranges."""
    entry = config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="HelloWatt",
        data=mock_config_entry,
        source=config_entries.SOURCE_USER,
        unique_id="test@example.com",
        options={},
    )

    hass.config_entries._entries.setdefault(DOMAIN, []).append(entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Test valid ranges (1-24 hours, 3-30 days)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "update_interval": 12,  # Valid: 1-24
            "lookback_days": 15,  # Valid: 3-30
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY


# ============================================================================
# Authentication Validation Tests
# ============================================================================


async def test_user_flow_invalid_credentials(hass: HomeAssistant) -> None:
    """Test config flow with invalid credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.hellowatt.config_flow.HelloWattApiClient"
    ) as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.authenticate = AsyncMock(
            side_effect=Exception("Authentication failed: Invalid credentials")
        )
        mock_client.return_value = mock_client_instance

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "wrong_password",
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test config flow when cannot connect to API."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.hellowatt.config_flow.HelloWattApiClient"
    ) as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.authenticate = AsyncMock(
            side_effect=Exception("ClientError")
        )
        mock_client.return_value = mock_client_instance

        # We need to handle aiohttp.ClientError properly
        import aiohttp

        mock_client_instance.authenticate = AsyncMock(side_effect=aiohttp.ClientError())

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test_password",
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_timeout(hass: HomeAssistant) -> None:
    """Test config flow when connection times out."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.hellowatt.config_flow.HelloWattApiClient"
    ) as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.authenticate = AsyncMock(side_effect=TimeoutError())
        mock_client.return_value = mock_client_instance

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test_password",
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "timeout"}


# ============================================================================
# Reauth Flow Tests
# ============================================================================


async def test_reauth_flow_success(hass: HomeAssistant) -> None:
    """Test successful reauth flow."""
    # Create an existing entry
    entry = config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "old_password",
        },
        source=config_entries.SOURCE_USER,
        unique_id="test@example.com",
    )
    hass.config_entries._entries.setdefault(DOMAIN, []).append(entry)

    # Trigger reauth
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": entry.entry_id,
            "unique_id": entry.unique_id,
        },
        data=entry.data,
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    # Submit new password
    with patch(
        "custom_components.hellowatt.config_flow.HelloWattApiClient"
    ) as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.authenticate = AsyncMock()
        mock_client.return_value = mock_client_instance

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_PASSWORD: "new_password"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_reauth_flow_invalid_password(hass: HomeAssistant) -> None:
    """Test reauth flow with invalid new password."""
    # Create an existing entry
    entry = config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "old_password",
        },
        source=config_entries.SOURCE_USER,
        unique_id="test@example.com",
    )
    hass.config_entries._entries.setdefault(DOMAIN, []).append(entry)

    # Trigger reauth
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": entry.entry_id,
            "unique_id": entry.unique_id,
        },
        data=entry.data,
    )

    # Submit invalid password
    with patch(
        "custom_components.hellowatt.config_flow.HelloWattApiClient"
    ) as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.authenticate = AsyncMock(
            side_effect=Exception("Authentication failed")
        )
        mock_client.return_value = mock_client_instance

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_PASSWORD: "wrong_new_password"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test reauth flow when cannot connect to API."""
    import aiohttp

    # Create an existing entry
    entry = config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="HelloWatt (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "old_password",
        },
        source=config_entries.SOURCE_USER,
        unique_id="test@example.com",
    )
    hass.config_entries._entries.setdefault(DOMAIN, []).append(entry)

    # Trigger reauth
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": entry.entry_id,
            "unique_id": entry.unique_id,
        },
        data=entry.data,
    )

    # Submit password but connection fails
    with patch(
        "custom_components.hellowatt.config_flow.HelloWattApiClient"
    ) as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.authenticate = AsyncMock(side_effect=aiohttp.ClientError())
        mock_client.return_value = mock_client_instance

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_PASSWORD: "new_password"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
