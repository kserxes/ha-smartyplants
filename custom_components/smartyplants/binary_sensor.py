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

_MOISTURE_DRY_STATUSES = frozenset({"LOW", "NON_OPTIMAL_LOW", "DANGEROUSLY_LOW"})


def _get_device_info(plant: PlantData) -> DeviceInfo:
    """Return device info for a plant."""
    info = DeviceInfo(
        identifiers={(DOMAIN, plant.plant_id)},
        name=plant.name,
        manufacturer="SmartyPlants",
        model=plant.species,
    )
    if plant.environment_name:
        info["suggested_area"] = plant.environment_name
    return info


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


class SmartyPlantsNeedsWateringSensor(
    CoordinatorEntity[SmartyPlantsCoordinator], BinarySensorEntity
):
    """Binary sensor indicating whether a plant needs watering."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "needs_watering"

    def __init__(
        self,
        coordinator: SmartyPlantsCoordinator,
        plant_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._plant_id = plant_id
        self._attr_unique_id = f"{plant_id}_needs_watering"

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
        """Return True if the plant needs watering."""
        moisture = self._plant.moisture
        return moisture is not None and moisture.status in _MOISTURE_DRY_STATUSES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartyPlantsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SmartyPlants binary sensor entities."""
    coordinator = entry.runtime_data.coordinator

    entities: list[BinarySensorEntity] = []
    for plant_id in coordinator.data:
        entities.append(SmartyPlantsNeedsAttentionSensor(coordinator, plant_id))
        entities.append(SmartyPlantsNeedsWateringSensor(coordinator, plant_id))

    async_add_entities(entities)
