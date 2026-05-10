"""DataUpdateCoordinator für Beatbot."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BeatbotAPI, BeatbotAPIError, BeatbotAuthError, BeatbotDevice, BeatbotDeviceState
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class BeatbotData:
    device: BeatbotDevice
    state: BeatbotDeviceState


class BeatbotCoordinator(DataUpdateCoordinator[BeatbotData]):
    def __init__(
        self,
        hass: HomeAssistant,
        api: BeatbotAPI,
        device: BeatbotDevice,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device.device_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.device = device

    async def _async_update_data(self) -> BeatbotData:
        try:
            state = await self.api.get_device_state(self.device.device_id)
            # Gerätestatus (online/offline) ebenfalls aktualisieren
            devices = await self.api.get_devices()
            for dev in devices:
                if dev.device_id == self.device.device_id:
                    self.device = dev
                    break
            return BeatbotData(device=self.device, state=state)
        except BeatbotAuthError as err:
            raise UpdateFailed(f"Authentifizierungsfehler: {err}") from err
        except BeatbotAPIError as err:
            raise UpdateFailed(f"API-Fehler: {err}") from err
