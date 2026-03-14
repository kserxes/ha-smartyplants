"""DataUpdateCoordinator for the SmartyPlants integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartyPlantsClient
from .const import DOMAIN
from .exceptions import (
    SmartyPlantsAuthError,
    SmartyPlantsConnectionError,
    SmartyPlantsError,
)
from .models import PlantData

_LOGGER = logging.getLogger(__name__)


class SmartyPlantsCoordinator(DataUpdateCoordinator[dict[str, PlantData]]):
    """Coordinator that fetches plant data and merges attention status."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        client: SmartyPlantsClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.client = client

    async def _async_update_data(self) -> dict[str, PlantData]:
        """Fetch plants and attention status, returning data keyed by plant_id."""
        try:
            plants = await self.client.async_get_plants()
            attention_ids = await self.client.async_get_requires_attention()
        except SmartyPlantsAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (SmartyPlantsConnectionError, SmartyPlantsError) as err:
            raise UpdateFailed(str(err)) from err

        result: dict[str, PlantData] = {}
        for plant in plants:
            plant.needs_attention = plant.plant_id in attention_ids
            result[plant.plant_id] = plant
        return result
