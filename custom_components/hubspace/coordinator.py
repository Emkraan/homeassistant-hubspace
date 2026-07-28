"""DataUpdateCoordinator for the Hubspace integration.

aioafero manages its own internal polling loops (a fast state poll and a slow
discovery poll) and pushes events to subscribers rather than being polled on
a timer by Home Assistant. This coordinator therefore runs in *push* mode
(``update_interval=None``): it exists to reuse HA's ``CoordinatorEntity``
plumbing (listener dispatch, ``last_update_success``, unload/reload
lifecycle), not to drive its own update loop. All state changes flow through
a single Afero event-stream subscription that calls ``async_set_updated_data``
/ ``async_set_update_error`` directly.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .aioafero.errors import InvalidAuth
from .aioafero.types import EventType
from .aioafero.v1 import AferoBridgeV1
from .const import (
    CONF_DISCOVERY_INTERVAL,
    CONF_POLLING_INTERVAL,
    CONF_REFRESH_TOKEN,
    CONF_STALE_GRACE_MINUTES,
    CONF_TOLERATE_STALE_DATA,
    DEFAULT_DISCOVERY_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_STALE_GRACE_MINUTES,
    DEFAULT_TOLERATE_STALE_DATA,
    DOMAIN,
    MIN_POLLING_INTERVAL,
    PER_DEVICE_STALE_MULTIPLIER,
    STALE_DEVICE_CHECK_INTERVAL_SECONDS,
    STALE_DEVICE_DISCOVERY_COOLDOWN_MINUTES,
    STALE_DEVICE_RELOAD_THRESHOLD_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

# How long to wait for aioafero's first discovery+state poll to complete
# before giving up and asking HA to retry setup later.
FIRST_POLL_TIMEOUT = 30


class HubspaceCoordinator(DataUpdateCoordinator[None]):
    """Owns the aioafero bridge plus per-device and whole-account availability."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator and construct (but do not start) the bridge."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self._entry = entry
        polling_interval = max(
            entry.options.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL),
            MIN_POLLING_INTERVAL,
        )
        self.bridge = AferoBridgeV1(
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
            session=async_get_clientsession(hass),
            polling_interval=polling_interval,
            discovery_interval=entry.options.get(
                CONF_DISCOVERY_INTERVAL, DEFAULT_DISCOVERY_INTERVAL
            ),
            client_name="home-assistant-emkraan",
        )
        self.tolerate_stale_data: bool = entry.options.get(
            CONF_TOLERATE_STALE_DATA, DEFAULT_TOLERATE_STALE_DATA
        )
        self.stale_grace = timedelta(
            minutes=entry.options.get(
                CONF_STALE_GRACE_MINUTES, DEFAULT_STALE_GRACE_MINUTES
            )
        )
        self._last_seen: dict[str, datetime] = {}
        self._deleted_ids: set[str] = set()
        self._disconnected_since: datetime | None = None
        self._unsub_bridge_events: callable | None = None
        self._unsub_stale_check: callable | None = None
        self._unsub_stale_watchdog: callable | None = None
        self._stale_since: dict[str, datetime] = {}
        self._last_discovery_recovery: datetime | None = None

    async def _async_setup(self) -> None:
        """Start the bridge and wait for its first poll. Called once by HA."""
        self._unsub_bridge_events = self.bridge.events.subscribe(
            self._handle_bridge_event
        )
        self._unsub_stale_watchdog = async_track_time_interval(
            self.hass,
            self._async_check_stale_devices,
            timedelta(seconds=STALE_DEVICE_CHECK_INTERVAL_SECONDS),
        )
        try:
            await self.bridge.initialize()
            await asyncio.wait_for(
                self.bridge.events.wait_for_first_poll(), timeout=FIRST_POLL_TIMEOUT
            )
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed(
                "Hubspace credentials are no longer valid"
            ) from err
        except TimeoutError as err:
            raise ConfigEntryNotReady(
                "Timed out waiting for the initial Hubspace poll"
            ) from err
        if not self.bridge.events.connected:
            raise ConfigEntryNotReady("Could not connect to the Hubspace cloud")

    async def _async_update_data(self) -> None:
        """No-op: HA calls this once via async_config_entry_first_refresh().

        Real state flows through _handle_bridge_event from here on; this
        coordinator never re-polls on its own timer (update_interval=None).
        """
        return None

    async def async_shutdown(self) -> None:
        """Unsubscribe and close the bridge session."""
        await super().async_shutdown()
        if self._unsub_stale_check is not None:
            self._unsub_stale_check()
        if self._unsub_stale_watchdog is not None:
            self._unsub_stale_watchdog()
        if self._unsub_bridge_events is not None:
            self._unsub_bridge_events()
        await self.bridge.close()

    def device_available(self, device_id: str) -> bool:
        """Return whether a specific device has reported in recently.

        Distinct from ``last_update_success`` (whole-account health): a
        shared cloud hiccup doesn't have to take every device down, but one
        device that Afero silently stops returning (Wi-Fi drop, or the
        Home-Depot "Myko+" migration vanishing it from the API entirely)
        should go unavailable on its own.
        """
        if device_id in self._deleted_ids:
            return False
        last_seen = self._last_seen.get(device_id)
        if last_seen is None:
            return False
        max_age = timedelta(
            seconds=self.bridge.events.polling_interval * PER_DEVICE_STALE_MULTIPLIER
        )
        return (dt_util.utcnow() - last_seen) <= max_age

    async def _async_check_stale_devices(self, _now) -> None:
        """Self-heal a device that stopped responding after a Wi-Fi/power drop.

        Confirmed live: a device can reconnect to Wi-Fi (and work fine in the
        official Hubspace app) while Afero's own state-poll endpoint keeps
        silently failing to return fresh data for that one device -- every
        other device polls fine, so this never trips the whole-account
        DISCONNECTED path. Previously the only recovery was a manual
        integration reload, which works only because it forces a brand new
        discovery pass. This does that automatically: a cheap out-of-band
        discovery refresh first, escalating to a full config-entry reload
        (the same fix, automated) only if a device is still stale well after
        repeated refreshes.
        """
        now = dt_util.utcnow()
        stale_ids = [
            device_id
            for device_id in self._last_seen
            if device_id not in self._deleted_ids
            and not self.device_available(device_id)
        ]
        self._stale_since = {
            device_id: self._stale_since.get(device_id, now) for device_id in stale_ids
        }
        if not stale_ids:
            return

        oldest_stale = min(self._stale_since.values())
        if now - oldest_stale >= timedelta(
            minutes=STALE_DEVICE_RELOAD_THRESHOLD_MINUTES
        ):
            _LOGGER.warning(
                "%d device(s) still unresponsive after %d minutes despite "
                "discovery refreshes; reloading the integration to force a "
                "full resync",
                len(stale_ids),
                STALE_DEVICE_RELOAD_THRESHOLD_MINUTES,
            )
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self._entry.entry_id)
            )
            return

        if self._last_discovery_recovery is not None and now - (
            self._last_discovery_recovery
        ) < timedelta(minutes=STALE_DEVICE_DISCOVERY_COOLDOWN_MINUTES):
            return
        self._last_discovery_recovery = now
        _LOGGER.info(
            "%d device(s) stale; forcing an out-of-band discovery refresh",
            len(stale_ids),
        )
        try:
            await self.bridge.events.perform_discovery_poll()
        except Exception as err:  # noqa: BLE001 - best-effort recovery attempt
            _LOGGER.debug("Stale-device discovery refresh attempt failed: %s", err)

    @callback
    def _handle_bridge_event(self, event_type: EventType, data) -> None:
        """Translate an aioafero event-stream event into coordinator state."""
        if event_type == EventType.INVALID_AUTH:
            _LOGGER.warning("Hubspace reported invalid auth; starting reauth")
            self._entry.async_start_reauth(self.hass)
            return
        if event_type == EventType.DISCONNECTED:
            self._handle_disconnected()
            return
        if event_type in (EventType.CONNECTED, EventType.RECONNECTED):
            self._handle_reconnected()
            return
        if event_type == EventType.RESOURCE_DELETED:
            device_id = data.get("device_id") if data else None
            if device_id:
                self._deleted_ids.add(device_id)
                self._last_seen.pop(device_id, None)
                self.async_update_listeners()
            return
        if event_type in (
            EventType.RESOURCE_ADDED,
            EventType.RESOURCE_UPDATED,
            EventType.RESOURCE_UPDATE_RESPONSE,
        ):
            device_id = data.get("device_id") if data else None
            if device_id:
                self._last_seen[device_id] = dt_util.utcnow()
                self._deleted_ids.discard(device_id)
            self.async_update_listeners()

    def _handle_disconnected(self) -> None:
        if self._disconnected_since is None:
            self._disconnected_since = dt_util.utcnow()
        if not self.tolerate_stale_data:
            self.async_set_update_error(UpdateFailed("Hubspace cloud connection lost"))
            return
        if self._unsub_stale_check is None:
            self._unsub_stale_check = async_call_later(
                self.hass, self.stale_grace, self._check_still_disconnected
            )

    @callback
    def _check_still_disconnected(self, _now) -> None:
        self._unsub_stale_check = None
        if self._disconnected_since is not None:
            self.async_set_update_error(
                UpdateFailed(
                    "Hubspace cloud connection has been down for longer than "
                    "the configured stale-data grace period"
                )
            )

    def _handle_reconnected(self) -> None:
        self._disconnected_since = None
        if self._unsub_stale_check is not None:
            self._unsub_stale_check()
            self._unsub_stale_check = None
        if not self.last_update_success:
            self.async_set_updated_data(None)
