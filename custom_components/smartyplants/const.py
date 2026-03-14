"""Constants for the SmartyPlants integration."""

from typing import Final

DOMAIN: Final = "smartyplants"

API_BASE_URL: Final = "https://api.smartyplants.ai/api"

CONF_ACCESS_TOKEN: Final = "access_token"
CONF_REFRESH_TOKEN: Final = "refresh_token"

OPT_SCAN_INTERVAL: Final = "scan_interval"
OPT_SHOW_STATUS_SENSORS: Final = "show_status_sensors"

DEFAULT_SCAN_INTERVAL: Final = 15
MIN_SCAN_INTERVAL: Final = 5

READING_STATUS_OPTIONS: Final = [
    "optimal",
    "low",
    "high",
    "non_optimal_low",
    "non_optimal_high",
    "dangerously_low",
]
