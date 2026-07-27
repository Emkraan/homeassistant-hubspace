"""Config flow for the Hubspace integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
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

from .aioafero.errors import (
    ExceededMaximumRetries,
    InvalidAuth,
    InvalidOTP,
    OTPRequired,
)
from .aioafero.v1 import AferoBridgeV1
from .const import (
    CONF_DISCOVERY_INTERVAL,
    CONF_POLLING_INTERVAL,
    CONF_REFRESH_TOKEN,
    CONF_STALE_GRACE_MINUTES,
    CONF_TOLERATE_STALE_DATA,
    DEFAULT_DISCOVERY_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_STALE_GRACE_MINUTES,
    DEFAULT_TOLERATE_STALE_DATA,
    DOMAIN,
    MIN_POLLING_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class HubspaceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hubspace."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._username: str | None = None
        self._password: str | None = None
        self._bridge: AferoBridgeV1 | None = None
        self._otp_required: bool = False
        self._reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect Hubspace account credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            self._bridge = AferoBridgeV1(
                self._username,
                self._password,
                session=async_get_clientsession(self.hass),
            )
            errors = await self._try_login()
            if not errors:
                if self._otp_required:
                    return await self.async_step_otp()
                return self._create_entry()

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.EMAIL)
                    ),
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
        )

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect a one-time-passcode when the account has MFA enabled."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self._bridge.otp_login(user_input["otp_code"])
            except InvalidOTP:
                errors["base"] = "invalid_otp"
            except (aiohttp.ClientError, TimeoutError, ExceededMaximumRetries):
                errors["base"] = "cannot_connect"
            else:
                return self._create_entry()

        return self.async_show_form(
            step_id="otp",
            errors=errors,
            data_schema=vol.Schema({vol.Required("otp_code"): str}),
        )

    async def _try_login(self) -> dict[str, str]:
        """Attempt login on self._bridge, stashing OTP state on the same instance."""
        self._otp_required = False
        try:
            await self._bridge.get_account_id()
        except OTPRequired:
            self._otp_required = True
        except InvalidAuth:
            return {"base": "invalid_auth"}
        except (aiohttp.ClientError, TimeoutError, ExceededMaximumRetries):
            return {"base": "cannot_connect"}
        except Exception:  # noqa: BLE001 - surface anything unexpected as "unknown"
            _LOGGER.exception("Unexpected error during Hubspace login")
            return {"base": "unknown"}
        return {}

    def _create_entry(self) -> ConfigFlowResult:
        data = {
            CONF_USERNAME: self._username,
            CONF_PASSWORD: self._password,
            CONF_REFRESH_TOKEN: self._bridge.refresh_token,
        }
        if self._reauth_entry is not None:
            return self.async_update_reload_and_abort(
                self._reauth_entry, data=data, reason="reauth_successful"
            )
        return self.async_create_entry(title="Hubspace", data=data)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauthentication triggered by an invalid stored credential."""
        self._reauth_entry = self._get_reauth_entry()
        self._username = entry_data[CONF_USERNAME]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-collect only the password."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._password = user_input[CONF_PASSWORD]
            errors = await self._try_login()
            if not errors:
                if self._bridge is not None:
                    return self._create_entry()
                return await self.async_step_otp()

        return self.async_show_form(
            step_id="reauth_confirm",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            description_placeholders={"username": self._username or ""},
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> HubspaceOptionsFlow:
        """Return the options flow handler."""
        return HubspaceOptionsFlow()


class HubspaceOptionsFlow(OptionsFlow):
    """Options for polling interval and stale-data tolerance."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLLING_INTERVAL,
                        default=options.get(
                            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_POLLING_INTERVAL,
                            max=300,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Required(
                        CONF_DISCOVERY_INTERVAL,
                        default=options.get(
                            CONF_DISCOVERY_INTERVAL, DEFAULT_DISCOVERY_INTERVAL
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=300,
                            max=86400,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Required(
                        CONF_TOLERATE_STALE_DATA,
                        default=options.get(
                            CONF_TOLERATE_STALE_DATA, DEFAULT_TOLERATE_STALE_DATA
                        ),
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_STALE_GRACE_MINUTES,
                        default=options.get(
                            CONF_STALE_GRACE_MINUTES, DEFAULT_STALE_GRACE_MINUTES
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=120,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="min",
                        )
                    ),
                }
            ),
        )
