"""Tests for the SmartyPlants DataUpdateCoordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.smartyplants.coordinator import SmartyPlantsCoordinator
from custom_components.smartyplants.exceptions import (
    SmartyPlantsAuthError,
    SmartyPlantsConnectionError,
)
from custom_components.smartyplants.models import PlantData, SensorReading


def _make_plant(plant_id: str = "plant-1", name: str = "Monstera") -> PlantData:
    """Create a PlantData instance for testing."""
    return PlantData(
        plant_id=plant_id,
        name=name,
        species="Monstera deliciosa",
        common_names=["Swiss cheese plant"],
        image_url=None,
        sensor_id="sensor-1",
        sensor_identifier="SP-001",
        sensor_online=True,
        temperature=SensorReading(value=22, status="OPTIMAL", message="Perfect"),
        humidity=SensorReading(value=65, status="OPTIMAL", message="Good"),
        moisture=SensorReading(value=45, status="OPTIMAL", message="OK"),
    )


@pytest.fixture
def mock_client() -> AsyncMock:
    """Return a mock SmartyPlantsClient."""
    client = AsyncMock()
    client.async_get_plants = AsyncMock(return_value=[_make_plant()])
    client.async_get_requires_attention = AsyncMock(return_value=set())
    return client


async def test_update_success(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Test successful data fetch returns plants keyed by plant_id."""
    coordinator = SmartyPlantsCoordinator(
        hass,
        client=mock_client,
        update_interval=timedelta(minutes=15),
    )

    data = await coordinator._async_update_data()

    assert "plant-1" in data
    plant = data["plant-1"]
    assert plant.name == "Monstera"
    assert plant.needs_attention is False


async def test_update_with_attention(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Test that plants in the attention set get needs_attention=True."""
    mock_client.async_get_requires_attention.return_value = {"plant-1"}

    coordinator = SmartyPlantsCoordinator(
        hass,
        client=mock_client,
        update_interval=timedelta(minutes=15),
    )

    data = await coordinator._async_update_data()

    assert data["plant-1"].needs_attention is True


async def test_update_auth_error(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Test that SmartyPlantsAuthError is raised as ConfigEntryAuthFailed."""
    mock_client.async_get_plants.side_effect = SmartyPlantsAuthError("Token expired")

    coordinator = SmartyPlantsCoordinator(
        hass,
        client=mock_client,
        update_interval=timedelta(minutes=15),
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_update_connection_error(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Test that SmartyPlantsConnectionError is raised as UpdateFailed."""
    mock_client.async_get_plants.side_effect = SmartyPlantsConnectionError(
        "Connection refused"
    )

    coordinator = SmartyPlantsCoordinator(
        hass,
        client=mock_client,
        update_interval=timedelta(minutes=15),
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_multiple_plants(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Test multiple plants where only one is in the attention set."""
    mock_client.async_get_plants.return_value = [
        _make_plant(plant_id="plant-1", name="Monstera"),
        _make_plant(plant_id="plant-2", name="Fern"),
    ]
    mock_client.async_get_requires_attention.return_value = {"plant-2"}

    coordinator = SmartyPlantsCoordinator(
        hass,
        client=mock_client,
        update_interval=timedelta(minutes=15),
    )

    data = await coordinator._async_update_data()

    assert len(data) == 2
    assert data["plant-1"].needs_attention is False
    assert data["plant-2"].needs_attention is True
    assert data["plant-2"].name == "Fern"
