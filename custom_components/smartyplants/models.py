"""Data models for the SmartyPlants integration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SensorReading:
    """A single sensor reading with value, status, and message."""

    value: float | None
    status: str
    message: str


@dataclass
class PlantThresholds:
    """Threshold configuration for a reading variant."""

    critical_low: float
    low_optimal: float
    high_optimal: float
    critical_high: float


@dataclass
class PlantData:
    """Processed plant data from the API, ready for entities to consume."""

    plant_id: str
    name: str
    species: str
    common_names: list[str]
    image_url: str | None

    sensor_id: str | None
    sensor_identifier: str | None
    sensor_online: bool

    temperature: SensorReading | None = None
    humidity: SensorReading | None = None
    moisture: SensorReading | None = None
    light: SensorReading | None = None
    nutrient: SensorReading | None = None
    battery: SensorReading | None = None
    voltage: SensorReading | None = None

    environment_name: str | None = None
    needs_attention: bool = False
    attention_variant: str | None = None
    attention_message: str | None = None

    thresholds: dict[str, PlantThresholds] = field(default_factory=dict)
