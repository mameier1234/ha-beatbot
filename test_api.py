"""Schneller API-Test zum Debuggen."""
import asyncio
import base64
import hashlib
import hmac
import json
import os
import time

import aiohttp

ACCESS_ID = "qeswvwwtxpjfyefrpyrx"
ACCESS_KEY = "1359f00e558d4049ae6357a69a2cd831"
EMPTY_BODY_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
APP_VERSION = "4.0.0.1"

REGIONS = {
    "EU": "https://eu-iot.beatbot.com",
    "NA": "https://na-iot.beatbot.com",
    "CN": "https://cn-iot.beatbot.com",
}


def sha256_body(body: str) -> str:
    if not body:
        return EMPTY_BODY_HASH
    return hashlib.sha256(body.encode()).hexdigest().upper()


def string_to_sign(method: str, body: str, path: str) -> str:
    body_hash = sha256_body(body)
    return f"{method.upper()}\n{body_hash}\n\n{path}"


def sign(token: str, timestamp: str, sts: str) -> str:
    to_sign = ACCESS_ID + token + timestamp + sts
    return hmac.new(
        ACCESS_KEY.encode(),
        to_sign.encode(),
        hashlib.sha256,
    ).hexdigest().upper()


def aes_encrypt_password(password: str, salt: str = "BEATBOT") -> str:
    """AES-256-CBC encrypt wie KeyUtil.encrypt(password, 'BEATBOT') in der App."""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    key = hashlib.sha256(salt.encode()).digest()  # 32 Byte
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(password.encode("utf-8"), AES.block_size))
    return base64.b64encode(iv + ct).decode("utf-8")


def build_headers(method: str, path: str, body: str = "", token: str = "") -> dict:
    timestamp = str(int(time.time() * 1000))
    sts = string_to_sign(method, body, path)
    sig = sign(token, timestamp, sts)
    return {
        "client-id": ACCESS_ID,
        "timestamp": timestamp,
        "sign-method": "HMAC-SHA256",
        "x-sign": sig,
        "x-auth-tenant": "1",
        "x-platform": "Android",
        "x-app-version": APP_VERSION,
        "X-Device-Id": "homeassistant-test",
        "Accept-Language": "de",
        "User-Agent": f"BeatBot/{APP_VERSION} (Android; Android 12)",
        "Content-Type": "application/json",
        **({"x-auth-token": token} if token else {}),
    }


async def test_login_raw(region: str, body_dict: dict, label: str):
    """Sendet einen Login-Request mit dem gegebenen body_dict."""
    base = REGIONS[region]
    path = "/api/auth/login/email-password"
    body_str = json.dumps(body_dict, separators=(",", ":"))

    print(f"\n{'─'*60}")
    print(f"[{label}]  Region={region}")
    print(f"Body: {body_str[:120]}")

    headers = build_headers("POST", path, body_str)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            base + path,
            headers=headers,
            data=body_str,
        ) as resp:
            text = await resp.text()
            print(f"HTTP {resp.status}  →  {text[:300]}")
            return resp.status, text


async def main():
    import sys
    import json as _json

    if len(sys.argv) < 4:
        print("Nutzung: python test_api.py EMAIL PASSWORT LAND(z.B.49)")
        return

    email = sys.argv[1]
    raw_pw = sys.argv[2]
    country = sys.argv[3]

    md5_lower = hashlib.md5(raw_pw.encode()).hexdigest()
    md5_upper = md5_lower.upper()
    sha256_lower = hashlib.sha256(raw_pw.encode()).hexdigest()
    aes_pw = aes_encrypt_password(raw_pw)

    # Verschiedene Kombinationen: Feldname × Passwort-Format
    # Zuerst EU testen, dann NA
    test_cases = [
        # (Feldname, Passwort-Wert, Beschreibung)
        ("password",          raw_pw,      "password / plaintext"),
        ("password",          aes_pw,      "password / AES-CBC(BEATBOT)"),
        ("password",          md5_lower,   "password / MD5-lower"),
        ("password",          md5_upper,   "password / MD5-upper"),
        ("password",          sha256_lower,"password / SHA256-lower"),
        ("passwd",            raw_pw,      "passwd   / plaintext"),
        ("passwd",            md5_lower,   "passwd   / MD5-lower"),
        ("passwd",            aes_pw,      "passwd   / AES-CBC(BEATBOT)"),
        ("pwd",               raw_pw,      "pwd      / plaintext"),
        ("encryptedPassword", raw_pw,      "encryptedPassword / plaintext"),
        ("encryptedPassword", aes_pw,      "encryptedPassword / AES-CBC(BEATBOT)"),
        ("userPassword",      raw_pw,      "userPassword / plaintext"),
    ]

    print(f"\n{'='*60}")
    print(f"Teste {len(test_cases)} Kombinationen für Region EU und NA")
    print(f"Email: {email}  Land: {country}")

    for region in ["EU", "NA"]:
        print(f"\n{'='*60}\nRegion: {region}")
        for field, pw_val, desc in test_cases:
            body = {"email": email, field: pw_val, "countryCode": country}
            status, text = await test_login_raw(region, body, desc)
            try:
                resp = _json.loads(text)
                code = resp.get("code")
                if status == 200 and code == 0:
                    token = str(resp.get("data", {}).get("token", ""))[:30]
                    print(f"\n{'='*60}")
                    print(f"✅ ERFOLG! Region={region}, {desc}")
                    print(f"   Token: {token}...")
                    return
            except Exception:
                pass


asyncio.run(main())
