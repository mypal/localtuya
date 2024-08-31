"""Platform to locally control Tuya-based climate devices."""
import logging
from functools import partial
from typing import Any

from homeassistant.components.climate import (
    DOMAIN,
    ClimateEntity,
    HVACMode,
    ClimateEntityFeature,
    ATTR_HVAC_MODE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    UnitOfTemperature,
)
 
from .common import LocalTuyaEntity, async_setup_entry
 
_LOGGER = logging.getLogger(__name__)

ModeMap = {
    HVACMode.HEAT: "hot",
    HVACMode.COOL: "cold",
    HVACMode.AUTO: "heat_floorheat",
    HVACMode.HEAT_COOL: "floor_heat",
    HVACMode.FAN_ONLY: "wind",
}

def find_mode_key(value):
    for key, val in ModeMap.items():
        if val == value:
            return key
    return HVACMode.COOL

IDX_SWITCH = 1
IDX_MODE = 2
IDX_TEMP_SET = 16
IDX_TEMP_CURRENT = 24
IDX_LEVEL = 28
IDX_HUMIDITY = 34

def flow_schema(dps):
    """Return schema used in config flow."""
    return {
    }
 
 
class LocaltuyaClimate(LocalTuyaEntity, ClimateEntity):
    """Tuya climate device."""
 
    def __init__(
        self,
        device,
        config_entry,
        switchid,
        **kwargs,
    ):
        """Initialize a new LocaltuyaClimate."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.FAN_MODE |
            ClimateEntityFeature.TURN_OFF |
            ClimateEntityFeature.TURN_ON
        )
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO, HVACMode.HEAT_COOL, HVACMode.FAN_ONLY]
        self._attr_target_temperature_step = PRECISION_HALVES
        self._attr_precision = PRECISION_TENTHS
        self._attr_fan_modes = ['1', '2', '3', '4', '5', 'auto']
        self._attr_min_temp = 15
        self._attr_max_temp = 40

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperatures."""
        payload = {}
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            self._attr_target_temperature = kwargs.get(ATTR_TEMPERATURE)
            payload[str(IDX_TEMP_SET)] = int(kwargs.get(ATTR_TEMPERATURE) * 10)
        if (hvac_mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            self._attr_hvac_mode = hvac_mode
            payload[str(IDX_SWITCH)] = hvac_mode != HVACMode.OFF
            if hvac_mode != HVACMode.OFF:
                payload[str(IDX_MODE)] = ModeMap[hvac_mode]

        await self._device.set_dps(payload)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new operation mode."""
        payload = {}
        self._attr_hvac_mode = hvac_mode
        payload[str(IDX_SWITCH)] = hvac_mode != HVACMode.OFF
        if hvac_mode != HVACMode.OFF:
            payload[str(IDX_MODE)] = ModeMap[hvac_mode]

        await self._device.set_dps(payload)
    
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        self._attr_fan_mode = fan_mode
        payload = {
            IDX_LEVEL: fan_mode,
        }
        await self._device.set_dps(payload)

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self._device.set_dp(True, self._dp_id)
 
    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self._device.set_dp(False, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        switch = self.dps(IDX_SWITCH)
        mode = self.dps(IDX_MODE)
        temp_set = self.dps(IDX_TEMP_SET) / 10.0
        temp_cur = self.dps(IDX_TEMP_CURRENT) / 10.0
        level = self.dps(IDX_LEVEL)
        humidity = self.dps(IDX_HUMIDITY)

        if switch:
            self._attr_hvac_mode = find_mode_key(mode)
        else:
            self._attr_hvac_mode = HVACMode.OFF
        
        self._attr_target_temperature = temp_set
        self._attr_current_temperature = temp_cur
        self._attr_fan_mode = level
        self._attr_current_humidity = humidity
 
 
async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaClimate, flow_schema)
