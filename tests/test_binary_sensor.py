"""Tests for SmartyPlants binary sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartyplants.const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)
from custom_components.smartyplants.models import PlantData, SensorReading

from .const import MOCK_ACCESS_TOKEN, MOCK_PLANT_ID, MOCK_REFRESH_TOKEN, MOCK_SENSOR_ID


def _make_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="test@example.com",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_ACCESS_TOKEN: MOCK_ACCESS_TOKEN,
            CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
        },
        options={},
        unique_id="test-user-id",
    )


def _make_plant(
    *,
    sensor_online: bool = True,
    needs_attention: bool = False,
    moisture: SensorReading | None = None,
) -> PlantData:
    """Create a test plant."""
    return PlantData(
        plant_id=MOCK_PLANT_ID,
        name="Test Monstera",
        species="Monstera deliciosa",
        common_names=["Swiss cheese plant"],
        image_url=None,
        sensor_id=MOCK_SENSOR_ID,
        sensor_identifier="SP-001",
        sensor_online=sensor_online,
        temperature=SensorReading(value=22.0, status="OPTIMAL", message="OK"),
        moisture=moisture,
        needs_attention=needs_attention,
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


def _get_needs_attention_entity_id(hass: HomeAssistant) -> str:
    """Get the entity_id for the needs_attention binary sensor via registry."""
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{MOCK_PLANT_ID}_needs_attention"
    )
    assert entity_id is not None
    return entity_id


def _get_needs_watering_entity_id(hass: HomeAssistant) -> str:
    """Get the entity_id for the needs_watering binary sensor via registry."""
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{MOCK_PLANT_ID}_needs_watering"
    )
    assert entity_id is not None
    return entity_id


async def test_no_attention_needed(hass: HomeAssistant) -> None:
    """Test binary sensor is off when plant does not need attention."""
    plant = _make_plant(needs_attention=False)
    plant_data = {plant.plant_id: plant}
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    entity_id = _get_needs_attention_entity_id(hass)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "off"
    assert state.attributes["device_class"] == "problem"


async def test_attention_needed(hass: HomeAssistant) -> None:
    """Test binary sensor is on when plant needs attention."""
    plant = _make_plant(needs_attention=True)
    plant_data = {plant.plant_id: plant}
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    entity_id = _get_needs_attention_entity_id(hass)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "on"


async def test_sensor_offline_unavailable(hass: HomeAssistant) -> None:
    """Test binary sensor is unavailable when plant sensor is offline."""
    plant = _make_plant(sensor_online=False)
    plant_data = {plant.plant_id: plant}
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    entity_id = _get_needs_attention_entity_id(hass)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"


async def test_needs_watering_off_when_optimal(hass: HomeAssistant) -> None:
    """Test needs_watering is off when moisture is optimal."""
    plant = _make_plant(
        moisture=SensorReading(value=55.0, status="OPTIMAL", message="Great")
    )
    plant_data = {plant.plant_id: plant}
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    entity_id = _get_needs_watering_entity_id(hass)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "off"


async def test_needs_watering_off_when_no_reading(hass: HomeAssistant) -> None:
    """Test needs_watering is off when there is no moisture reading."""
    plant = _make_plant(moisture=None)
    plant_data = {plant.plant_id: plant}
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    entity_id = _get_needs_watering_entity_id(hass)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "off"


async def test_needs_watering_on_when_low(hass: HomeAssistant) -> None:
    """Test needs_watering is on when moisture status is LOW."""
    plant = _make_plant(
        moisture=SensorReading(value=30.0, status="LOW", message="Needs water")
    )
    plant_data = {plant.plant_id: plant}
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    entity_id = _get_needs_watering_entity_id(hass)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "on"


async def test_needs_watering_on_when_non_optimal_low(hass: HomeAssistant) -> None:
    """Test needs_watering is on when moisture status is NON_OPTIMAL_LOW."""
    plant = _make_plant(
        moisture=SensorReading(value=20.0, status="NON_OPTIMAL_LOW", message="Too dry")
    )
    plant_data = {plant.plant_id: plant}
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    entity_id = _get_needs_watering_entity_id(hass)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "on"


async def test_needs_watering_on_when_dangerously_low(hass: HomeAssistant) -> None:
    """Test needs_watering is on when moisture status is DANGEROUSLY_LOW."""
    plant = _make_plant(
        moisture=SensorReading(value=5.0, status="DANGEROUSLY_LOW", message="Critical")
    )
    plant_data = {plant.plant_id: plant}
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    entity_id = _get_needs_watering_entity_id(hass)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "on"


async def test_needs_watering_sensor_offline_unavailable(hass: HomeAssistant) -> None:
    """Test needs_watering is unavailable when sensor is offline."""
    plant = _make_plant(
        sensor_online=False,
        moisture=SensorReading(value=30.0, status="LOW", message="Needs water"),
    )
    plant_data = {plant.plant_id: plant}
    entry = _make_config_entry()
    await _setup_integration(hass, entry, plant_data)

    entity_id = _get_needs_watering_entity_id(hass)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"
