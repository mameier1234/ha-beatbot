"""Beatbot Pool Robot Integration für Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BeatbotAPI, BeatbotAPIError, BeatbotAuthError
from .const import CONF_COUNTRY_CODE, CONF_REGION, DOMAIN
from .coordinator import BeatbotCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.VACUUM, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = BeatbotAPI(session, entry.data[CONF_REGION])
    api.set_tokens(entry.data.get("token", ""), entry.data.get("refresh_token", ""))

    # Bei abgelaufenem Token neu einloggen
    try:
        devices = await api.get_devices()
    except (BeatbotAuthError, BeatbotAPIError):
        try:
            await api.login(
                entry.data[CONF_EMAIL],
                entry.data[CONF_PASSWORD],
                entry.data[CONF_COUNTRY_CODE],
            )
            token, refresh_token = api.get_tokens()
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, "token": token, "refresh_token": refresh_token}
            )
            devices = await api.get_devices()
        except Exception as err:
            _LOGGER.error("Login fehlgeschlagen: %s", err)
            return False

    coordinators: dict[str, BeatbotCoordinator] = {}
    for device in devices:
        coordinator = BeatbotCoordinator(hass, api, device)
        await coordinator.async_config_entry_first_refresh()
        coordinators[device.device_id] = coordinator

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
