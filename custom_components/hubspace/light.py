"""Light platform for the Hubspace integration.

Multi-zone / dual-channel lights (e.g. a fixture with independent white and
color zones) are already split into separate ``Light`` resources by aioafero
itself (``LightController.DEVICE_SPLIT_CALLBACKS``) — each split zone shows
up as its own entry in ``bridge.lights.items`` with its own device id, so no
zone-splitting logic is needed at this layer.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity, LightEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HubspaceCoordinator
from .entity import HubspaceEntity

CONTROLLER_ATTR = "lights"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hubspace lights from a config entry.

    Entities are created once from the devices known at startup. Hubspace
    devices are paired through the Hubspace app, not added at runtime from
    HA's perspective, so there is no dynamic-discovery-while-running case to
    handle here.
    """
    coordinator: HubspaceCoordinator = entry.runtime_data
    controller = coordinator.bridge.lights
    async_add_entities(HubspaceLight(coordinator, item.id) for item in controller.items)


class HubspaceLight(HubspaceEntity, LightEntity):
    """Representation of a Hubspace light (or split light zone)."""

    def __init__(self, coordinator: HubspaceCoordinator, device_id: str) -> None:
        """Initialize the light."""
        super().__init__(coordinator, CONTROLLER_ATTR, device_id)
        self._attr_name = None

    @property
    def _resource(self):
        return self.resource

    @property
    def _supported_modes(self) -> set[ColorMode]:
        modes: set[ColorMode] = set()
        light = self._resource
        if light.supports_color:
            modes.add(ColorMode.RGB)
        if light.supports_color_temperature:
            modes.add(ColorMode.COLOR_TEMP)
        if not modes and light.supports_dimming:
            modes.add(ColorMode.BRIGHTNESS)
        if not modes and light.supports_on:
            modes.add(ColorMode.ONOFF)
        return modes

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Return the color modes this light supports."""
        return self._supported_modes

    @property
    def color_mode(self) -> ColorMode:
        """Return the currently active color mode."""
        light = self._resource
        modes = self._supported_modes
        afero_mode = light.color_mode.mode if light.color_mode else None
        if afero_mode == "color" and ColorMode.RGB in modes:
            return ColorMode.RGB
        if ColorMode.COLOR_TEMP in modes:
            return ColorMode.COLOR_TEMP
        if ColorMode.RGB in modes:
            return ColorMode.RGB
        if ColorMode.BRIGHTNESS in modes:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def supported_features(self) -> LightEntityFeature:
        """Return supported entity features."""
        if self._resource.supports_effects:
            return LightEntityFeature.EFFECT
        return LightEntityFeature(0)

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self._resource.is_on

    @property
    def brightness(self) -> int | None:
        """Return brightness scaled from Afero's 0-100 to HA's 0-255."""
        if not self._resource.supports_dimming:
            return None
        return round(self._resource.brightness * 255 / 100)

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the RGB color."""
        color = self._resource.color
        if color is None:
            return None
        return (color.red, color.green, color.blue)

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        color_temperature = self._resource.color_temperature
        if color_temperature is None:
            return None
        return color_temperature.temperature

    @property
    def min_color_temp_kelvin(self) -> int | None:
        """Return the coldest color temperature this light supports."""
        color_temperature = self._resource.color_temperature
        if not color_temperature or not color_temperature.supported:
            return None
        return min(color_temperature.supported)

    @property
    def max_color_temp_kelvin(self) -> int | None:
        """Return the warmest color temperature this light supports."""
        color_temperature = self._resource.color_temperature
        if not color_temperature or not color_temperature.supported:
            return None
        return max(color_temperature.supported)

    @property
    def effect_list(self) -> list[str] | None:
        """Return the list of supported effects."""
        effect = self._resource.effect
        if effect is None:
            return None
        names: set[str] = set()
        for group in effect.effects.values():
            names.update(group)
        return sorted(names)

    @property
    def effect(self) -> str | None:
        """Return the currently active effect, if any."""
        effect = self._resource.effect
        if effect is None:
            return None
        return effect.effect

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on, applying any requested attributes in one call."""
        controller = self.coordinator.bridge.lights
        brightness = kwargs.get("brightness")
        await controller.set_state(
            self.device_id,
            on=True,
            brightness=(
                round(brightness * 100 / 255) if brightness is not None else None
            ),
            color=kwargs.get("rgb_color"),
            color_mode=(
                "color"
                if "rgb_color" in kwargs
                else "sequence" if "effect" in kwargs else None
            ),
            temperature=kwargs.get("color_temp_kelvin"),
            effect=kwargs.get("effect"),
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.coordinator.bridge.lights.turn_off(self.device_id)
