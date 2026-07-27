"""Valve platform for the Hubspace integration.

Like switches, a single Afero valve/water-timer device can expose more than
one independently controllable zone, keyed by ``functionInstance``.
"""

from __future__ import annotations


from homeassistant.components.valve import ValveEntity, ValveEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HubspaceCoordinator
from .entity import HubspaceEntity

CONTROLLER_ATTR = "valves"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hubspace valves from a config entry."""
    coordinator: HubspaceCoordinator = entry.runtime_data
    entities = [
        HubspaceValve(coordinator, item.id, instance)
        for item in coordinator.bridge.valves.items
        for instance in item.open
    ]
    async_add_entities(entities)


class HubspaceValve(HubspaceEntity, ValveEntity):
    """Representation of a single zone of a Hubspace valve."""

    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
    _attr_reports_position = False

    def __init__(
        self, coordinator: HubspaceCoordinator, device_id: str, instance: str | None
    ) -> None:
        """Initialize the valve."""
        super().__init__(coordinator, CONTROLLER_ATTR, device_id, instance or "default")
        self.instance = instance
        self._attr_name = instance.replace("-", " ").title() if instance else None

    @property
    def is_closed(self) -> bool:
        """Return true if the valve is closed."""
        return not self.resource.open[self.instance].open

    async def async_open_valve(self) -> None:
        """Open the valve."""
        await self.coordinator.bridge.valves.turn_on(
            self.device_id, instance=self.instance
        )

    async def async_close_valve(self) -> None:
        """Close the valve."""
        await self.coordinator.bridge.valves.turn_off(
            self.device_id, instance=self.instance
        )
