"""Switch platform for the Hubspace integration.

A single Afero switch device can expose more than one independently
toggleable element (e.g. a multi-outlet power strip), keyed by
``functionInstance``. One HA entity is created per instance.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HubspaceCoordinator
from .entity import HubspaceEntity

CONTROLLER_ATTR = "switches"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hubspace switches from a config entry."""
    coordinator: HubspaceCoordinator = entry.runtime_data
    entities = [
        HubspaceSwitch(coordinator, item.id, instance)
        for item in coordinator.bridge.switches.items
        for instance in item.on
    ]
    async_add_entities(entities)


class HubspaceSwitch(HubspaceEntity, SwitchEntity):
    """Representation of a single toggleable element of a Hubspace switch."""

    def __init__(
        self, coordinator: HubspaceCoordinator, device_id: str, instance: str | None
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, CONTROLLER_ATTR, device_id, instance or "default")
        self.instance = instance
        self._attr_name = instance.replace("-", " ").title() if instance else None

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.resource.on[self.instance].on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.bridge.switches.turn_on(
            self.device_id, instance=self.instance
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.bridge.switches.turn_off(
            self.device_id, instance=self.instance
        )
