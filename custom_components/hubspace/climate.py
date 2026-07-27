"""Climate platform for the Hubspace integration (thermostats + portable ACs).

Afero HVAC mode strings are mapped 1:1 onto real HA ``HVACMode`` values only.
Any mode string without a direct equivalent is left out of ``hvac_modes``
rather than invented or approximated — see the README's Troubleshooting
section for the current confirmed set.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .aioafero.types import TemperatureUnit
from .coordinator import HubspaceCoordinator
from .entity import HubspaceEntity

HVAC_MODE_TO_AFERO = {
    HVACMode.OFF: "off",
    HVACMode.HEAT: "heat",
    HVACMode.COOL: "cool",
    HVACMode.HEAT_COOL: "auto",
    HVACMode.FAN_ONLY: "fan",
    HVACMode.DRY: "dehumidify",
}
AFERO_MODE_TO_HVAC = {v: k for k, v in HVAC_MODE_TO_AFERO.items()}

HVAC_ACTION_MAP = {
    "heating": HVACAction.HEATING,
    "cooling": HVACAction.COOLING,
    "fan": HVACAction.FAN,
    "idle": HVACAction.IDLE,
    "off": HVACAction.OFF,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hubspace climate entities from a config entry."""
    coordinator: HubspaceCoordinator = entry.runtime_data
    entities: list[ClimateEntity] = [
        HubspaceThermostat(coordinator, item.id)
        for item in coordinator.bridge.thermostats.items
    ]
    entities.extend(
        HubspacePortableAC(coordinator, item.id)
        for item in coordinator.bridge.portable_acs.items
    )
    async_add_entities(entities)


class _HubspaceClimateBase(HubspaceEntity, ClimateEntity):
    """Shared HVAC-mode/temperature plumbing for thermostats and portable ACs."""

    _attr_name = None

    @property
    def temperature_unit(self) -> str:
        """Return the unit temperatures are expressed in."""
        if self.coordinator.bridge.temperature_unit == TemperatureUnit.FAHRENHEIT:
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of HVAC modes this device supports."""
        hvac_mode = self.resource.hvac_mode
        if hvac_mode is None:
            return [HVACMode.OFF]
        return [
            AFERO_MODE_TO_HVAC[mode]
            for mode in hvac_mode.supported_modes
            if mode in AFERO_MODE_TO_HVAC
        ] or [HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the current HVAC mode."""
        hvac_mode = self.resource.hvac_mode
        if hvac_mode is None or hvac_mode.mode is None:
            return None
        return AFERO_MODE_TO_HVAC.get(hvac_mode.mode)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current HVAC action."""
        action = self.resource.hvac_action
        if action is None:
            return None
        return HVAC_ACTION_MAP.get(action)

    @property
    def current_temperature(self) -> float | None:
        """Return the current measured temperature."""
        return self.resource.temperature


class HubspaceThermostat(_HubspaceClimateBase):
    """Representation of a Hubspace thermostat."""

    def __init__(self, coordinator: HubspaceCoordinator, device_id: str) -> None:
        """Initialize the thermostat."""
        super().__init__(coordinator, "thermostats", device_id)

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return supported entity features."""
        features = ClimateEntityFeature.TARGET_TEMPERATURE
        if self.resource.supports_temperature_range:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        if self.resource.supports_fan_mode:
            features |= ClimateEntityFeature.FAN_MODE
        return features

    @property
    def fan_modes(self) -> list[str] | None:
        """Return supported fan modes."""
        fan_mode = self.resource.fan_mode
        return sorted(fan_mode.modes) if fan_mode else None

    @property
    def fan_mode(self) -> str | None:
        """Return the current fan mode."""
        fan_mode = self.resource.fan_mode
        return fan_mode.mode if fan_mode else None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature for the active heat/cool mode."""
        return self.resource.target_temperature

    @property
    def target_temperature_low(self) -> float | None:
        """Return the auto-mode heating setpoint."""
        if not self.resource.supports_temperature_range:
            return None
        return self.resource.target_temperature_auto_heating.value

    @property
    def target_temperature_high(self) -> float | None:
        """Return the auto-mode cooling setpoint."""
        if not self.resource.supports_temperature_range:
            return None
        return self.resource.target_temperature_auto_cooling.value

    @property
    def min_temp(self) -> float:
        """Return the minimum settable temperature."""
        return self.resource.target_temperature_min or 0.0

    @property
    def max_temp(self) -> float:
        """Return the maximum settable temperature."""
        return self.resource.target_temperature_max or 99.0

    @property
    def target_temperature_step(self) -> float:
        """Return the smallest increment supported."""
        return self.resource.target_temperature_step

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        afero_mode = HVAC_MODE_TO_AFERO.get(hvac_mode)
        if afero_mode is not None:
            await self.coordinator.bridge.thermostats.set_hvac_mode(
                self.device_id, afero_mode
            )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan mode."""
        await self.coordinator.bridge.thermostats.set_fan_mode(self.device_id, fan_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature (single setpoint or heat/cool range)."""
        controller = self.coordinator.bridge.thermostats
        if ATTR_TEMPERATURE in kwargs:
            await controller.set_target_temperature(
                self.device_id, kwargs[ATTR_TEMPERATURE]
            )
            return
        low = kwargs.get("target_temp_low")
        high = kwargs.get("target_temp_high")
        if low is not None and high is not None:
            await controller.set_temperature_range(self.device_id, low, high)


class HubspacePortableAC(_HubspaceClimateBase):
    """Representation of a Hubspace portable air conditioner."""

    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self, coordinator: HubspaceCoordinator, device_id: str) -> None:
        """Initialize the portable AC."""
        super().__init__(coordinator, "portable_acs", device_id)

    @property
    def target_temperature(self) -> float | None:
        """Return the cooling setpoint."""
        target = self.resource.target_temperature_cooling
        return target.value if target else None

    @property
    def min_temp(self) -> float:
        """Return the minimum settable temperature."""
        target = self.resource.target_temperature_cooling
        return target.min if target else 16.0

    @property
    def max_temp(self) -> float:
        """Return the maximum settable temperature."""
        target = self.resource.target_temperature_cooling
        return target.max if target else 32.0

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        afero_mode = HVAC_MODE_TO_AFERO.get(hvac_mode)
        if afero_mode is not None:
            await self.coordinator.bridge.portable_acs.set_state(
                self.device_id, hvac_mode=afero_mode
            )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the cooling setpoint."""
        if ATTR_TEMPERATURE in kwargs:
            await self.coordinator.bridge.portable_acs.set_state(
                self.device_id, target_temperature=kwargs[ATTR_TEMPERATURE]
            )
