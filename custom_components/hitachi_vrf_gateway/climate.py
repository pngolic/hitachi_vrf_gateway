"""Climate platform for Hitachi VRF Gateway."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import FAN_AUTO, FAN_HIGH, FAN_LOW, FAN_MEDIUM
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICES,
    CONF_GATEWAY_NAME,
    CONF_HOST,
    DOMAIN,
    FAN_AUTO,
    FAN_SHARP,
    FAN_STRONG,
    FAN_SUPER,
    FAN_WEAK,
    MODE_COOL,
    MODE_DRY,
    MODE_FAN,
    MODE_HEAT,
    TEMP_MAX,
    TEMP_MIN,
    TEMP_STEP,
)
from .coordinator import HitachiGatewayCoordinator

_LOGGER = logging.getLogger(__name__)

# Map gateway mode codes → HA HVACMode
GATEWAY_TO_HVAC: dict[str, HVACMode] = {
    MODE_HEAT: HVACMode.HEAT,
    MODE_COOL: HVACMode.COOL,
    MODE_FAN:  HVACMode.FAN_ONLY,
    MODE_DRY:  HVACMode.DRY,
}

HVAC_TO_GATEWAY: dict[HVACMode, str] = {v: k for k, v in GATEWAY_TO_HVAC.items()}

# Map gateway fan codes → HA fan mode strings
GATEWAY_TO_FAN: dict[str, str] = {
    FAN_WEAK:   FAN_LOW,
    FAN_SHARP:  FAN_MEDIUM,
    FAN_STRONG: FAN_HIGH,
    FAN_SUPER:  "turbo",
    FAN_AUTO:   FAN_AUTO,
}

FAN_TO_GATEWAY: dict[str, str] = {v: k for k, v in GATEWAY_TO_FAN.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate entities from config entry."""
    coordinator: HitachiGatewayCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        HitachiClimateEntity(coordinator, entry, dev_id)
        for dev_id in coordinator.device_ids
    ]
    async_add_entities(entities, update_before_add=True)


class HitachiClimateEntity(CoordinatorEntity[HitachiGatewayCoordinator], ClimateEntity):
    """Represents one indoor VRF unit."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = TEMP_STEP
    _attr_min_temp = TEMP_MIN
    _attr_max_temp = TEMP_MAX
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.FAN_ONLY,
        HVACMode.DRY,
    ]
    _attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, "turbo", FAN_AUTO]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        coordinator: HitachiGatewayCoordinator,
        entry: ConfigEntry,
        device_id: int,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_dev{device_id}"
        self._attr_name = (
            f"{entry.data.get(CONF_GATEWAY_NAME, 'Hitachi')} Unit {device_id}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="Hitachi / Johnson Controls",
            model="VRF Smart Gateway",
            configuration_url=f"https://{entry.data[CONF_HOST]}",
        )

    @property
    def _status(self):
        """Shortcut to this device's status from coordinator data."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._device_id)
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        if not self._status:
            return HVACMode.OFF
        if self._status.power == "0" or self._status.power == "OFF":
            return HVACMode.OFF
        return GATEWAY_TO_HVAC.get(self._status.mode, HVACMode.HEAT)

    @property
    def current_temperature(self) -> float | None:
        return self._status.room_temp if self._status else None

    @property
    def target_temperature(self) -> float | None:
        return self._status.target_temp if self._status else None

    @property
    def fan_mode(self) -> str | None:
        if not self._status:
            return FAN_AUTO
        return GATEWAY_TO_FAN.get(self._status.fan_speed, FAN_AUTO)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.api.async_set_power(self._device_id, False)
        else:
            await self.coordinator.api.async_set_power(self._device_id, True)
            mode_code = HVAC_TO_GATEWAY.get(hvac_mode, MODE_HEAT)
            await self.coordinator.api.async_set_mode(self._device_id, mode_code)
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            await self.coordinator.api.async_set_temperature(self._device_id, temp)
            await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan speed."""
        fan_code = FAN_TO_GATEWAY.get(fan_mode, FAN_SHARP)
        await self.coordinator.api.async_set_fan_mode(self._device_id, fan_code)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn the unit on."""
        await self.coordinator.api.async_set_power(self._device_id, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn the unit off."""
        await self.coordinator.api.async_set_power(self._device_id, False)
        await self.coordinator.async_request_refresh()
