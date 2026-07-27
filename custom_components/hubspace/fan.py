"""Fan platform for the Hubspace integration.

Only ``bridge.fans`` (ceiling/standalone fans) map to HA's ``fan`` domain.
Exhaust fans expose their on/off toggle, speed, and light as separate
``switch``/``fan``/``light`` resources on Afero's side (aioafero's own
``exhaust_fan_callback`` splits them out) — their remaining settings
(auto-off timer, motion sensitivity, humidity threshold) surface generically
through the ``number``/``select``/``binary_sensor`` platforms.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HubspaceCoordinator
from .entity import HubspaceEntity

CONTROLLER_ATTR = "fans"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hubspace fans from a config entry."""
    coordinator: HubspaceCoordinator = entry.runtime_data
    async_add_entities(
        HubspaceFan(coordinator, item.id) for item in coordinator.bridge.fans.items
    )


class HubspaceFan(HubspaceEntity, FanEntity):
    """Representation of a Hubspace fan."""

    _attr_name = None

    def __init__(self, coordinator: HubspaceCoordinator, device_id: str) -> None:
        """Initialize the fan."""
        super().__init__(coordinator, CONTROLLER_ATTR, device_id)

    @property
    def _speed_count(self) -> int:
        speed = self.resource.speed
        return len(speed.speeds) if speed and speed.speeds else 0

    @property
    def supported_features(self) -> FanEntityFeature:
        """Return supported entity features."""
        features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if self.resource.supports_speed:
            features |= FanEntityFeature.SET_SPEED
        if self.resource.supports_direction:
            features |= FanEntityFeature.DIRECTION
        if self.resource.supports_presets:
            features |= FanEntityFeature.PRESET_MODE
        return features

    @property
    def is_on(self) -> bool:
        """Return true if the fan is on."""
        return self.resource.is_on

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if not self.resource.supports_speed:
            return None
        return self.resource.current_speed

    @property
    def speed_count(self) -> int:
        """Return the number of discrete speed steps."""
        return self._speed_count or 1

    @property
    def current_direction(self) -> str | None:
        """Return the current fan direction."""
        if not self.resource.supports_direction:
            return None
        return "forward" if self.resource.current_direction else "reverse"

    @property
    def preset_modes(self) -> list[str] | None:
        """Return supported preset modes."""
        if not self.resource.supports_presets:
            return None
        return ["comfort-breeze"]

    @property
    def preset_mode(self) -> str | None:
        """Return the currently active preset."""
        return self.resource.current_preset

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan, optionally at a given speed or preset."""
        controller = self.coordinator.bridge.fans
        if preset_mode is not None:
            await controller.set_preset(self.device_id, True)
            return
        if percentage is not None:
            await controller.set_speed(self.device_id, percentage)
            return
        await controller.turn_on(self.device_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self.coordinator.bridge.fans.turn_off(self.device_id)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed percentage."""
        if percentage == 0:
            await self.async_turn_off()
            return
        await self.coordinator.bridge.fans.set_speed(self.device_id, percentage)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the fan preset mode."""
        await self.coordinator.bridge.fans.set_preset(self.device_id, True)

    async def async_set_direction(self, direction: str) -> None:
        """Set the fan rotation direction."""
        await self.coordinator.bridge.fans.set_direction(
            self.device_id, direction == "forward"
        )
