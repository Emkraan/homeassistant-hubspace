"""Alarm control panel platform for the Hubspace integration.

This platform owns only the panel entity (arm/disarm/trigger). Zone and
keypad sensors are separate ``binary_sensor``/``select``/``number``
entities, fanned out generically by those platforms from
``bridge.security_systems_sensors`` / ``bridge.security_systems_keypads`` —
see binary_sensor.py.
"""

from __future__ import annotations


from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HubspaceCoordinator
from .entity import HubspaceEntity

CONTROLLER_ATTR = "security_systems"

ALARM_STATE_MAP = {
    "disarmed": AlarmControlPanelState.DISARMED,
    "arm-away": AlarmControlPanelState.ARMED_AWAY,
    "arm-stay": AlarmControlPanelState.ARMED_HOME,
    "arming-away": AlarmControlPanelState.ARMING,
    "arming-stay": AlarmControlPanelState.ARMING,
    "alarming-sos": AlarmControlPanelState.TRIGGERED,
    "alarming": AlarmControlPanelState.TRIGGERED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hubspace alarm control panels from a config entry."""
    coordinator: HubspaceCoordinator = entry.runtime_data
    async_add_entities(
        HubspaceAlarmPanel(coordinator, item.id)
        for item in coordinator.bridge.security_systems.items
    )


class HubspaceAlarmPanel(HubspaceEntity, AlarmControlPanelEntity):
    """Representation of a Hubspace security panel."""

    _attr_name = None
    _attr_code_format = CodeFormat.NUMBER
    _attr_code_arm_required = False

    def __init__(self, coordinator: HubspaceCoordinator, device_id: str) -> None:
        """Initialize the alarm panel."""
        super().__init__(coordinator, CONTROLLER_ATTR, device_id)

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return supported entity features."""
        features = AlarmControlPanelEntityFeature(0)
        if self.resource.supports_home:
            features |= AlarmControlPanelEntityFeature.ARM_HOME
        if self.resource.supports_away:
            features |= AlarmControlPanelEntityFeature.ARM_AWAY
        if self.resource.supports_trigger:
            features |= AlarmControlPanelEntityFeature.TRIGGER
        return features

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current alarm state."""
        alarm_state = self.resource.alarm_state
        if alarm_state is None or alarm_state.mode is None:
            return None
        return ALARM_STATE_MAP.get(alarm_state.mode)

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm the panel using the configured PIN."""
        if not code:
            raise HomeAssistantError("A disarm PIN is required for this panel")
        await self.coordinator.bridge.security_systems.disarm(self.device_id, int(code))

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Arm the panel in home/stay mode."""
        await self.coordinator.bridge.security_systems.arm_home(self.device_id)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm the panel in away mode."""
        await self.coordinator.bridge.security_systems.arm_away(self.device_id)

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        """Manually trigger the alarm siren."""
        await self.coordinator.bridge.security_systems.alarm_trigger(self.device_id)
