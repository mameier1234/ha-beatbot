"""Beatbot API-Client mit HMAC-SHA256-Signierung."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import (
    ACCESS_ID,
    ACCESS_KEY,
    EMPTY_BODY_HASH,
    REGIONS,
    X_AUTH_TENANT,
)

_LOGGER = logging.getLogger(__name__)

APP_VERSION = "4.0.0.1"
DEVICE_ID = "homeassistant-beatbot-integration"


@dataclass
class BeatbotDevice:
    device_id: str
    name: str
    online: bool
    product_id: str
    sn: str


@dataclass
class BeatbotDeviceState:
    work_stat: int
    battery: int | None
    in_water: bool | None
    replenish_energy: bool | None
    error_code: int | None


class BeatbotAuthError(Exception):
    pass


class BeatbotAPIError(Exception):
    pass


class BeatbotAPI:
    def __init__(self, session: aiohttp.ClientSession, region: str) -> None:
        self._session = session
        self._base_url = f"https://{REGIONS[region]}"
        self._token: str = ""
        self._refresh_token: str = ""

    def _sha256_body(self, body: str) -> str:
        if not body:
            return EMPTY_BODY_HASH
        return hashlib.sha256(body.encode("utf-8")).hexdigest().upper()

    def _string_to_sign(self, method: str, body: str, path: str, params: dict | None = None) -> str:
        if params:
            sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            path_with_params = f"{path}?{sorted_params}"
        else:
            path_with_params = path
        body_hash = self._sha256_body(body)
        return f"{method.upper()}\n{body_hash}\n\n{path_with_params}"

    def _sign(self, timestamp: str, string_to_sign: str) -> str:
        to_sign = ACCESS_ID + self._token + timestamp + string_to_sign
        return hmac.new(
            ACCESS_KEY.encode("utf-8"),
            to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()

    def _build_headers(self, method: str, path: str, body: str = "", params: dict | None = None) -> dict:
        timestamp = str(int(time.time() * 1000))
        string_to_sign = self._string_to_sign(method, body, path, params)
        signature = self._sign(timestamp, string_to_sign)
        headers = {
            "client-id": ACCESS_ID,
            "timestamp": timestamp,
            "sign-method": "HMAC-SHA256",
            "x-sign": signature,
            "x-auth-tenant": X_AUTH_TENANT,
            "x-platform": "Android",
            "x-app-version": APP_VERSION,
            "X-Device-Id": DEVICE_ID,
            "Accept-Language": "en",
            "User-Agent": f"BeatBot/{APP_VERSION} (Android; Android 12)",
            "Content-Type": "application/json",
        }
        if self._token:
            headers["x-auth-token"] = self._token
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        params: dict | None = None,
        retry_on_401: bool = True,
    ) -> Any:
        body_str = json.dumps(body, separators=(",", ":")) if body else ""
        headers = self._build_headers(method, path, body_str, params)
        url = self._base_url + path
        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                data=body_str if body_str else None,
                params=params,
            ) as resp:
                if resp.status == 401 and retry_on_401:
                    if await self._refresh_token_request():
                        return await self._request(method, path, body, params, retry_on_401=False)
                    raise BeatbotAuthError("Token abgelaufen – bitte neu einloggen")
                data = await resp.json()
                if resp.status >= 400:
                    raise BeatbotAPIError(f"HTTP {resp.status}: {data}")
                return data
        except aiohttp.ClientError as err:
            raise BeatbotAPIError(f"Verbindungsfehler: {err}") from err

    async def login(self, email: str, password: str, country_code: str) -> None:
        path = "/api/auth/login/email-password"
        body = {"email": email, "password": password, "countryCode": country_code}
        data = await self._request("POST", path, body=body)
        if "data" not in data:
            raise BeatbotAuthError(f"Login fehlgeschlagen: {data}")
        self._token = data["data"]["token"]
        self._refresh_token = data["data"]["refreshToken"]

    async def _refresh_token_request(self) -> bool:
        if not self._refresh_token:
            return False
        path = "/api/auth/refresh-token"
        params = {"refresh_token": self._refresh_token}
        try:
            data = await self._request("GET", path, params=params, retry_on_401=False)
            if "data" in data:
                self._token = data["data"]["token"]
                self._refresh_token = data["data"]["refreshToken"]
                return True
        except Exception as err:
            _LOGGER.warning("Token-Erneuerung fehlgeschlagen: %s", err)
        return False

    def set_tokens(self, token: str, refresh_token: str) -> None:
        self._token = token
        self._refresh_token = refresh_token

    def get_tokens(self) -> tuple[str, str]:
        return self._token, self._refresh_token

    async def get_devices(self) -> list[BeatbotDevice]:
        data = await self._request("GET", "/api/devices")
        devices = []
        for item in data.get("data", []):
            product = item.get("product") or {}
            devices.append(BeatbotDevice(
                device_id=item["deviceId"],
                name=item.get("name", item["deviceId"]),
                online=item.get("online", 0) == 1,
                product_id=product.get("productId", ""),
                sn=item.get("sn", ""),
            ))
        return devices

    async def get_device_properties(
        self, device_id: str, properties: list[dict]
    ) -> list[dict]:
        """Liest Geräteeigenschaften via POST /api/devices/{id}/properties."""
        path = f"/api/devices/{urllib.parse.quote(device_id)}/properties"
        body = {"properties": properties}
        data = await self._request("POST", path, body=body)
        return data.get("data", [])

    async def write_property(
        self, device_id: str, product_id: str, siid: int, piid: int, value: Any
    ) -> None:
        """Schreibt eine Geräteeigenschaft (Steuerbefehl)."""
        path = "/api/command/property/write"
        body = {
            "deviceId": device_id,
            "productId": product_id,
            "data": {
                "method": "set_properties",
                "params": [{"siid": siid, "piid": piid, "value": value}],
            },
        }
        await self._request("POST", path, body=body)

    async def get_device_state(self, device_id: str) -> BeatbotDeviceState:
        """Liest alle relevanten Statuspunkte in einer Anfrage."""
        from .const import (
            PIID_BATTERY,
            PIID_ERROR_CODE,
            PIID_IN_WATER,
            PIID_REPLENISH_ENERGY,
            PIID_WORK_STATUS,
            SIID_DEVICE,
            SIID_MAIN,
        )
        props_to_read = [
            {"siid": SIID_MAIN, "piid": PIID_WORK_STATUS},
            {"siid": SIID_MAIN, "piid": PIID_BATTERY},
            {"siid": SIID_DEVICE, "piid": PIID_IN_WATER},
            {"siid": SIID_DEVICE, "piid": PIID_REPLENISH_ENERGY},
            {"siid": SIID_DEVICE, "piid": PIID_ERROR_CODE},
        ]
        results = await self.get_device_properties(device_id, props_to_read)

        def _find(siid: int, piid: int) -> Any:
            for r in results:
                if r.get("siid") == siid and r.get("piid") == piid:
                    return r.get("value")
            return None

        work_stat = _find(SIID_MAIN, PIID_WORK_STATUS)
        battery = _find(SIID_MAIN, PIID_BATTERY)
        in_water = _find(SIID_DEVICE, PIID_IN_WATER)
        replenish = _find(SIID_DEVICE, PIID_REPLENISH_ENERGY)
        error_code = _find(SIID_DEVICE, PIID_ERROR_CODE)

        return BeatbotDeviceState(
            work_stat=int(work_stat) if work_stat is not None else 0,
            battery=int(battery) if battery is not None else None,
            in_water=bool(in_water) if in_water is not None else None,
            replenish_energy=bool(replenish) if replenish is not None else None,
            error_code=int(error_code) if error_code is not None else None,
        )
