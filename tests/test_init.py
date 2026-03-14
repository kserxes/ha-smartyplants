"""Tests for SmartyPlants integration setup."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartyplants.const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    OPT_SCAN_INTERVAL,
)
from custom_components.smartyplants.models import PlantData, SensorReading

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


def _make_plant() -> PlantData:
    """Create a test plant."""
    return PlantData(
        plant_id=MOCK_PLANT_ID,
        name="Test Monstera",
        species="Monstera deliciosa",
        common_names=["Swiss cheese plant"],
        image_url=None,
        sensor_id=MOCK_SENSOR_ID,
        sensor_identifier="SP-001",
        sensor_online=True,
        temperature=SensorReading(value=22.0, status="OPTIMAL", message="OK"),
    )


async def _setup_integration(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    plants: list[PlantData] | None = None,
) -> AsyncMock:
    """Set up the integration and return the mock client."""
    entry.add_to_hass(hass)

    if plants is None:
        plants = [_make_plant()]

    with patch(
        "custom_components.smartyplants.SmartyPlantsClient",
    ) as mock_client_class:
        client = AsyncMock()
        client.async_get_plants = AsyncMock(return_value=plants)
        client.async_get_requires_attention = AsyncMock(return_value=set())
        mock_client_class.return_value = client

        with patch("custom_components.smartyplants.async_get_clientsession"):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

    return client


async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test successful setup of a config entry."""
    entry = _make_config_entry()
    await _setup_integration(hass, entry)

    assert entry.state is ConfigEntryState.LOADED


async def test_unload_entry(hass: HomeAssistant) -> None:
    """Test unloading a config entry."""
    entry = _make_config_entry()
    await _setup_integration(hass, entry)

    assert entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_custom_scan_interval(hass: HomeAssistant) -> None:
    """Test that custom scan interval is applied to coordinator."""
    entry = _make_config_entry(options={OPT_SCAN_INTERVAL: 30})
    await _setup_integration(hass, entry)

    coordinator = entry.runtime_data.coordinator
    assert coordinator.update_interval == timedelta(minutes=30)
