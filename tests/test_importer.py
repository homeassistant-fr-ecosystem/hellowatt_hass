"""Tests for HelloWatt importer."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

from homeassistant.core import HomeAssistant

from custom_components.hellowatt.importer import _import_statistics


async def test_import_statistics_base_tariff_no_peak_off_peak_imported(
    hass: HomeAssistant,
    mock_api_response_electricity_base: dict[str, Any],
) -> None:
    """Base-tariff data must not import electricity_peak or electricity_off_peak statistics."""
    captured_calls: list[str] = []

    def fake_import(_hass_arg, metadata, _stats_data):
        captured_calls.append(metadata.statistic_id)
        return True

    mock_er = Mock()
    mock_er.async_get_entity_id = Mock(
        side_effect=lambda _platform, _domain, unique_id: f"sensor.{unique_id}"
    )

    with (
        patch(
            "custom_components.hellowatt.importer.er.async_get", return_value=mock_er
        ),
        patch(
            "homeassistant.components.recorder.models.StatisticData",
            side_effect=Mock,
        ),
        patch(
            "homeassistant.components.recorder.models.StatisticMetaData",
            side_effect=Mock,
        ),
        patch(
            "homeassistant.components.recorder.statistics.async_import_statistics",
            side_effect=fake_import,
        ),
    ):
        await _import_statistics(
            hass,
            pdl="12345678901234",
            energy_type="electricity",
            data=mock_api_response_electricity_base,
        )

    peak_calls = [s for s in captured_calls if "peak" in s]
    assert peak_calls == [], (
        f"Base-tariff import must not produce peak/off_peak statistics, got: {peak_calls}"
    )


async def test_import_statistics_hphc_tariff_imports_peak_off_peak(
    hass: HomeAssistant,
    mock_api_response_electricity: dict[str, Any],
) -> None:
    """HP/HC-tariff data must import electricity_peak and electricity_off_peak statistics."""
    captured_calls: list[str] = []

    def fake_import(_hass_arg, metadata, _stats_data):
        captured_calls.append(metadata.statistic_id)
        return True

    mock_er = Mock()
    mock_er.async_get_entity_id = Mock(
        side_effect=lambda _platform, _domain, unique_id: f"sensor.{unique_id}"
    )

    with (
        patch(
            "custom_components.hellowatt.importer.er.async_get", return_value=mock_er
        ),
        patch(
            "homeassistant.components.recorder.models.StatisticData",
            side_effect=Mock,
        ),
        patch(
            "homeassistant.components.recorder.models.StatisticMetaData",
            side_effect=Mock,
        ),
        patch(
            "homeassistant.components.recorder.statistics.async_import_statistics",
            side_effect=fake_import,
        ),
    ):
        await _import_statistics(
            hass,
            pdl="12345678901234",
            energy_type="electricity",
            data=mock_api_response_electricity,
        )

    assert any("_peak" in s and "off" not in s for s in captured_calls), (
        f"Expected electricity_peak in imported statistics, got: {captured_calls}"
    )
    assert any("off_peak" in s for s in captured_calls), (
        f"Expected electricity_off_peak in imported statistics, got: {captured_calls}"
    )


async def test_import_statistics_base_tariff_cumulative_sums_no_peak_keys(
    hass: HomeAssistant,
    mock_api_response_electricity_base: dict[str, Any],
) -> None:
    """cumulative_sums must not be initialized with peak/off_peak keys for base-tariff data."""
    cumulative_sums: dict[str, float] = {}

    mock_er = Mock()
    mock_er.async_get_entity_id = Mock(return_value=None)

    with (
        patch(
            "custom_components.hellowatt.importer.er.async_get", return_value=mock_er
        ),
        patch(
            "homeassistant.components.recorder.models.StatisticData",
            side_effect=Mock,
        ),
        patch(
            "homeassistant.components.recorder.models.StatisticMetaData",
            side_effect=Mock,
        ),
        patch(
            "homeassistant.components.recorder.statistics.async_import_statistics",
            return_value=True,
        ),
    ):
        await _import_statistics(
            hass,
            pdl="12345678901234",
            energy_type="electricity",
            data=mock_api_response_electricity_base,
            cumulative_sums=cumulative_sums,
        )

    peak_keys = [k for k in cumulative_sums if "peak" in k]
    assert peak_keys == [], (
        f"cumulative_sums must not contain peak/off_peak keys for base-tariff, got: {peak_keys}"
    )
