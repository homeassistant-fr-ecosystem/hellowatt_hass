"""API Client for HelloWatt."""
from __future__ import annotations

from datetime import datetime
import aiohttp

from .const import API_URL

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Accept": "application/json; version=1.48",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.hellowatt.fr/mon-compte/",
}

class HelloWattApiClient:
    """HelloWatt API Client."""

    def __init__(
        self, session: aiohttp.ClientSession, username: str, password: str
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._username = username
        self._password = password
        self._homes = []
        self._authenticating = False

    @property
    def homes(self) -> list[dict]:
        """Return the homes."""
        return self._homes

    def _get_headers(self) -> dict:
        """Get headers."""
        headers = HEADERS.copy()
        for cookie in self._session.cookie_jar:
            if cookie.key == "csrftoken":
                headers["x-csrftoken"] = cookie.value
                break
        return headers

    async def authenticate(self) -> None:
        """Authenticate."""
        if self._authenticating:
            # Prevent recursive authentication attempts
            return

        self._authenticating = True
        try:
            login_url = "https://www.hellowatt.fr/accounts/login/"

            # 1. Get login page to get CSRF cookie
            async with self._session.get(login_url) as response:
                response.raise_for_status()

            csrftoken = ""
            for cookie in self._session.cookie_jar:
                if cookie.key == "csrftoken":
                    csrftoken = cookie.value
                    break

            data = {
                "login": self._username,
                "password": self._password,
                "csrfmiddlewaretoken": csrftoken,
            }

            headers = {
                "User-Agent": HEADERS["User-Agent"],
                "Referer": login_url,
            }

            async with self._session.post(login_url, data=data, headers=headers) as response:
                response.raise_for_status()

                try:
                    resp_json = await response.json()
                except Exception:
                    resp_json = None

                if resp_json:
                    form = resp_json.get("form", {})
                    if form.get("errors"):
                        raise Exception(f"Authentication failed: {form['errors']}")
                    for field_name, field_data in form.get("fields", {}).items():
                        if field_data.get("errors"):
                            raise Exception(f"Authentication failed ({field_name}): {field_data['errors']}")

                if not any(cookie.key == "sessionid" for cookie in self._session.cookie_jar):
                    raise Exception("Authentication failed: No session cookie received")

            # Fetch homes after successful authentication - bypass retry logic
            url = f"{API_URL}/homes"
            async with self._session.get(url, headers=self._get_headers()) as response:
                response.raise_for_status()
                self._homes = await response.json()
        finally:
            self._authenticating = False

    async def get_daily_consumption(self, home_id: str, start_date: datetime, end_date: datetime) -> dict:
        """Get daily electricity consumption."""
        url = f"{API_URL}/homes/{home_id}/sge_measures/conso_daily"
        params = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }

        async with self._session.get(url, params=params, headers=self._get_headers()) as response:
            if response.status == 403:
                # Session might have expired, try to re-authenticate
                await self.authenticate()
                # Retry the request
                async with self._session.get(url, params=params, headers=self._get_headers()) as retry_response:
                    if retry_response.status != 200:
                        response_text = await retry_response.text()
                        from .const import LOGGER
                        LOGGER.error(
                            "API error on retry for %s: status=%s, response=%s",
                            url,
                            retry_response.status,
                            response_text[:500]  # Limit to 500 chars
                        )
                    retry_response.raise_for_status()
                    return await retry_response.json()

            if response.status != 200:
                response_text = await response.text()
                from .const import LOGGER
                LOGGER.error(
                    "API error for %s: status=%s, params=%s, response=%s",
                    url,
                    response.status,
                    params,
                    response_text[:500]  # Limit to 500 chars
                )
            response.raise_for_status()
            return await response.json()

    async def get_daily_gas_consumption(self, home_id: str, start_date: datetime, end_date: datetime) -> dict:
        """Get daily gas consumption."""
        url = f"{API_URL}/homes/{home_id}/adict_measures/conso_daily"
        params = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }

        async with self._session.get(url, params=params, headers=self._get_headers()) as response:
            if response.status == 403:
                # Session might have expired, try to re-authenticate
                await self.authenticate()
                # Retry the request
                async with self._session.get(url, params=params, headers=self._get_headers()) as retry_response:
                    # 500 errors often indicate no gas contract, not a real error
                    if retry_response.status == 500:
                        from .const import LOGGER
                        LOGGER.debug(
                            "Gas data not available (status 500) - likely no gas contract for home %s",
                            home_id
                        )
                        raise Exception("No gas contract available")
                    if retry_response.status != 200:
                        response_text = await retry_response.text()
                        from .const import LOGGER
                        LOGGER.error(
                            "API error on retry for %s: status=%s, response=%s",
                            url,
                            retry_response.status,
                            response_text[:500]  # Limit to 500 chars
                        )
                    retry_response.raise_for_status()
                    return await retry_response.json()

            # 500 errors often indicate no gas contract, not a real error
            if response.status == 500:
                from .const import LOGGER
                LOGGER.debug(
                    "Gas data not available (status 500) - likely no gas contract for home %s",
                    home_id
                )
                raise Exception("No gas contract available")

            if response.status != 200:
                response_text = await response.text()
                from .const import LOGGER
                LOGGER.error(
                    "API error for %s: status=%s, params=%s, response=%s",
                    url,
                    response.status,
                    params,
                    response_text[:500]  # Limit to 500 chars
                )
            response.raise_for_status()
            return await response.json()

    async def get_yearly_temperature(self, home_id: str, start_date: datetime, end_date: datetime) -> dict:
        """Get yearly temperature."""
        url = f"{API_URL}/homes/{home_id}/temperature_measures/yearly"
        params = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }

        async with self._session.get(url, params=params, headers=self._get_headers()) as response:
            if response.status == 403:
                # Session might have expired, try to re-authenticate
                await self.authenticate()
                # Retry the request
                async with self._session.get(url, params=params, headers=self._get_headers()) as retry_response:
                    retry_response.raise_for_status()
                    return await retry_response.json()
            response.raise_for_status()
            return await response.json()

    async def get_contracts(self, home_id: str) -> list[dict]:
        """Get contracts."""
        url = f"{API_URL}/homes/{home_id}/contracts"

        async with self._session.get(url, headers=self._get_headers()) as response:
            if response.status == 403:
                # Session might have expired, try to re-authenticate
                await self.authenticate()
                # Retry the request
                async with self._session.get(url, headers=self._get_headers()) as retry_response:
                    retry_response.raise_for_status()
                    return await retry_response.json()
            response.raise_for_status()
            return await response.json()

    async def get_homes(self) -> list[dict]:
        """Get homes."""
        url = f"{API_URL}/homes"

        async with self._session.get(url, headers=self._get_headers()) as response:
            if response.status == 403:
                # Session might have expired, try to re-authenticate
                await self.authenticate()
                # Retry the request
                async with self._session.get(url, headers=self._get_headers()) as retry_response:
                    retry_response.raise_for_status()
                    return await retry_response.json()
            response.raise_for_status()
            return await response.json()