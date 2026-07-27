"""Binary sensor platform for the Hubspace integration.

Walks every initialized controller's generic ``binary_sensors`` dict, same
approach as sensor.py. This is also how security-system zone sensors surface
(``bridge.security_systems_sensors``, split off the panel by aioafero's own
``security_system_callback``) without any bespoke per-zone code here.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HubspaceCoordinator
from .entity import HubspaceEntity

_DEVICE_CLASS_BY_KEY_PREFIX = {
    "motion-detection": BinarySensorDeviceClass.MOTION,
    "error": BinarySensorDeviceClass.PROBLEM,
    "battery-powered": None,
    "humidity-threshold-met": BinarySensorDeviceClass.MOISTURE,
    "max-temp-exceeded": BinarySensorDeviceClass.HEAT,
    "min-temp-exceeded": BinarySensorDeviceClass.COLD,
    "filter-replacement": BinarySensorDeviceClass.PROBLEM,
}


def _friendly_name(key: str) -> str:
    return key.split("|")[0].replace("-", " ").replace("_", " ").strip().title()


def _device_class(key: str) -> BinarySensorDeviceClass | None:
    return _DEVICE_CLASS_BY_KEY_PREFIX.get(key.split("|")[0])


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hubspace binary sensors from every controller's generic dict."""
    coordinator: HubspaceCoordinator = entry.runtime_data
    entities = [
        HubspaceBinarySensor(coordinator, controller_attr, item.id, sensor_key)
        for controller_attr, controller in coordinator.bridge.controllers_by_name.items()
        for item in controller.items
        for sensor_key in item.binary_sensors
    ]
    async_add_entities(entities)


class HubspaceBinarySensor(HubspaceEntity, BinarySensorEntity):
    """A single generic alert/state flag on a Hubspace resource."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: HubspaceCoordinator,
        controller_attr: str,
        device_id: str,
        sensor_key: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, controller_attr, device_id, sensor_key)
        self.sensor_key = sensor_key
        self._attr_name = _friendly_name(sensor_key)
        self._attr_device_class = _device_class(sensor_key)

    @property
    def is_on(self) -> bool:
        """Return true if the sensor is in its alerting state."""
        return self.resource.binary_sensors[self.sensor_key].value
