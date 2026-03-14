"""Tests for the SmartyPlants API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.smartyplants.api import (
    SmartyPlantsClient,
    _parse_plant,
    _parse_reading,
    _parse_thresholds,
)
from custom_components.smartyplants.exceptions import (
    SmartyPlantsAuthError,
    SmartyPlantsConnectionError,
)

from .const import (
    MOCK_ACCESS_TOKEN,
    MOCK_EMAIL,
    MOCK_PASSWORD,
    MOCK_PLANT_ID,
    MOCK_REFRESH_TOKEN,
    MOCK_SENSOR_ID,
    MOCK_USER_ID,
)


def _make_response(status: int, json_data: dict | list | None = None) -> AsyncMock:
    """Create a mock aiohttp response."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)
    # Make it work as an async context manager
    return resp


def _make_session() -> AsyncMock:
    """Create a mock aiohttp ClientSession."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    return session


def _set_post_response(session: AsyncMock, response: AsyncMock) -> None:
    """Configure session.post to return the given response as context manager."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.post.return_value = ctx


def _set_get_response(session: AsyncMock, response: AsyncMock) -> None:
    """Configure session.get to return the given response as context manager."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.get.return_value = ctx


def _set_get_responses(session: AsyncMock, responses: list[AsyncMock]) -> None:
    """Configure session.get to return multiple responses in sequence."""
    ctxs = []
    for resp in responses:
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=resp)
        ctx.__aexit__ = AsyncMock(return_value=False)
        ctxs.append(ctx)
    session.get.side_effect = ctxs


def _login_response_json() -> dict:
    """Return a successful login response body."""
    return {
        "success": True,
        "data": {
            "user": {"userId": MOCK_USER_ID},
            "token": {
                "accessToken": MOCK_ACCESS_TOKEN,
                "refreshToken": MOCK_REFRESH_TOKEN,
            },
        },
        "message": "Login successful",
    }


def _refresh_response_json(new_access_token: str) -> dict:
    """Return a successful token refresh response body."""
    return {
        "success": True,
        "data": {
            "token": {
                "accessToken": new_access_token,
                "refreshToken": None,
            },
        },
        "message": "Token refreshed",
    }


def _plant_api_data() -> dict:
    """Return a single raw plant as the API would return it."""
    return {
        "id": MOCK_PLANT_ID,
        "name": "Monstera",
        "imageUrl": "https://example.com/monstera.jpg",
        "sensor": {
            "id": MOCK_SENSOR_ID,
            "identifier": "SP-001",
            "isOnline": True,
        },
        "plantReference": {
            "scientificNameWithoutAuthor": "Monstera deliciosa",
            "commonNames": ["Swiss cheese plant"],
            "plantConfigurations": [
                {
                    "variant": "TEMPERATURE",
                    "valueOne": 10.0,
                    "valueTwo": 18.0,
                    "valueThree": 27.0,
                    "valueFour": 35.0,
                },
                {
                    "variant": "SALINITY",
                    "valueOne": 0.5,
                    "valueTwo": 1.0,
                    "valueThree": 2.5,
                    "valueFour": 3.5,
                },
            ],
        },
        "sensors": [
            {
                "sensor": {"id": MOCK_SENSOR_ID},
                "sensorData": {
                    "temperature": {
                        "value": 22.5,
                        "status": "OPTIMAL",
                        "message": "Temperature is great",
                    },
                    "humidity": {
                        "value": 55.0,
                        "status": "OPTIMAL",
                        "message": "Humidity is good",
                    },
                    "waterLevel": {
                        "value": 40.0,
                        "status": "LOW",
                        "message": "Needs water",
                    },
                    "light": {
                        "value": 800.0,
                        "status": "OPTIMAL",
                        "message": "Good light",
                    },
                    "nutrient": {
                        "value": 1.5,
                        "status": "OPTIMAL",
                        "message": "Nutrients OK",
                    },
                    "batteryPercent": {
                        "value": 85.0,
                        "status": "OPTIMAL",
                        "message": "Battery good",
                    },
                    "voltage": {
                        "value": 3.7,
                        "status": "OPTIMAL",
                        "message": "Voltage OK",
                    },
                },
            }
        ],
    }


class TestLogin:
    """Tests for login functionality."""

    async def test_login_success(self) -> None:
        """Test successful login returns tokens and user ID."""
        session = _make_session()
        resp = _make_response(201, _login_response_json())
        _set_post_response(session, resp)

        client = SmartyPlantsClient(session)
        result = await client.async_login(MOCK_EMAIL, MOCK_PASSWORD)

        if isinstance(result, Exception):
            raise result
        assert result["user_id"] == MOCK_USER_ID
        assert result["access_token"] == MOCK_ACCESS_TOKEN
        assert result["refresh_token"] == MOCK_REFRESH_TOKEN

    async def test_login_invalid_credentials(self) -> None:
        """Test login with invalid credentials raises AuthError."""
        session = _make_session()
        resp = _make_response(401, {"success": False, "message": "Invalid credentials"})
        _set_post_response(session, resp)

        client = SmartyPlantsClient(session)
        with pytest.raises(SmartyPlantsAuthError):
            await client.async_login(MOCK_EMAIL, "wrong_password")

    async def test_login_connection_error(self) -> None:
        """Test login with connection error raises ConnectionError."""
        session = _make_session()
        session.post.side_effect = aiohttp.ClientError("Connection refused")

        client = SmartyPlantsClient(session)
        with pytest.raises(SmartyPlantsConnectionError):
            await client.async_login(MOCK_EMAIL, MOCK_PASSWORD)


class TestTokenRefresh:
    """Tests for token refresh functionality."""

    async def test_refresh_success(self) -> None:
        """Test successful token refresh returns new access token."""
        session = _make_session()
        new_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJleHAiOjk5OTk5OTk5OTl9.new"  # noqa: E501
        resp = _make_response(201, _refresh_response_json(new_token))
        _set_post_response(session, resp)

        client = SmartyPlantsClient(session)
        # Use an expired access token so refresh is needed
        client.set_tokens(
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjowfQ.x",
            refresh_token=MOCK_REFRESH_TOKEN,
        )

        result = await client.async_refresh_access_token()

        if isinstance(result, Exception):
            raise result
        assert result == new_token

    async def test_refresh_expired_refresh_token(self) -> None:
        """Test refresh with expired refresh token raises AuthError."""
        session = _make_session()
        resp = _make_response(
            401,
            {"success": False, "message": "Refresh token expired"},
        )
        _set_post_response(session, resp)

        client = SmartyPlantsClient(session)
        client.set_tokens(
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjowfQ.x",
            refresh_token=MOCK_REFRESH_TOKEN,
        )

        with pytest.raises(SmartyPlantsAuthError):
            await client.async_refresh_access_token()

    async def test_refresh_calls_callback(self) -> None:
        """Test that token refresh calls the callback with new tokens."""
        session = _make_session()
        new_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJleHAiOjk5OTk5OTk5OTl9.new"  # noqa: E501
        resp = _make_response(201, _refresh_response_json(new_token))
        _set_post_response(session, resp)

        callback = AsyncMock()
        client = SmartyPlantsClient(session)
        client.set_tokens(
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjowfQ.x",
            refresh_token=MOCK_REFRESH_TOKEN,
        )
        client.set_token_updated_callback(callback)

        await client.async_refresh_access_token()

        callback.assert_awaited_once_with(new_token, MOCK_REFRESH_TOKEN)


class TestParsingHelpers:
    """Tests for parsing helper functions."""

    def test_parse_reading_normal(self) -> None:
        """Test parsing a normal sensor reading."""
        raw = {"value": 22.5, "status": "OPTIMAL", "message": "Looking good"}
        result = _parse_reading(raw)
        assert result is not None
        assert result.value == 22.5
        assert result.status == "OPTIMAL"
        assert result.message == "Looking good"

    def test_parse_reading_none(self) -> None:
        """Test parsing None returns None."""
        result = _parse_reading(None)
        assert result is None

    def test_parse_reading_null_value(self) -> None:
        """Test parsing a reading with null value."""
        raw = {"value": None, "status": "LOW", "message": "No data"}
        result = _parse_reading(raw)
        assert result is not None
        assert result.value is None
        assert result.status == "LOW"

    def test_parse_thresholds_temperature(self) -> None:
        """Test parsing temperature thresholds."""
        configs = [
            {
                "variant": "TEMPERATURE",
                "valueOne": 10.0,
                "valueTwo": 18.0,
                "valueThree": 27.0,
                "valueFour": 35.0,
            }
        ]
        result = _parse_thresholds(configs)
        assert "temperature" in result
        t = result["temperature"]
        assert t.critical_low == 10.0
        assert t.low_optimal == 18.0
        assert t.high_optimal == 27.0
        assert t.critical_high == 35.0

    def test_parse_thresholds_salinity_maps_to_nutrient(self) -> None:
        """Test that SALINITY variant maps to 'nutrient' key."""
        configs = [
            {
                "variant": "SALINITY",
                "valueOne": 0.5,
                "valueTwo": 1.0,
                "valueThree": 2.5,
                "valueFour": 3.5,
            }
        ]
        result = _parse_thresholds(configs)
        assert "nutrient" in result
        assert "salinity" not in result

    def test_parse_plant_no_sensor_returns_none(self) -> None:
        """Test that a plant without sensor returns None."""
        raw = {
            "id": MOCK_PLANT_ID,
            "name": "Lonely plant",
            "sensor": None,
        }
        result = _parse_plant(raw)
        assert result is None

    def test_parse_plant_full_data(self) -> None:
        """Test parsing a complete plant with all data."""
        raw = _plant_api_data()
        result = _parse_plant(raw)
        assert result is not None
        assert result.plant_id == MOCK_PLANT_ID
        assert result.name == "Monstera"
        assert result.species == "Monstera deliciosa"
        assert result.common_names == ["Swiss cheese plant"]
        assert result.image_url == "https://example.com/monstera.jpg"
        assert result.sensor_id == MOCK_SENSOR_ID
        assert result.sensor_identifier == "SP-001"
        assert result.sensor_online is True

        # Sensor readings
        assert result.temperature is not None
        assert result.temperature.value == 22.5
        assert result.humidity is not None
        assert result.humidity.value == 55.0
        assert result.moisture is not None
        assert result.moisture.value == 40.0
        assert result.light is not None
        assert result.light.value == 800.0
        assert result.nutrient is not None
        assert result.nutrient.value == 1.5
        assert result.battery is not None
        assert result.battery.value == 85.0
        assert result.voltage is not None
        assert result.voltage.value == 3.7

        # Thresholds
        assert "temperature" in result.thresholds
        assert "nutrient" in result.thresholds
        assert result.thresholds["temperature"].critical_low == 10.0
        assert result.thresholds["nutrient"].critical_low == 0.5


class TestGetPlants:
    """Tests for fetching plants."""

    async def test_get_plants_success(self) -> None:
        """Test successful plant fetch with one plant."""
        session = _make_session()

        plants_resp = _make_response(
            200,
            {
                "success": True,
                "data": [_plant_api_data()],
                "meta": {
                    "page": 1,
                    "limit": 50,
                    "hasNextPage": False,
                    "totalCount": 1,
                },
            },
        )
        _set_get_response(session, plants_resp)

        client = SmartyPlantsClient(session)
        client.set_tokens(MOCK_ACCESS_TOKEN, MOCK_REFRESH_TOKEN)

        result = await client.async_get_plants()

        if isinstance(result, Exception):
            raise result
        assert len(result) == 1
        plant = result[0]
        assert plant.plant_id == MOCK_PLANT_ID
        assert plant.name == "Monstera"
        assert plant.temperature is not None
        assert plant.temperature.value == 22.5

    async def test_get_plants_skips_sensorless(self) -> None:
        """Test that plants without sensors are skipped."""
        session = _make_session()

        plants_resp = _make_response(
            200,
            {
                "success": True,
                "data": [
                    _plant_api_data(),
                    {"id": "no-sensor-plant", "name": "Lonely", "sensor": None},
                ],
                "meta": {"page": 1, "limit": 50, "hasNextPage": False},
            },
        )
        _set_get_response(session, plants_resp)

        client = SmartyPlantsClient(session)
        client.set_tokens(MOCK_ACCESS_TOKEN, MOCK_REFRESH_TOKEN)

        result = await client.async_get_plants()
        assert len(result) == 1

    async def test_get_plants_pagination(self) -> None:
        """Test that pagination fetches all pages."""
        session = _make_session()

        page1_resp = _make_response(
            200,
            {
                "success": True,
                "data": [_plant_api_data()],
                "meta": {"page": 1, "limit": 50, "hasNextPage": True},
            },
        )
        plant2 = _plant_api_data()
        plant2["id"] = "plant-2"
        plant2["name"] = "Ficus"
        page2_resp = _make_response(
            200,
            {
                "success": True,
                "data": [plant2],
                "meta": {"page": 2, "limit": 50, "hasNextPage": False},
            },
        )
        _set_get_responses(session, [page1_resp, page2_resp])

        client = SmartyPlantsClient(session)
        client.set_tokens(MOCK_ACCESS_TOKEN, MOCK_REFRESH_TOKEN)

        result = await client.async_get_plants()
        assert len(result) == 2
        assert result[0].plant_id == MOCK_PLANT_ID
        assert result[1].plant_id == "plant-2"


class TestGetRequiresAttention:
    """Tests for fetching plants that require attention."""

    async def test_requires_attention_returns_ids(self) -> None:
        """Test that requires-attention returns a set of plant IDs."""
        session = _make_session()

        resp = _make_response(
            200,
            {
                "success": True,
                "data": [
                    {"id": "plant-1", "name": "Monstera"},
                    {"id": "plant-2", "name": "Ficus"},
                ],
                "meta": {"page": 1, "limit": 50, "hasNextPage": False},
            },
        )
        _set_get_response(session, resp)

        client = SmartyPlantsClient(session)
        client.set_tokens(MOCK_ACCESS_TOKEN, MOCK_REFRESH_TOKEN)

        result = await client.async_get_requires_attention()

        if isinstance(result, Exception):
            raise result
        assert result == {"plant-1", "plant-2"}
