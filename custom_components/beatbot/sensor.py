"""Beatbot Sensoren."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, WORK_STAT
from .coordinator import BeatbotCoordinator, BeatbotData


@dataclass(frozen=True, kw_only=True)
class BeatbotSensorDescription(SensorEntityDescription):
    value_fn: Any = None


SENSOR_DESCRIPTIONS: tuple[BeatbotSensorDescription, ...] = (
    BeatbotSensorDescription(
        key="battery",
        name="Batterie",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.state.battery,
    ),
    BeatbotSensorDescription(
        key="status",
        name="Status",
        value_fn=lambda data: WORK_STAT.get(data.state.work_stat, "unknown"),
        icon="mdi:robot",
    ),
    BeatbotSensorDescription(
        key="work_stat",
        name="Status-Code",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.state.work_stat,
        icon="mdi:numeric",
        entity_registry_enabled_default=False,
    ),
    BeatbotSensorDescription(
        key="error_code",
        name="Fehlercode",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.state.error_code,
        icon="mdi:alert-circle",
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinators: dict[str, BeatbotCoordinator] = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for coordinator in coordinators.values():
        for description in SENSOR_DESCRIPTIONS:
            entities.append(BeatbotSensor(coordinator, description))
    async_add_entities(entities)


class BeatbotSensor(CoordinatorEntity[BeatbotCoordinator], SensorEntity):
    entity_description: BeatbotSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BeatbotCoordinator,
        description: BeatbotSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        device = coordinator.device
        self._attr_unique_id = f"{device.device_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
        )

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.device.online
