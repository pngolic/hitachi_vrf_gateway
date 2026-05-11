"""Data update coordinator for Hitachi VRF Gateway."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HitachiDeviceStatus, HitachiGatewayApi
from .const import (
    CONF_DEVICES,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class HitachiGatewayCoordinator(DataUpdateCoordinator[dict[int, HitachiDeviceStatus]]):
    """Coordinator that polls all devices on one gateway."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.device_ids: list[int] = [
            int(x.strip())
            for x in entry.data[CONF_DEVICES].split(",")
            if x.strip()
        ]
        self.api = HitachiGatewayApi(
            host=entry.data[CONF_HOST],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[int, HitachiDeviceStatus]:
        """Fetch status for all devices. Called automatically every 30s."""
        results: dict[int, HitachiDeviceStatus] = {}

        # Login if needed (api handles session internally)
        if not self.api._logged_in:
            login_ok = await self.api.async_login()
            if not login_ok:
                raise UpdateFailed(f"Cannot login to gateway {self.api.host}")

        for dev_id in self.device_ids:
            try:
                status = await self.api.async_get_status(dev_id)
                results[dev_id] = status
                _LOGGER.debug(
                    "Dev %s → power=%s mode=%s temp=%s",
                    dev_id, status.power, status.mode, status.target_temp,
                )
            except Exception as err:
                _LOGGER.warning("Failed to poll dev %s: %s", dev_id, err)
                # Keep last known state if available
                if self.data and dev_id in self.data:
                    results[dev_id] = self.data[dev_id]

        return results
