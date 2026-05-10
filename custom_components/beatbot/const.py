DOMAIN = "beatbot"

CONF_REGION = "region"
CONF_COUNTRY_CODE = "country_code"

REGIONS = {
    "NA": "na-iot.beatbot.com",
    "EU": "eu-iot.beatbot.com",
    "CN": "cn-iot.beatbot.com",
}

ACCESS_ID = "qeswvwwtxpjfyefrpyrx"
ACCESS_KEY = "1359f00e558d4049ae6357a69a2cd831"
X_AUTH_TENANT = "1"
EMPTY_BODY_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

DEFAULT_SCAN_INTERVAL = 30

# SIID/PIID Mapping
SIID_MAIN = 1
PIID_WORK_STATUS = 4
PIID_BATTERY = 5
PIID_CLEAN_MODE = 3
PIID_SPEED_MODE = 8
PIID_DOCK_CMD = 9

SIID_DEVICE = 2
PIID_IN_WATER = 28
PIID_REPLENISH_ENERGY = 51
PIID_ERROR_CODE = 26

# workStat Werte → Name
WORK_STAT = {
    0: "standby",
    1: "goto_charge",
    2: "charging",
    3: "charge_done",
    4: "paused",
    5: "cleaning",
    6: "sleep",
    7: "return_trip",
    8: "clean_done",
    9: "remote_control",
    10: "clean_wait",
    11: "wifi_connect",
    12: "diving",
    13: "emerge",
    14: "auto_dock",
    15: "dock",
    16: "finish_connect",
    17: "self_cleaning",
    18: "replenish_energy",
    19: "chase_light",
    20: "dock_done",
}

# Befehle für PIID_WORK_STATUS
CMD_START_CLEANING = 5
CMD_PAUSE = 4
CMD_STANDBY = 0

SPEED_NORMAL = 0
SPEED_BOOST = 1

FAN_SPEED_LIST = ["normal", "boost"]
