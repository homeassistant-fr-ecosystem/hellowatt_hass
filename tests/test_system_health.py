"""Tests for HelloWatt system health.

Following Home Assistant testing guidelines:
https://developers.home-assistant.io/docs/creating_integration_tests_file_structure
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant

from custom_components.hellowatt.const import DOMAIN
from custom_components.hellowatt.system_health import (
    async_register,
    async_system_health_info,
)

# ============================================================================
# Registration Tests
# ============================================================================


def test_async_register_registers_info_callback() -> None:
    """Test async_register registers the info callback."""
    register = Mock()

    async_register(Mock(), register)

    register.async_register_info.assert_called_once_with(async_system_health_info)


# ============================================================================
# System Health Info Tests
# ============================================================================


async def test_async_system_health_info_no_accounts(hass: HomeAssistant) -> None:
    """Test system health info when no accounts are configured."""
    with patch(
        "custom_components.hellowatt.system_health.system_health.async_check_can_reach_url",
        AsyncMock(return_value="ok"),
    ):
        result = await async_system_health_info(hass)

    assert result == {
        "api_endpoint_reachable": "ok",
        "configured_accounts": 0,
        "total_pdl_coordinators": 0,
    }


async def test_async_system_health_info_with_accounts_and_coordinators(
    hass: HomeAssistant,
) -> None:
    """Test system health info counts accounts and coordinators."""
    hass.data[DOMAIN] = {
        "entry_1": {
            "client": Mock(),
            "coordinators": {"pdl1": Mock(), "pdl2": Mock()},
        },
        "entry_2": {
            "client": Mock(),
            "coordinators": {"pdl3": Mock()},
        },
    }

    with patch(
        "custom_components.hellowatt.system_health.system_health.async_check_can_reach_url",
        AsyncMock(return_value="ok"),
    ):
        result = await async_system_health_info(hass)

    assert result["configured_accounts"] == 2
    assert result["total_pdl_coordinators"] == 3


async def test_async_system_health_info_ignores_non_dict_entries(
    hass: HomeAssistant,
) -> None:
    """Test system health info ignores entries that are not dicts."""
    hass.data[DOMAIN] = {"entry_1": "not_a_dict"}

    with patch(
        "custom_components.hellowatt.system_health.system_health.async_check_can_reach_url",
        AsyncMock(return_value="ok"),
    ):
        result = await async_system_health_info(hass)

    assert result["configured_accounts"] == 1
    assert result["total_pdl_coordinators"] == 0


async def test_async_system_health_info_api_unreachable(hass: HomeAssistant) -> None:
    """Test system health info reports API unreachable status."""
    with patch(
        "custom_components.hellowatt.system_health.system_health.async_check_can_reach_url",
        AsyncMock(return_value={"type": "failed", "error": "unreachable"}),
    ):
        result = await async_system_health_info(hass)

    assert result["api_endpoint_reachable"] == {
        "type": "failed",
        "error": "unreachable",
    }
