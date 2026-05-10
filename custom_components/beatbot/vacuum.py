"""Beatbot Staubsauger-Entität."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CMD_PAUSE,
    CMD_STANDBY,
    CMD_START_CLEANING,
    DOMAIN,
    FAN_SPEED_LIST,
    PIID_DOCK_CMD,
    PIID_SPEED_MODE,
    PIID_WORK_STATUS,
    SIID_MAIN,
    SPEED_BOOST,
    SPEED_NORMAL,
    WORK_STAT,
)
from .coordinator import BeatbotCoordinator

_LOGGER = logging.getLogger(__name__)

# workStat → HA VacuumActivity
_WORK_STAT_TO_ACTIVITY: dict[int, VacuumActivity] = {
    0: VacuumActivity.IDLE,       # standby
    1: VacuumActivity.RETURNING,  # goto_charge
    2: VacuumActivity.DOCKED,     # charging
    3: VacuumActivity.DOCKED,     # charge_done
    4: VacuumActivity.PAUSED,     # paused
    5: VacuumActivity.CLEANING,   # cleaning
    6: VacuumActivity.IDLE,       # sleep
    7: VacuumActivity.RETURNING,  # return_trip
    8: VacuumActivity.IDLE,       # clean_done
    9: VacuumActivity.CLEANING,   # remote_control
    10: VacuumActivity.IDLE,      # clean_wait
    11: VacuumActivity.IDLE,      # wifi_connect
    12: VacuumActivity.CLEANING,  # diving
    13: VacuumActivity.CLEANING,  # emerge
    14: VacuumActivity.RETURNING, # auto_dock
    15: VacuumActivity.RETURNING, # dock
    16: VacuumActivity.IDLE,      # finish_connect
    17: VacuumActivity.CLEANING,  # self_cleaning
    18: VacuumActivity.DOCKED,    # replenish_energy
    19: VacuumActivity.CLEANING,  # chase_light
    20: VacuumActivity.DOCKED,    # dock_done
}

SUPPORTED_FEATURES = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.BATTERY
    | VacuumEntityFeature.FAN_SPEED
    | VacuumEntityFeature.STATE
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinators: dict[str, BeatbotCoordinator] = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BeatbotVacuum(coordinator) for coordinator in coordinators.values()
    )


class BeatbotVacuum(CoordinatorEntity[BeatbotCoordinator], StateVacuumEntity):
    _attr_supported_features = SUPPORTED_FEATURES
    _attr_fan_speed_list = FAN_SPEED_LIST
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: BeatbotCoordinator) -> None:
        super().__init__(coordinator)
        device = coordinator.device
        self._attr_unique_id = device.device_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
            name=device.name,
            manufacturer="Beatbot",
            model="Pool Robot",
            serial_number=device.sn,
        )

    @property
    def activity(self) -> VacuumActivity | None:
        if self.coordinator.data is None:
            return None
        work_stat = self.coordinator.data.state.work_stat
        return _WORK_STAT_TO_ACTIVITY.get(work_stat, VacuumActivity.IDLE)

    @property
    def battery_level(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.state.battery

    @property
    def fan_speed(self) -> str | None:
        return None  # wird separat via Sensor bereitgestellt

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self.coordinator.data is None:
            return {}
        state = self.coordinator.data.state
        work_stat = state.work_stat
        return {
            "work_stat": work_stat,
            "work_stat_name": WORK_STAT.get(work_stat, "unknown"),
            "in_water": state.in_water,
            "replenish_energy": state.replenish_energy,
            "error_code": state.error_code,
        }

    @property
    def available(self) -> bool:
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.device.online

    async def async_start(self) -> None:
        await self._write(SIID_MAIN, PIID_WORK_STATUS, CMD_START_CLEANING)

    async def async_stop(self, **kwargs: Any) -> None:
        await self._write(SIID_MAIN, PIID_WORK_STATUS, CMD_STANDBY)

    async def async_pause(self) -> None:
        await self._write(SIID_MAIN, PIID_WORK_STATUS, CMD_PAUSE)

    async def async_return_to_base(self, **kwargs: Any) -> None:
        await self._write(SIID_MAIN, PIID_DOCK_CMD, 1)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        value = SPEED_BOOST if fan_speed == "boost" else SPEED_NORMAL
        await self._write(SIID_MAIN, PIID_SPEED_MODE, value)

    async def _write(self, siid: int, piid: int, value: Any) -> None:
        device = self.coordinator.device
        await self.coordinator.api.write_property(
            device.device_id, device.product_id, siid, piid, value
        )
        await self.coordinator.async_request_refresh()
