"""Tests for SmartyPlants data models."""

from custom_components.smartyplants.models import (
    PlantData,
    PlantThresholds,
    SensorReading,
)


def test_sensor_reading_construction():
    reading = SensorReading(value=22.5, status="OPTIMAL", message="Looking good")
    assert reading.value == 22.5
    assert reading.status == "OPTIMAL"
    assert reading.message == "Looking good"


def test_sensor_reading_none_value():
    reading = SensorReading(value=None, status="LOW", message="No data")
    assert reading.value is None


def test_plant_thresholds():
    thresholds = PlantThresholds(
        critical_low=10, low_optimal=18, high_optimal=27, critical_high=30
    )
    assert thresholds.critical_low == 10
    assert thresholds.high_optimal == 27


def test_plant_data_defaults():
    plant = PlantData(
        plant_id="abc",
        name="Monstera",
        species="Monstera deliciosa",
        common_names=["Swiss cheese plant"],
        image_url=None,
        sensor_id="sensor-1",
        sensor_identifier="SP-001",
        sensor_online=True,
    )
    assert plant.temperature is None
    assert plant.needs_attention is False
    assert plant.thresholds == {}


def test_plant_data_with_readings():
    plant = PlantData(
        plant_id="abc",
        name="Monstera",
        species="Monstera deliciosa",
        common_names=["Swiss cheese plant"],
        image_url="https://example.com/img.jpg",
        sensor_id="sensor-1",
        sensor_identifier="SP-001",
        sensor_online=True,
        temperature=SensorReading(value=22, status="OPTIMAL", message="Perfect"),
        needs_attention=True,
        attention_variant="humidity",
        attention_message="Too dry",
        thresholds={
            "temperature": PlantThresholds(
                critical_low=10, low_optimal=18, high_optimal=27, critical_high=30
            )
        },
    )
    assert plant.temperature is not None
    assert plant.temperature.value == 22
    assert plant.needs_attention is True
    assert "temperature" in plant.thresholds
