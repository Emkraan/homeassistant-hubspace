"""Constants for the Hubspace integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "hubspace"

CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_POLLING_INTERVAL: Final = "polling_interval"

DEFAULT_POLLING_INTERVAL: Final = 30
DEFAULT_DISCOVERY_INTERVAL: Final = 3600
# Afero's own API is rate-limited tightly enough that the upstream community
# integration had to add a hard floor after users self-DoSed their account by
# setting an aggressive polling interval. Enforced both in the options-flow
# schema and again as a clamp in the coordinator, in case a config entry is
# ever hand-edited.
MIN_POLLING_INTERVAL: Final = 2

CONF_DISCOVERY_INTERVAL: Final = "discovery_interval"
CONF_TOLERATE_STALE_DATA: Final = "tolerate_stale_data"
CONF_STALE_GRACE_MINUTES: Final = "stale_grace_minutes"

DEFAULT_TOLERATE_STALE_DATA: Final = True
DEFAULT_STALE_GRACE_MINUTES: Final = 10

# How many consecutive missed per-device state updates before that single
# device (not the whole account) is treated as unavailable. At the default
# 30s polling interval this is a 3 minute grace window for one flaky device.
PER_DEVICE_STALE_MULTIPLIER: Final = 6

PLATFORMS: Final = [
    "alarm_control_panel",
    "binary_sensor",
    "climate",
    "fan",
    "light",
    "lock",
    "number",
    "select",
    "sensor",
    "switch",
    "valve",
]
