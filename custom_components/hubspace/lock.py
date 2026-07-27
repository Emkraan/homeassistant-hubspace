"""Lock platform for the Hubspace integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .aioafero.v1.models.features import CurrentPositionEnum
from .coordinator import HubspaceCoordinator
from .entity import HubspaceEntity

CONTROLLER_ATTR = "locks"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hubspace locks from a config entry."""
    coordinator: HubspaceCoordinator = entry.runtime_data
    async_add_entities(
        HubspaceLock(coordinator, item.id) for item in coordinator.bridge.locks.items
    )


class HubspaceLock(HubspaceEntity, LockEntity):
    """Representation of a Hubspace lock."""

    _attr_name = None

    def __init__(self, coordinator: HubspaceCoordinator, device_id: str) -> None:
        """Initialize the lock."""
        super().__init__(coordinator, CONTROLLER_ATTR, device_id)

    @property
    def is_locked(self) -> bool | None:
        """Return true if the lock is locked."""
        position = self.resource.position
        if position is None:
            return None
        return position.position == CurrentPositionEnum.LOCKED

    @property
    def is_locking(self) -> bool:
        """Return true if the lock is currently locking."""
        position = self.resource.position
        return position is not None and position.position == CurrentPositionEnum.LOCKING

    @property
    def is_unlocking(self) -> bool:
        """Return true if the lock is currently unlocking."""
        position = self.resource.position
        return (
            position is not None and position.position == CurrentPositionEnum.UNLOCKING
        )

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the device."""
        await self.coordinator.bridge.locks.lock(self.device_id)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the device."""
        await self.coordinator.bridge.locks.unlock(self.device_id)
