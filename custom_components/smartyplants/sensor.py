"""Sensor platform for the SmartyPlants integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfConductivity,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SmartyPlantsConfigEntry
from .const import DOMAIN, OPT_SHOW_STATUS_SENSORS, READING_STATUS_OPTIONS
from .coordinator import SmartyPlantsCoordinator
from .models import PlantData, SensorReading


@dataclass(frozen=True, kw_only=True)
class SmartyPlantsSensorDescription(SensorEntityDescription):
    """Describe a SmartyPlants numeric sensor."""

    reading_key: str
    value_fn: Callable[[SensorReading], float | None] = lambda r: r.value


@dataclass(frozen=True, kw_only=True)
class SmartyPlantsStatusSensorDescription(SensorEntityDescription):
    """Describe a SmartyPlants status sensor."""

    reading_key: str


NUMERIC_SENSORS: tuple[SmartyPlantsSensorDescription, ...] = (
    SmartyPlantsSensorDescription(
        key="temperature",
        translation_key="temperature",
        reading_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SmartyPlantsSensorDescription(
        key="humidity",
        translation_key="humidity",
        reading_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SmartyPlantsSensorDescription(
        key="soil_moisture",
        translation_key="soil_moisture",
        reading_key="moisture",
        device_class=SensorDeviceClass.MOISTURE,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SmartyPlantsSensorDescription(
        key="light",
        translation_key="light",
        reading_key="light",
        native_unit_of_measurement="mol/d\u22c5m\u00b2",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SmartyPlantsSensorDescription(
        key="nutrient",
        translation_key="nutrient",
        reading_key="nutrient",
        device_class=SensorDeviceClass.CONDUCTIVITY,
        native_unit_of_measurement=UnitOfConductivity.MILLISIEMENS_PER_CM,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SmartyPlantsSensorDescription(
        key="battery",
        translation_key="battery",
        reading_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
)

STATUS_SENSORS: tuple[SmartyPlantsStatusSensorDescription, ...] = (
    SmartyPlantsStatusSensorDescription(
        key="temperature_status",
        translation_key="temperature_status",
        reading_key="temperature",
        device_class=SensorDeviceClass.ENUM,
        options=READING_STATUS_OPTIONS,
    ),
    SmartyPlantsStatusSensorDescription(
        key="humidity_status",
        translation_key="humidity_status",
        reading_key="humidity",
        device_class=SensorDeviceClass.ENUM,
        options=READING_STATUS_OPTIONS,
    ),
    SmartyPlantsStatusSensorDescription(
        key="soil_moisture_status",
        translation_key="soil_moisture_status",
        reading_key="moisture",
        device_class=SensorDeviceClass.ENUM,
        options=READING_STATUS_OPTIONS,
    ),
    SmartyPlantsStatusSensorDescription(
        key="light_status",
        translation_key="light_status",
        reading_key="light",
        device_class=SensorDeviceClass.ENUM,
        options=READING_STATUS_OPTIONS,
    ),
    SmartyPlantsStatusSensorDescription(
        key="nutrient_status",
        translation_key="nutrient_status",
        reading_key="nutrient",
        device_class=SensorDeviceClass.ENUM,
        options=READING_STATUS_OPTIONS,
    ),
)


def _get_device_info(plant: PlantData) -> DeviceInfo:
    """Return device info for a plant."""
    return DeviceInfo(
        identifiers={(DOMAIN, plant.plant_id)},
        name=plant.name,
        manufacturer="SmartyPlants",
        model=plant.species,
    )


class SmartyPlantsNumericSensor(
    CoordinatorEntity[SmartyPlantsCoordinator], SensorEntity
):
    """A numeric sensor for a SmartyPlants reading."""

    _attr_has_entity_name = True
    entity_description: SmartyPlantsSensorDescription

    def __init__(
        self,
        coordinator: SmartyPlantsCoordinator,
        plant_id: str,
        description: SmartyPlantsSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._plant_id = plant_id
        self._attr_unique_id = f"{plant_id}_{description.key}"

    @property
    def _plant(self) -> PlantData:
        """Return the plant data."""
        return self.coordinator.data[self._plant_id]

    @property
    def _reading(self) -> SensorReading | None:
        """Return the sensor reading for this entity."""
        return getattr(self._plant, self.entity_description.reading_key, None)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _get_device_info(self._plant)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self._plant.sensor_online

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        reading = self._reading
        if reading is None:
            return None
        return self.entity_description.value_fn(reading)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return extra state attributes."""
        attrs: dict[str, object] = {}
        reading = self._reading
        if reading is not None:
            attrs["status"] = reading.status
            attrs["status_message"] = reading.message

        thresholds = self._plant.thresholds.get(self.entity_description.reading_key)
        if thresholds is not None:
            attrs["threshold_critical_low"] = thresholds.critical_low
            attrs["threshold_low_optimal"] = thresholds.low_optimal
            attrs["threshold_high_optimal"] = thresholds.high_optimal
            attrs["threshold_critical_high"] = thresholds.critical_high

        return attrs if attrs else None


class SmartyPlantsStatusSensor(
    CoordinatorEntity[SmartyPlantsCoordinator], SensorEntity
):
    """A status sensor for a SmartyPlants reading."""

    _attr_has_entity_name = True
    entity_description: SmartyPlantsStatusSensorDescription

    def __init__(
        self,
        coordinator: SmartyPlantsCoordinator,
        plant_id: str,
        description: SmartyPlantsStatusSensorDescription,
        *,
        enabled_default: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._plant_id = plant_id
        self._attr_unique_id = f"{plant_id}_{description.key}"
        self._attr_entity_registry_enabled_default = enabled_default

    @property
    def _plant(self) -> PlantData:
        """Return the plant data."""
        return self.coordinator.data[self._plant_id]

    @property
    def _reading(self) -> SensorReading | None:
        """Return the sensor reading for this entity."""
        return getattr(self._plant, self.entity_description.reading_key, None)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _get_device_info(self._plant)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self._plant.sensor_online

    @property
    def native_value(self) -> str | None:
        """Return the status value (lowercased)."""
        reading = self._reading
        if reading is None:
            return None
        return reading.status.lower()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartyPlantsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SmartyPlants sensor entities."""
    coordinator = entry.runtime_data.coordinator
    show_status = entry.options.get(OPT_SHOW_STATUS_SENSORS, False)

    entities: list[SensorEntity] = []
    for plant_id in coordinator.data:
        for description in NUMERIC_SENSORS:
            entities.append(
                SmartyPlantsNumericSensor(coordinator, plant_id, description)
            )
        for description in STATUS_SENSORS:
            entities.append(
                SmartyPlantsStatusSensor(
                    coordinator,
                    plant_id,
                    description,
                    enabled_default=show_status,
                )
            )

    async_add_entities(entities)
