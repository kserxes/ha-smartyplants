"""Tests for the SmartyPlants config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.smartyplants.const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    OPT_SCAN_INTERVAL,
    OPT_SHOW_STATUS_SENSORS,
)
from custom_components.smartyplants.exceptions import (
    SmartyPlantsAuthError,
    SmartyPlantsConnectionError,
)

from .const import (
    MOCK_ACCESS_TOKEN,
    MOCK_EMAIL,
    MOCK_PASSWORD,
    MOCK_REFRESH_TOKEN,
    MOCK_USER_ID,
)

PATCH_CLIENT = "custom_components.smartyplants.config_flow.SmartyPlantsClient"
PATCH_SESSION = (
    "custom_components.smartyplants.config_flow.async_get_clientsession"
)


def _mock_login_success(client_mock: AsyncMock) -> None:
    """Configure the client mock to return a successful login."""
    client_mock.return_value.async_login = AsyncMock(
        return_value={
            "user_id": MOCK_USER_ID,
            "access_token": MOCK_ACCESS_TOKEN,
            "refresh_token": MOCK_REFRESH_TOKEN,
        }
    )


class TestUserStep:
    """Tests for the user config flow step."""

    async def test_show_form(self, hass: HomeAssistant) -> None:
        """Test that the form is shown on init."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    async def test_success(self, hass: HomeAssistant) -> None:
        """Test successful login creates an entry."""
        with (
            patch(PATCH_CLIENT) as client_mock,
            patch(PATCH_SESSION),
        ):
            _mock_login_success(client_mock)

            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_USER},
                data={CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: MOCK_PASSWORD},
            )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == MOCK_EMAIL
        assert result["data"][CONF_EMAIL] == MOCK_EMAIL
        assert result["data"][CONF_ACCESS_TOKEN] == MOCK_ACCESS_TOKEN
        assert result["data"][CONF_REFRESH_TOKEN] == MOCK_REFRESH_TOKEN
        assert CONF_PASSWORD not in result["data"]

    async def test_invalid_credentials(self, hass: HomeAssistant) -> None:
        """Test that invalid credentials show an error."""
        with (
            patch(PATCH_CLIENT) as client_mock,
            patch(PATCH_SESSION),
        ):
            client_mock.return_value.async_login = AsyncMock(
                side_effect=SmartyPlantsAuthError("Bad creds"),
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_USER},
                data={CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: "wrong"},
            )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}

    async def test_connection_error(self, hass: HomeAssistant) -> None:
        """Test that a connection error shows an error."""
        with (
            patch(PATCH_CLIENT) as client_mock,
            patch(PATCH_SESSION),
        ):
            client_mock.return_value.async_login = AsyncMock(
                side_effect=SmartyPlantsConnectionError("Timeout"),
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_USER},
                data={CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: MOCK_PASSWORD},
            )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}

    async def test_unknown_error(self, hass: HomeAssistant) -> None:
        """Test that an unknown error shows a generic error."""
        with (
            patch(PATCH_CLIENT) as client_mock,
            patch(PATCH_SESSION),
        ):
            client_mock.return_value.async_login = AsyncMock(
                side_effect=RuntimeError("Something broke"),
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_USER},
                data={CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: MOCK_PASSWORD},
            )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}

    async def test_duplicate_entry(self, hass: HomeAssistant) -> None:
        """Test that a duplicate account aborts."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        existing = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_USER_ID,
            data={
                CONF_EMAIL: MOCK_EMAIL,
                CONF_ACCESS_TOKEN: MOCK_ACCESS_TOKEN,
                CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
            },
        )
        existing.add_to_hass(hass)

        with (
            patch(PATCH_CLIENT) as client_mock,
            patch(PATCH_SESSION),
        ):
            _mock_login_success(client_mock)

            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_USER},
                data={CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: MOCK_PASSWORD},
            )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


class TestReauthStep:
    """Tests for the re-authentication flow."""

    async def test_reauth_success(self, hass: HomeAssistant) -> None:
        """Test successful re-authentication updates the entry."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_USER_ID,
            data={
                CONF_EMAIL: MOCK_EMAIL,
                CONF_ACCESS_TOKEN: "old_token",
                CONF_REFRESH_TOKEN: "old_refresh",
            },
        )
        entry.add_to_hass(hass)

        result = await entry.start_reauth_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        with (
            patch(PATCH_CLIENT) as client_mock,
            patch(PATCH_SESSION),
        ):
            _mock_login_success(client_mock)

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    CONF_EMAIL: MOCK_EMAIL,
                    CONF_PASSWORD: MOCK_PASSWORD,
                },
            )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"
        assert entry.data[CONF_ACCESS_TOKEN] == MOCK_ACCESS_TOKEN
        assert entry.data[CONF_REFRESH_TOKEN] == MOCK_REFRESH_TOKEN

    async def test_reauth_invalid_credentials(
        self, hass: HomeAssistant
    ) -> None:
        """Test that invalid credentials during reauth show an error."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_USER_ID,
            data={
                CONF_EMAIL: MOCK_EMAIL,
                CONF_ACCESS_TOKEN: "old_token",
                CONF_REFRESH_TOKEN: "old_refresh",
            },
        )
        entry.add_to_hass(hass)

        result = await entry.start_reauth_flow(hass)

        with (
            patch(PATCH_CLIENT) as client_mock,
            patch(PATCH_SESSION),
        ):
            client_mock.return_value.async_login = AsyncMock(
                side_effect=SmartyPlantsAuthError("Bad creds"),
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    CONF_EMAIL: MOCK_EMAIL,
                    CONF_PASSWORD: "wrong",
                },
            )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


class TestOptionsFlow:
    """Tests for the options flow."""

    async def test_options_defaults(self, hass: HomeAssistant) -> None:
        """Test configuring options with new values."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_USER_ID,
            data={
                CONF_EMAIL: MOCK_EMAIL,
                CONF_ACCESS_TOKEN: MOCK_ACCESS_TOKEN,
                CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
            },
        )
        entry.add_to_hass(hass)

        # Mock the setup to avoid actually setting up the integration
        with patch(
            "custom_components.smartyplants.async_setup_entry",
            return_value=True,
            create=True,
        ):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                OPT_SCAN_INTERVAL: 10,
                OPT_SHOW_STATUS_SENSORS: True,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][OPT_SCAN_INTERVAL] == 10
        assert result["data"][OPT_SHOW_STATUS_SENSORS] is True
