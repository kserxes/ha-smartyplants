"""Tests for SmartyPlants sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartyplants.const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    OPT_SHOW_STATUS_SENSORS,
)
from custom_components.smartyplants.models import (
    PlantData,
    PlantThresholds,
    SensorReading,
)

from .const import MOCK_ACCESS_TOKEN, MOCK_PLANT_ID, MOCK_REFRESH_TOKEN, MOCK_SENSOR_ID


def _make_config_entry(options: dict | None = None) -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="test@example.com",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_ACCESS_TOKEN: MOCK_ACCESS_TOKEN,
            CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
        },
        options=options or {},
        unique_id="test-user-id",
    )


def _make_plant(
    *,
    sensor_online: bool = True,
    needs_attention: bool = False,
) -> PlantData:
    """Create a test plant with full sensor data."""
    return PlantData(
        plant_id=MOCK_PLANT_ID,
        name="Test Monstera",
        species="Monstera deliciosa",
        common_names=["Swiss cheese plant"],
        image_url=None,
        sensor_id=MOCK_SENSOR_ID,
        sensor_identifier="SP-001",
        sensor_online=sensor_online,
        temperature=SensorReading(value=22.0, status="OPTIMAL", message="Perfect temp"),
        humidity=SensorReading(value=65.0, status="OPTIMAL", message="Good humidity"),
        moisture=SensorReading(value=45.5, status="LOW", message="Needs water"),
        light=SensorReading(value=12.65, status="HIGH", message="Bright"),
        nutrient=SensorReading(value=1.2, status="OPTIMAL", message="Good"),
        battery=SensorReading(value=85.0, status="OPTIMAL", message="OK"),
        voltage=SensorReading(value=3.1, status="OPTIMAL", message="OK"),
        needs_attention=needs_attention,
        thresholds={
            "temperature": PlantThresholds(
                critical_low=5.0,
                low_optimal=15.0,
                high_optimal=30.0,
                critical_high=35.0,
            ),
        },
    )


async def _setup_integration(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    plant_data: dict[str, PlantData],
) -> None:
    """Set up the integration with mocked coordinator data."""
    entry.add_to_hass(hass)

    with patch(
        "custom_components.smartyplants.SmartyPlantsClient",
    ) as mock_client_class:
        client = AsyncMock()
        client.set_tokens = MagicMock()
        client.set_token_updated_callback = MagicMock()
        client.async_get_plants = AsyncMock(return_value=list(plant_data.values()))
        client.async_get_requires_attention = AsyncMock(
            return_value={pid for pid, p in plant_data.items() if p.needs_attention}
        )
        mock_client_class.return_value = client

        with patch("custom_components.smartyplants.async_get_clientsession"):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED


@pytest.fixture
def plant() -> PlantData:
    """Return a default test plant."""
    return _make_plant()


@pytest.fixture
def plant_data(plant: PlantData) -> dict[str, PlantData]:
    """Return plant data dict keyed by plant_id."""
    return {plant.plant_id: plant}


async def test_temperature(
    hass: HomeAssistant, plant_data: dict[str, PlantData]
) -> None:
    """Test temperature sensor has correct state and attributes."""
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    state = hass.states.get("sensor.test_monstera_temperature")
    assert state is not None
    assert state.state == "22.0"
    assert state.attributes["unit_of_measurement"] == "\u00b0C"
    assert state.attributes["device_class"] == "temperature"
    assert state.attributes["status"] == "OPTIMAL"
    assert state.attributes["status_message"] == "Perfect temp"


async def test_humidity(hass: HomeAssistant, plant_data: dict[str, PlantData]) -> None:
    """Test humidity sensor state."""
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    state = hass.states.get("sensor.test_monstera_humidity")
    assert state is not None
    assert state.state == "65.0"


async def test_soil_moisture(
    hass: HomeAssistant, plant_data: dict[str, PlantData]
) -> None:
    """Test soil moisture sensor state and device class."""
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    state = hass.states.get("sensor.test_monstera_soil_moisture")
    assert state is not None
    assert state.state == "45.5"
    assert state.attributes["device_class"] == "moisture"


async def test_light(hass: HomeAssistant, plant_data: dict[str, PlantData]) -> None:
    """Test light sensor state and unit."""
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    # Light has no device_class, so HA uses translation_key for name.
    # Without translations file, the entity gets no name suffix.
    ent_reg = er.async_get(hass)
    entity_entry = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{MOCK_PLANT_ID}_light"
    )
    assert entity_entry is not None
    state = hass.states.get(entity_entry)
    assert state is not None
    assert state.state == "12.65"
    assert state.attributes["unit_of_measurement"] == "lx"
    assert state.attributes["device_class"] == "illuminance"


async def test_battery_diagnostic(
    hass: HomeAssistant, plant_data: dict[str, PlantData]
) -> None:
    """Test battery sensor has diagnostic entity category."""
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    ent_reg = er.async_get(hass)
    entity_entry = ent_reg.async_get("sensor.test_monstera_battery")
    assert entity_entry is not None
    assert entity_entry.entity_category == "diagnostic"


async def test_threshold_attributes(
    hass: HomeAssistant, plant_data: dict[str, PlantData]
) -> None:
    """Test threshold attributes are present on temperature sensor."""
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    state = hass.states.get("sensor.test_monstera_temperature")
    assert state is not None
    assert state.attributes["threshold_critical_low"] == 5.0
    assert state.attributes["threshold_high_optimal"] == 30.0


async def test_sensor_offline_unavailable(hass: HomeAssistant) -> None:
    """Test sensor is unavailable when plant sensor is offline."""
    plant = _make_plant(sensor_online=False)
    plant_data = {plant.plant_id: plant}
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    state = hass.states.get("sensor.test_monstera_temperature")
    assert state is not None
    assert state.state == "unavailable"


async def test_status_sensors_disabled_by_default(
    hass: HomeAssistant, plant_data: dict[str, PlantData]
) -> None:
    """Test status sensors are disabled by default."""
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    ent_reg = er.async_get(hass)
    # Look up by unique_id since disabled entities may not have a predictable entity_id
    entity_entry = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{MOCK_PLANT_ID}_temperature_status"
    )
    assert entity_entry is not None
    reg_entry = ent_reg.async_get(entity_entry)
    assert reg_entry is not None
    assert reg_entry.disabled_by is not None


async def test_status_sensors_enabled_by_option(hass: HomeAssistant) -> None:
    """Test status sensors are enabled when show_status_sensors option is True."""
    plant = _make_plant()
    plant_data = {plant.plant_id: plant}
    entry = _make_config_entry(options={OPT_SHOW_STATUS_SENSORS: True})
    await _setup_integration(hass, entry, plant_data)

    ent_reg = er.async_get(hass)
    entity_entry = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{MOCK_PLANT_ID}_temperature_status"
    )
    assert entity_entry is not None
    reg_entry = ent_reg.async_get(entity_entry)
    assert reg_entry is not None
    assert reg_entry.disabled_by is None
