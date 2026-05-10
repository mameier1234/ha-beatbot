"""Config Flow für Beatbot."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BeatbotAPI, BeatbotAuthError, BeatbotAPIError
from .const import CONF_COUNTRY_CODE, CONF_REGION, DOMAIN, REGIONS

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_REGION, default="EU"): vol.In(list(REGIONS.keys())),
        vol.Required(CONF_COUNTRY_CODE, default="DE"): str,
    }
)


class BeatbotConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            region = user_input[CONF_REGION]
            country_code = user_input[CONF_COUNTRY_CODE]

            await self.async_set_unique_id(email.lower())
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            api = BeatbotAPI(session, region)
            try:
                await api.login(email, password, country_code)
                token, refresh_token = api.get_tokens()
            except BeatbotAuthError:
                errors["base"] = "invalid_auth"
            except BeatbotAPIError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unbekannter Fehler beim Login")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=email,
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                        CONF_REGION: region,
                        CONF_COUNTRY_CODE: country_code,
                        "token": token,
                        "refresh_token": refresh_token,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
