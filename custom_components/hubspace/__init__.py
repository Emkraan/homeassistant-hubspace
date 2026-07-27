"""The Hubspace integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import HubspaceCoordinator

type HubspaceConfigEntry = ConfigEntry[HubspaceCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: HubspaceConfigEntry) -> bool:
    """Set up Hubspace from a config entry."""
    coordinator = HubspaceCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(
    hass: HomeAssistant, entry: HubspaceConfigEntry
) -> None:
    """Reload the entry whenever the options flow saves changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: HubspaceConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
