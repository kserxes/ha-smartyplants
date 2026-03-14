"""Binary sensor platform for the SmartyPlants integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SmartyPlantsConfigEntry
from .const import DOMAIN
from .coordinator import SmartyPlantsCoordinator
from .models import PlantData


def _get_device_info(plant: PlantData) -> DeviceInfo:
    """Return device info for a plant."""
    return DeviceInfo(
        identifiers={(DOMAIN, plant.plant_id)},
        name=plant.name,
        manufacturer="SmartyPlants",
        model=plant.species,
    )


class SmartyPlantsNeedsAttentionSensor(
    CoordinatorEntity[SmartyPlantsCoordinator], BinarySensorEntity
):
    """Binary sensor indicating whether a plant needs attention."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "needs_attention"

    def __init__(
        self,
        coordinator: SmartyPlantsCoordinator,
        plant_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._plant_id = plant_id
        self._attr_unique_id = f"{plant_id}_needs_attention"

    @property
    def _plant(self) -> PlantData:
        """Return the plant data."""
        return self.coordinator.data[self._plant_id]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _get_device_info(self._plant)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self._plant.sensor_online

    @property
    def is_on(self) -> bool:
        """Return True if the plant needs attention."""
        return self._plant.needs_attention


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartyPlantsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SmartyPlants binary sensor entities."""
    coordinator = entry.runtime_data.coordinator

    entities = [
        SmartyPlantsNeedsAttentionSensor(coordinator, plant_id)
        for plant_id in coordinator.data
    ]

    async_add_entities(entities)
