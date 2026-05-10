# Beatbot Pool Robot – Home Assistant Integration

Inoffizielle Home Assistant Custom Component für den **Beatbot Pool Roboter**.

## Features

- **Staubsauger-Entität** mit Start, Stop, Pause, Zur Dockstation
- **Lüfterstufe** (Normal / Boost)
- **Sensoren**: Batteriestand, Status-Text, Status-Code, Fehlercode
- **Binärsensoren**: Im Wasser, Online-Status, Energie nachfüllen
- Automatischer Token-Refresh
- 21 Roboter-Zustände werden korrekt auf HA-States gemappt

## Installation

1. Ordner `custom_components/beatbot/` in dein HA-Konfigurationsverzeichnis kopieren:
   ```
   config/custom_components/beatbot/
   ```
2. Home Assistant neu starten
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen → "Beatbot"**
4. E-Mail, Passwort, Region (NA/EU/CN) und Ländercode eingeben

## Entitäten

| Entität | Typ | Beschreibung |
|---|---|---|
| `vacuum.beatbot_*` | Vacuum | Hauptsteuerung des Roboters |
| `sensor.*_batterie` | Sensor | Ladestand in % |
| `sensor.*_status` | Sensor | Aktueller Status als Text |
| `binary_sensor.*_im_wasser` | Binary Sensor | Ob der Roboter im Wasser ist |
| `binary_sensor.*_online` | Binary Sensor | Verbindungsstatus |

## Roboter-Zustände

| Code | Name | HA-State |
|---|---|---|
| 0 | Standby | idle |
| 1 | Zur Ladestation | returning |
| 2 | Lädt | docked |
| 3 | Geladen | docked |
| 4 | Pausiert | paused |
| 5 | Reinigt | cleaning |
| 7 | Rückkehr | returning |
| 12 | Taucht | cleaning |
| 17 | Selbstreinigung | cleaning |
| 20 | Dockstation fertig | docked |

## Hinweise

- Pollt alle 30 Sekunden (konfigurierbar in `const.py` via `DEFAULT_SCAN_INTERVAL`)
- Basiert auf der offiziellen Beatbot-App API (reverse engineered)
- Getestet mit Region **EU** (`eu-iot.beatbot.com`)

## Lizenz

MIT
