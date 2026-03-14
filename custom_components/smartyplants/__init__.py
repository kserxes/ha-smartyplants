"""The SmartyPlants integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartyPlantsClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    OPT_SCAN_INTERVAL,
)
from .coordinator import SmartyPlantsCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


@dataclass
class SmartyPlantsRuntimeData:
    """Runtime data for the SmartyPlants integration."""

    coordinator: SmartyPlantsCoordinator


type SmartyPlantsConfigEntry = ConfigEntry[SmartyPlantsRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant, entry: SmartyPlantsConfigEntry
) -> bool:
    """Set up SmartyPlants from a config entry."""
    session = async_get_clientsession(hass)
    client = SmartyPlantsClient(session)
    client.set_tokens(entry.data[CONF_ACCESS_TOKEN], entry.data[CONF_REFRESH_TOKEN])

    async def _token_updated(new_access: str, new_refresh: str | None) -> None:
        data = {**entry.data, CONF_ACCESS_TOKEN: new_access}
        if new_refresh is not None:
            data[CONF_REFRESH_TOKEN] = new_refresh
        hass.config_entries.async_update_entry(entry, data=data)

    client.set_token_updated_callback(_token_updated)

    scan_interval = entry.options.get(OPT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = SmartyPlantsCoordinator(
        hass, client=client, update_interval=timedelta(minutes=scan_interval)
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = SmartyPlantsRuntimeData(coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: SmartyPlantsConfigEntry
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: SmartyPlantsConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
