"""Beatbot Binärsensoren."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BeatbotCoordinator, BeatbotData


@dataclass(frozen=True, kw_only=True)
class BeatbotBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Any = None


BINARY_SENSOR_DESCRIPTIONS: tuple[BeatbotBinarySensorDescription, ...] = (
    BeatbotBinarySensorDescription(
        key="in_water",
        name="Im Wasser",
        value_fn=lambda data: data.state.in_water,
        icon="mdi:waves",
    ),
    BeatbotBinarySensorDescription(
        key="replenish_energy",
        name="Energie nachfüllen",
        value_fn=lambda data: data.state.replenish_energy,
        icon="mdi:battery-charging",
        entity_registry_enabled_default=False,
    ),
    BeatbotBinarySensorDescription(
        key="online",
        name="Online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda data: data.device.online,
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
        for description in BINARY_SENSOR_DESCRIPTIONS:
            entities.append(BeatbotBinarySensor(coordinator, description))
    async_add_entities(entities)


class BeatbotBinarySensor(CoordinatorEntity[BeatbotCoordinator], BinarySensorEntity):
    entity_description: BeatbotBinarySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BeatbotCoordinator,
        description: BeatbotBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        device = coordinator.device
        self._attr_unique_id = f"{device.device_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
        )

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None
