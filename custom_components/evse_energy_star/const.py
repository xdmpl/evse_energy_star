DOMAIN = "evse_energy_star"
DEFAULT_SCAN_INTERVAL = 30
TITLE = "EVSE Energy Star"

# Повертаємо КЛЮЧІ, а не тексти
STATUS_MAP = {
    0: "no_data",
    6: "charging",
    9: "waiting",
    12: "ready",
    13: "delayed_start",
    14: "overcurrent",
    15: "overvoltage",
    16: "leakage",
    17: "station_error",
    18: "overtemperature",
    19: "locked",
    20: "no_ground",
    21: "plug_overheat",
    22: "undervoltage",
}
