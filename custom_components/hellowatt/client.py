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
        self, session: aiohttp.ClientSession, username: str, password: str, pdl: str
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._username = username
        self._password = password
        self._pdl = pdl

    @property
    def pdl(self) -> str:
        """Return the PDL."""
        return self._pdl

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

    async def get_daily_consumption(self, start_date: datetime, end_date: datetime) -> dict:
        """Get daily consumption."""
        url = f"{API_URL}/homes/{self._pdl}/sge_measures/conso_daily"
        params = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }

        async with self._session.get(url, params=params, headers=self._get_headers()) as response:
            response.raise_for_status()
            return await response.json()

    async def get_yearly_temperature(self, start_date: datetime, end_date: datetime) -> dict:
        """Get yearly temperature."""
        url = f"{API_URL}/homes/{self._pdl}/temperature_measures/yearly"
        params = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }

        async with self._session.get(url, params=params, headers=self._get_headers()) as response:
            response.raise_for_status()
            return await response.json()

    async def get_contracts(self) -> list[dict]:
        """Get contracts."""
        url = f"{API_URL}/homes/{self._pdl}/contracts"

        async with self._session.get(url, headers=self._get_headers()) as response:
            response.raise_for_status()
            return await response.json()

    async def get_homes(self) -> list[dict]:
        """Get homes."""
        url = f"{API_URL}/homes"

        async with self._session.get(url, headers=self._get_headers()) as response:
            response.raise_for_status()
            return await response.json()