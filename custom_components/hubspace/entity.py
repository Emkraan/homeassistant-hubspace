"""Base entity for the Hubspace integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HubspaceCoordinator


class HubspaceEntity(CoordinatorEntity[HubspaceCoordinator]):
    """Common base for every Hubspace platform entity.

    Each entity is bound to one aioafero controller (e.g. ``bridge.lights``)
    and one device id within it. State is always read live from the
    controller via ``resource`` rather than cached, since aioafero itself is
    the single source of truth — the coordinator only tracks availability.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HubspaceCoordinator,
        controller_attr: str,
        device_id: str,
        unique_suffix: str = "",
    ) -> None:
        """Initialize the entity, anchoring it to its aioafero resource."""
        super().__init__(coordinator)
        self._controller_attr = controller_attr
        self.device_id = device_id
        self._attr_unique_id = (
            f"{device_id}_{unique_suffix}" if unique_suffix else device_id
        )
        info = self.resource.device_information
        device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=info.name,
            manufacturer=info.manufacturer or "Hubspace",
            model=info.model,
        )
        # Split-zone resources (e.g. a dual-channel light's white/color
        # zones) carry their parent's device_id — nest them under the
        # physical device instead of surfacing as their own top-level device.
        if info.parent_id and info.parent_id != device_id:
            device_info["via_device"] = (DOMAIN, info.parent_id)
        self._attr_device_info = device_info

    @property
    def resource(self) -> Any:
        """Return the current typed aioafero resource for this entity."""
        controller = getattr(self.coordinator.bridge, self._controller_attr)
        return controller.get_device(self.device_id)

    @property
    def available(self) -> bool:
        """Entity is available only while the coordinator has fresh data for it."""
        return super().available and self.coordinator.device_available(self.device_id)
