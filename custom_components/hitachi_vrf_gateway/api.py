"""API client for Hitachi VRF Gateway."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .const import (
    API_ACT_CONTROL,
    API_ACT_LOGIN,
    API_ACT_STATUS,
    API_MOD_AUTH,
    API_MOD_DEVICE,
    FIELD_FAN,
    FIELD_MODE,
    FIELD_POWER,
    FIELD_TEMP,
    POWER_OFF,
    POWER_ON,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class HitachiDeviceStatus:
    """Status of one indoor unit."""
    device_id: int
    power: str = "OFF"
    mode: str = "Heat"
    fan_speed: str = "Sharp"
    target_temp: float = 20.0
    room_temp: float | None = None
    alarm: str = "0"
    raw: dict[str, Any] = field(default_factory=dict)


class HitachiGatewayApi:
    """Handles login, session, status and control for one gateway."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self._session = session
        self._logged_in = False

    def _url(self) -> str:
        return f"https://{self.host}/index.cgi"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def async_login(self) -> bool:
        """Login to the gateway and store session cookie."""
        session = await self._get_session()
        payload = {
            "mod": API_MOD_AUTH,
            "act": API_ACT_LOGIN,
            "username": self.username,
            "password": self.password,
        }
        try:
            async with session.post(
                self._url(),
                data=payload,
                params={"mod": API_MOD_AUTH, "act": API_ACT_LOGIN},
                ssl=self.verify_ssl,
                allow_redirects=True,
            ) as resp:
                resp.raise_for_status()
                self._logged_in = True
                _LOGGER.debug("Login successful for %s", self.host)
                return True
        except aiohttp.ClientError as err:
            _LOGGER.error("Login failed for %s: %s", self.host, err)
            self._logged_in = False
            return False

    async def async_get_status(self, device_id: int) -> HitachiDeviceStatus:
        """Get status JSON for one indoor unit."""
        if not self._logged_in:
            await self.async_login()

        session = await self._get_session()
        params = {
            "mod": API_MOD_DEVICE,
            "act": API_ACT_STATUS,
            "dev": str(device_id),
        }
        try:
            async with session.get(
                self._url(),
                params=params,
                ssl=self.verify_ssl,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                return self._parse_status(device_id, data)
        except aiohttp.ClientError as err:
            _LOGGER.error("Status fetch failed for dev %s: %s", device_id, err)
            return HitachiDeviceStatus(device_id=device_id)

    def _parse_status(self, device_id: int, data: dict) -> HitachiDeviceStatus:
        """Parse the JSON status response into a dataclass."""
        try:
            room_temp = float(data.get("Tr", 0) or 0)
        except (ValueError, TypeError):
            room_temp = None

        try:
            target_temp = float(data.get("Ts", 20.0) or 20.0)
        except (ValueError, TypeError):
            target_temp = 20.0

        return HitachiDeviceStatus(
            device_id=device_id,
            power=str(data.get("Operation", "OFF")),
            mode=str(data.get("Mode", "Heat")),
            fan_speed=str(data.get("Rair", "Sharp")),
            target_temp=target_temp,
            room_temp=room_temp,
            alarm=str(data.get("ALM", "0")),
            raw=data,
        )

    async def async_set_power(self, device_id: int, on: bool) -> bool:
        """Turn device on or off."""
        return await self._send_command(
            device_id, {FIELD_POWER: POWER_ON if on else POWER_OFF}
        )

    async def async_set_mode(self, device_id: int, mode_code: str) -> bool:
        """Set operation mode (heat/cool/fan/dry)."""
        return await self._send_command(device_id, {FIELD_MODE: mode_code})

    async def async_set_fan_mode(self, device_id: int, fan_code: str) -> bool:
        """Set fan speed."""
        return await self._send_command(device_id, {FIELD_FAN: fan_code})

    async def async_set_temperature(self, device_id: int, temperature: float) -> bool:
        """Set target temperature."""
        temp_str = f"{temperature:.1f}"
        return await self._send_command(device_id, {FIELD_TEMP: temp_str})

    async def _send_command(self, device_id: int, fields: dict) -> bool:
        """Send a POST control command to the gateway."""
        if not self._logged_in:
            await self.async_login()

        session = await self._get_session()
        payload = {
            "mod": API_MOD_DEVICE,
            "act": API_ACT_CONTROL,
            "dev": str(device_id),
            **fields,
        }
        try:
            async with session.post(
                self._url(),
                data=payload,
                params={"mod": API_MOD_DEVICE, "act": API_ACT_CONTROL, "dev": str(device_id)},
                ssl=self.verify_ssl,
            ) as resp:
                resp.raise_for_status()
                _LOGGER.debug("Command sent to dev %s: %s", device_id, fields)
                return True
        except aiohttp.ClientError as err:
            _LOGGER.error("Command failed for dev %s: %s", device_id, err)
            return False

    async def async_close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
