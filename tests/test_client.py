"""Tests for HelloWatt API client."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest

from custom_components.hellowatt.client import HelloWattApiClient


@pytest.mark.asyncio
class TestHelloWattApiClient:
    """Test HelloWatt API client."""

    def test_init(self, mock_aiohttp_session):
        """Test client initialization."""
        client = HelloWattApiClient(
            session=mock_aiohttp_session,
            username="test@example.com",
            password="test_password",
        )

        assert client._username == "test@example.com"
        assert client._password == "test_password"
        assert client._homes == []
        assert client._authenticating is False

    def test_homes_property(self, mock_hellowatt_client):
        """Test homes property returns homes list."""
        assert len(mock_hellowatt_client.homes) == 1
        assert mock_hellowatt_client.homes[0]["id"] == "home123"

    def test_get_headers_without_csrf(self, mock_hellowatt_client):
        """Test getting headers without CSRF token."""
        headers = mock_hellowatt_client._get_headers()

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "x-csrftoken" not in headers

    def test_get_headers_with_csrf(self, mock_hellowatt_client):
        """Test getting headers with CSRF token."""
        # Mock cookie jar with CSRF token
        mock_cookie = Mock()
        mock_cookie.key = "csrftoken"
        mock_cookie.value = "test_csrf_token"

        mock_hellowatt_client._session.cookie_jar.__iter__ = Mock(
            return_value=iter([mock_cookie])
        )

        headers = mock_hellowatt_client._get_headers()

        assert headers["x-csrftoken"] == "test_csrf_token"

    async def test_request_with_retry_success(
        self, mock_hellowatt_client, mock_api_response_electricity
    ):
        """Test successful request without retry."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_api_response_electricity)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_hellowatt_client._session.request = Mock(return_value=mock_response)

        result = await mock_hellowatt_client._request_with_retry(
            "GET", "https://example.com/api/test"
        )

        assert result == mock_api_response_electricity

    async def test_request_with_retry_403_reauthenticates(
        self, mock_hellowatt_client, mock_api_response_electricity
    ):
        """Test request retries after 403 with re-authentication."""
        # First response: 403 (authentication needed)
        mock_response_403 = AsyncMock()
        mock_response_403.status = 403
        mock_response_403.__aenter__ = AsyncMock(return_value=mock_response_403)
        mock_response_403.__aexit__ = AsyncMock(return_value=None)

        # Second response: 200 (success after re-auth)
        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.json = AsyncMock(return_value=mock_api_response_electricity)
        mock_response_200.__aenter__ = AsyncMock(return_value=mock_response_200)
        mock_response_200.__aexit__ = AsyncMock(return_value=None)

        # Mock request to return 403 first, then 200
        mock_hellowatt_client._session.request = Mock(
            side_effect=[mock_response_403, mock_response_200]
        )

        # Mock authenticate method
        mock_hellowatt_client.authenticate = AsyncMock()

        result = await mock_hellowatt_client._request_with_retry(
            "GET", "https://example.com/api/test"
        )

        # Verify authenticate was called
        mock_hellowatt_client.authenticate.assert_called_once()
        assert result == mock_api_response_electricity

    async def test_handle_response_500_with_gas_endpoint(self, mock_hellowatt_client):
        """Test 500 error handling for gas endpoint (no contract)."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        with pytest.raises(Exception, match="No gas contract available"):
            await mock_hellowatt_client._handle_response(
                mock_response, "https://example.com/api/gas", handle_500_as_no_data=True
            )

    async def test_handle_response_error_logging(self, mock_hellowatt_client):
        """Test error response logging."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")
        mock_response.raise_for_status = Mock(
            side_effect=aiohttp.ClientResponseError(
                request_info=Mock(), history=(), status=404
            )
        )

        with pytest.raises(aiohttp.ClientResponseError):
            await mock_hellowatt_client._handle_response(
                mock_response, "https://example.com/api/test"
            )

        # Verify text() was called for logging
        mock_response.text.assert_called_once()


@pytest.mark.asyncio
class TestHelloWattApiMethods:
    """Test HelloWatt API method wrappers."""

    async def test_get_daily_consumption(
        self, mock_hellowatt_client, mock_api_response_electricity
    ):
        """Test get_daily_consumption method."""
        mock_hellowatt_client._request_with_retry = AsyncMock(
            return_value=mock_api_response_electricity
        )

        start_date = datetime(2024, 1, 1, tzinfo=UTC)
        end_date = datetime(2024, 1, 2, tzinfo=UTC)

        result = await mock_hellowatt_client.get_daily_consumption(
            "home123", start_date, end_date
        )

        assert result == mock_api_response_electricity
        mock_hellowatt_client._request_with_retry.assert_called_once()

    async def test_get_daily_gas_consumption(
        self, mock_hellowatt_client, mock_api_response_gas
    ):
        """Test get_daily_gas_consumption method."""
        mock_hellowatt_client._request_with_retry = AsyncMock(
            return_value=mock_api_response_gas
        )

        start_date = datetime(2024, 1, 1, tzinfo=UTC)
        end_date = datetime(2024, 1, 2, tzinfo=UTC)

        result = await mock_hellowatt_client.get_daily_gas_consumption(
            "home123", start_date, end_date
        )

        assert result == mock_api_response_gas
        # Verify handle_500_as_no_data was set
        call_kwargs = mock_hellowatt_client._request_with_retry.call_args[1]
        assert call_kwargs.get("handle_500_as_no_data") is True

    async def test_get_yearly_temperature(
        self, mock_hellowatt_client, mock_api_response_temperature
    ):
        """Test get_yearly_temperature method."""
        mock_hellowatt_client._request_with_retry = AsyncMock(
            return_value=mock_api_response_temperature
        )

        start_date = datetime(2024, 1, 1, tzinfo=UTC)
        end_date = datetime(2024, 12, 31, tzinfo=UTC)

        result = await mock_hellowatt_client.get_yearly_temperature(
            "home123", start_date, end_date
        )

        assert result == mock_api_response_temperature

    async def test_get_contracts(
        self, mock_hellowatt_client, mock_api_response_contracts
    ):
        """Test get_contracts method."""
        mock_hellowatt_client._request_with_retry = AsyncMock(
            return_value=mock_api_response_contracts
        )

        result = await mock_hellowatt_client.get_contracts("home123")

        assert result == mock_api_response_contracts

    async def test_get_homes(self, mock_hellowatt_client):
        """Test get_homes method."""
        expected_homes = [{"id": "home123"}]
        mock_hellowatt_client._request_with_retry = AsyncMock(
            return_value=expected_homes
        )

        result = await mock_hellowatt_client.get_homes()

        assert result == expected_homes
