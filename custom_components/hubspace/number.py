"""Number platform for the Hubspace integration.

Walks every initialized controller's generic ``numbers`` dict
(``StandardMixin``), same approach as sensor.py. Every controller that
populates ``ITEM_NUMBERS`` accepts writing it back via
``set_state(device_id, numbers={(functionClass, functionInstance): value})``,
so one generic implementation covers all of them.
"""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HubspaceCoordinator
from .entity import HubspaceEntity


def _friendly_name(key: tuple[str, str | None], display_name: str | None) -> str:
    if display_name:
        return display_name
    func_class, func_instance = key
    return (
        (func_class if not func_instance else f"{func_class} {func_instance}")
        .replace("-", " ")
        .title()
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hubspace numbers from every controller's generic numbers dict."""
    coordinator: HubspaceCoordinator = entry.runtime_data
    entities = [
        HubspaceNumber(coordinator, controller_attr, item.id, key)
        for controller_attr, controller in coordinator.bridge.controllers_by_name.items()
        for item in controller.items
        for key in item.numbers
    ]
    async_add_entities(entities)


class HubspaceNumber(HubspaceEntity, NumberEntity):
    """A single generic numeric setting on a Hubspace resource."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: HubspaceCoordinator,
        controller_attr: str,
        device_id: str,
        key: tuple[str, str | None],
    ) -> None:
        """Initialize the number."""
        unique_suffix = f"{key[0]}_{key[1] or 'default'}"
        super().__init__(coordinator, controller_attr, device_id, unique_suffix)
        self.key = key
        number = self.resource.numbers[key]
        self._attr_name = _friendly_name(key, number.name)
        self._attr_native_unit_of_measurement = number.unit
        self._attr_native_min_value = number.min
        self._attr_native_max_value = number.max
        self._attr_native_step = number.step

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.resource.numbers[self.key].value

    async def async_set_native_value(self, value: float) -> None:
        """Set a new value."""
        controller = getattr(self.coordinator.bridge, self._controller_attr)
        await controller.set_state(self.device_id, numbers={self.key: value})
