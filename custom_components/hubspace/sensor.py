"""Sensor platform for the Hubspace integration.

Every aioafero resource type exposes its telemetry (battery level, Wi-Fi
RSSI, power draw, etc.) through the same generic ``sensors`` dict
(``StandardMixin``), keyed per-controller by that controller's own
``ITEM_SENSORS`` mapping. Rather than duplicate per-device-type code, this
platform walks every initialized controller once and creates one entity per
sensor entry it finds — new sensor keys added to any controller (including
future ones) are picked up automatically.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HubspaceCoordinator
from .entity import HubspaceEntity

_DEVICE_CLASS_BY_UNIT = {
    PERCENTAGE: SensorDeviceClass.BATTERY,
    SIGNAL_STRENGTH_DECIBELS: SensorDeviceClass.SIGNAL_STRENGTH,
    UnitOfPower.WATT: SensorDeviceClass.POWER,
    UnitOfElectricPotential.VOLT: SensorDeviceClass.VOLTAGE,
    UnitOfElectricCurrent.AMPERE: SensorDeviceClass.CURRENT,
}
_UNIT_ALIASES = {
    "dB": SIGNAL_STRENGTH_DECIBELS,
    "W": UnitOfPower.WATT,
    "V": UnitOfElectricPotential.VOLT,
    "A": UnitOfElectricCurrent.AMPERE,
    "%": PERCENTAGE,
}


def _friendly_name(key: str) -> str:
    return key.replace("|", " ").replace("-", " ").replace("_", " ").strip().title()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hubspace sensors from every controller's generic sensor dict."""
    coordinator: HubspaceCoordinator = entry.runtime_data
    entities = [
        HubspaceSensor(coordinator, controller_attr, item.id, sensor_key)
        for controller_attr, controller in coordinator.bridge.controllers_by_name.items()
        for item in controller.items
        for sensor_key in item.sensors
    ]
    async_add_entities(entities)


class HubspaceSensor(HubspaceEntity, SensorEntity):
    """A single generic telemetry value on a Hubspace resource."""

    def __init__(
        self,
        coordinator: HubspaceCoordinator,
        controller_attr: str,
        device_id: str,
        sensor_key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, controller_attr, device_id, sensor_key)
        self.sensor_key = sensor_key
        self._attr_name = _friendly_name(sensor_key)
        unit = _UNIT_ALIASES.get(
            self.resource.sensors[sensor_key].unit,
            self.resource.sensors[sensor_key].unit,
        )
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = _DEVICE_CLASS_BY_UNIT.get(unit)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        """Return the current sensor value."""
        return self.resource.sensors[self.sensor_key].value
