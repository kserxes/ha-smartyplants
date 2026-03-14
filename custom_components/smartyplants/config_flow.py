"""Config flow for the SmartyPlants integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import SmartyPlantsClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    OPT_SCAN_INTERVAL,
    OPT_SHOW_STATUS_SENSORS,
)
from .exceptions import SmartyPlantsAuthError, SmartyPlantsConnectionError

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL),
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD),
        ),
    }
)


class SmartyPlantsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartyPlants."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await self._async_validate_and_create(user_input)
            if not errors:
                return await self._async_create_entry_from_result(user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=USER_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> ConfigFlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle re-authentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await self._async_validate_and_create(user_input)
            if not errors:
                reauth_entry = self._get_reauth_entry()
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_ACCESS_TOKEN: self._login_result["access_token"],
                        CONF_REFRESH_TOKEN: self._login_result["refresh_token"],
                    },
                )

        reauth_entry = self._get_reauth_entry()
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL,
                        default=reauth_entry.data.get(CONF_EMAIL, ""),
                    ): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.EMAIL),
                    ),
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD),
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: Any,
    ) -> SmartyPlantsOptionsFlow:
        """Return the options flow handler."""
        return SmartyPlantsOptionsFlow()

    async def _async_validate_and_create(
        self,
        user_input: dict[str, Any],
    ) -> dict[str, str]:
        """Validate credentials and store the login result. Returns errors dict."""
        errors: dict[str, str] = {}
        try:
            session = async_get_clientsession(self.hass)
            client = SmartyPlantsClient(session)
            result = await client.async_login(
                user_input[CONF_EMAIL],
                user_input[CONF_PASSWORD],
            )
        except SmartyPlantsAuthError:
            errors["base"] = "invalid_auth"
        except SmartyPlantsConnectionError:
            errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected exception during login")
            errors["base"] = "unknown"
        else:
            self._login_result = result
        return errors

    async def _async_create_entry_from_result(
        self,
        user_input: dict[str, Any],
    ) -> ConfigFlowResult:
        """Create a config entry from a successful login."""
        result = self._login_result
        await self.async_set_unique_id(result["user_id"])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=user_input[CONF_EMAIL],
            data={
                CONF_EMAIL: user_input[CONF_EMAIL],
                CONF_ACCESS_TOKEN: result["access_token"],
                CONF_REFRESH_TOKEN: result["refresh_token"],
            },
        )


class SmartyPlantsOptionsFlow(OptionsFlow):
    """Handle options for SmartyPlants."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        OPT_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            OPT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="minutes",
                        ),
                    ),
                    vol.Required(
                        OPT_SHOW_STATUS_SENSORS,
                        default=self.config_entry.options.get(
                            OPT_SHOW_STATUS_SENSORS, False
                        ),
                    ): BooleanSelector(),
                }
            ),
        )
