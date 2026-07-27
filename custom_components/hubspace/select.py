"""Select platform for the Hubspace integration.

Walks every initialized controller's generic ``selects`` dict, same approach
as number.py — every controller that populates ``ITEM_SELECTS`` accepts
writing it back via
``set_state(device_id, selects={(functionClass, functionInstance): value})``.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HubspaceCoordinator
from .entity import HubspaceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hubspace selects from every controller's generic selects dict."""
    coordinator: HubspaceCoordinator = entry.runtime_data
    entities = [
        HubspaceSelect(coordinator, controller_attr, item.id, key)
        for controller_attr, controller in coordinator.bridge.controllers_by_name.items()
        for item in controller.items
        for key in item.selects
    ]
    async_add_entities(entities)


class HubspaceSelect(HubspaceEntity, SelectEntity):
    """A single generic option picker on a Hubspace resource."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: HubspaceCoordinator,
        controller_attr: str,
        device_id: str,
        key: tuple[str, str | None],
    ) -> None:
        """Initialize the select."""
        unique_suffix = f"{key[0]}_{key[1] or 'default'}"
        super().__init__(coordinator, controller_attr, device_id, unique_suffix)
        self.key = key
        self._attr_name = self.resource.selects[key].name

    @property
    def options(self) -> list[str]:
        """Return the available options."""
        return sorted(self.resource.selects[self.key].selects)

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        return self.resource.selects[self.key].selected

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        controller = getattr(self.coordinator.bridge, self._controller_attr)
        await controller.set_state(self.device_id, selects={self.key: option})
