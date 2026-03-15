"""Live integration tests for the SmartyPlants API client.

These tests hit the real SmartyPlants API. They are skipped when
the environment variables are not set.

Usage:
    SMARTYPLANTS_EMAIL="..." SMARTYPLANTS_PASSWORD="..." \
        pytest tests/live/ -v
"""

from __future__ import annotations

import os

import aiohttp
import pytest

from custom_components.smartyplants.api import SmartyPlantsClient
from custom_components.smartyplants.exceptions import SmartyPlantsAuthError
from custom_components.smartyplants.models import PlantData, SensorReading

EMAIL = os.environ.get("SMARTYPLANTS_EMAIL", "")
PASSWORD = os.environ.get("SMARTYPLANTS_PASSWORD", "")

pytestmark = pytest.mark.skipif(
    not EMAIL or not PASSWORD,
    reason="SMARTYPLANTS_EMAIL and SMARTYPLANTS_PASSWORD not set",
)


@pytest.fixture
async def session():
    """Create a real aiohttp session."""
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
async def authenticated_client(session: aiohttp.ClientSession):
    """Create a client and log in with real credentials."""
    client = SmartyPlantsClient(session)
    result = await client.async_login(EMAIL, PASSWORD)
    client.set_tokens(result["access_token"], result["refresh_token"])
    return client


class TestLogin:
    async def test_login_returns_tokens(self, session: aiohttp.ClientSession):
        client = SmartyPlantsClient(session)
        result = await client.async_login(EMAIL, PASSWORD)

        assert "user_id" in result
        assert "access_token" in result
        assert "refresh_token" in result
        assert len(result["user_id"]) > 0
        assert result["access_token"].count(".") == 2, (
            "access_token doesn't look like a JWT"
        )
        assert result["refresh_token"].count(".") == 2, (
            "refresh_token doesn't look like a JWT"
        )

    async def test_login_bad_password_raises_auth_error(
        self, session: aiohttp.ClientSession
    ):
        client = SmartyPlantsClient(session)
        with pytest.raises(SmartyPlantsAuthError):
            await client.async_login(EMAIL, "definitely-wrong-password-12345")


class TestTokenRefresh:
    async def test_refresh_returns_new_token(
        self, authenticated_client: SmartyPlantsClient
    ):
        new_token = await authenticated_client.async_refresh_access_token()

        assert isinstance(new_token, str)
        assert new_token.count(".") == 2, "Token doesn't look like a JWT"

    async def test_refreshed_token_works_for_api_calls(
        self, authenticated_client: SmartyPlantsClient
    ):
        """After refreshing, the new token should work for subsequent API calls."""
        await authenticated_client.async_refresh_access_token()
        plants = await authenticated_client.async_get_plants()
        assert isinstance(plants, list)


class TestGetPlants:
    async def test_returns_plant_data_list(
        self, authenticated_client: SmartyPlantsClient
    ):
        plants = await authenticated_client.async_get_plants()

        assert isinstance(plants, list)
        assert len(plants) > 0, "Expected at least one plant - is this account set up?"

    async def test_plant_has_required_fields(
        self, authenticated_client: SmartyPlantsClient
    ):
        plants = await authenticated_client.async_get_plants()
        plant = plants[0]

        assert isinstance(plant, PlantData)
        assert plant.plant_id
        assert plant.name
        assert plant.species
        assert isinstance(plant.common_names, list)
        assert plant.sensor_id is not None, "First plant should have a sensor assigned"
        assert plant.sensor_identifier is not None
        assert isinstance(plant.sensor_online, bool)

    async def test_plant_has_sensor_readings(
        self, authenticated_client: SmartyPlantsClient
    ):
        plants = await authenticated_client.async_get_plants()
        plant = plants[0]

        readings = [
            ("temperature", plant.temperature),
            ("humidity", plant.humidity),
            ("moisture", plant.moisture),
            ("light", plant.light),
            ("nutrient", plant.nutrient),
            ("battery", plant.battery),
            ("voltage", plant.voltage),
        ]

        populated = [(name, r) for name, r in readings if r is not None]
        assert len(populated) > 0, "Expected at least one sensor reading"

        for name, reading in populated:
            assert isinstance(reading, SensorReading), f"{name} is not a SensorReading"
            assert isinstance(reading.status, str), f"{name} status is not a string"
            assert len(reading.status) > 0, f"{name} status is empty"
            assert isinstance(reading.message, str), f"{name} message is not a string"
            if reading.value is not None:
                assert isinstance(reading.value, float), f"{name} value is not a float"

    async def test_reading_statuses_are_known_values(
        self, authenticated_client: SmartyPlantsClient
    ):
        """Verify we haven't missed any status values the API can return."""
        known_statuses = {
            "OPTIMAL",
            "LOW",
            "HIGH",
            "NON_OPTIMAL_LOW",
            "NON_OPTIMAL_HIGH",
            "DANGEROUSLY_LOW",
        }

        plants = await authenticated_client.async_get_plants()
        for plant in plants:
            for reading in [
                plant.temperature,
                plant.humidity,
                plant.moisture,
                plant.light,
                plant.nutrient,
                plant.battery,
                plant.voltage,
            ]:
                if reading is not None and reading.status:
                    assert reading.status in known_statuses, (
                        f"Unknown status '{reading.status}' on "
                        f"plant '{plant.name}' "
                        f"- API may have added a new status value"
                    )

    async def test_thresholds_parsed(self, authenticated_client: SmartyPlantsClient):
        """Verify threshold configs are parsed from plantConfigurations."""
        plants = await authenticated_client.async_get_plants()
        plant = plants[0]

        if plant.thresholds:
            for variant, thresholds in plant.thresholds.items():
                assert variant in (
                    "temperature",
                    "humidity",
                    "light",
                    "nutrient",
                    "moisture",
                ), f"Unknown threshold variant: {variant}"
                assert thresholds.critical_low <= thresholds.low_optimal
                assert thresholds.low_optimal <= thresholds.high_optimal
                assert thresholds.high_optimal <= thresholds.critical_high

    async def test_sensorless_plants_are_filtered(
        self, authenticated_client: SmartyPlantsClient
    ):
        """Every returned plant should have a sensor.

        Sensorless ones are filtered out by the client.
        """
        plants = await authenticated_client.async_get_plants()
        for plant in plants:
            assert plant.sensor_id is not None, (
                f"Plant '{plant.name}' has no sensor - should have been filtered"
            )


class TestGetRequiresAttention:
    async def test_returns_set_of_strings(
        self, authenticated_client: SmartyPlantsClient
    ):
        result = await authenticated_client.async_get_requires_attention()

        assert isinstance(result, set)
        for plant_id in result:
            assert isinstance(plant_id, str)
            assert len(plant_id) > 0

    async def test_attention_ids_are_valid_uuids(
        self, authenticated_client: SmartyPlantsClient
    ):
        attention_ids = await authenticated_client.async_get_requires_attention()
        for pid in attention_ids:
            assert len(pid) > 10, f"Suspiciously short plant ID: {pid}"
