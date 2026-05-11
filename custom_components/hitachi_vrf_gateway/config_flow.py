"""Config flow for Hitachi VRF Gateway."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import HitachiGatewayApi
from .const import (
    CONF_DEVICES,
    CONF_GATEWAY_NAME,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_NAME,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class HitachiVrfGatewayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Hitachi VRF Gateway."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Show the setup form and validate input."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]
            verify_ssl = user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)

            # Prevent duplicate gateways
            await self.async_set_unique_id(f"{host}::{username}")
            self._abort_if_unique_id_configured()

            # Test login before saving
            api = HitachiGatewayApi(
                host=host,
                username=username,
                password=password,
                verify_ssl=verify_ssl,
            )
            login_ok = await api.async_login()
            await api.async_close()

            if login_ok:
                return self.async_create_entry(
                    title=user_input.get(CONF_GATEWAY_NAME) or host,
                    data={
                        CONF_GATEWAY_NAME: user_input.get(CONF_GATEWAY_NAME, DEFAULT_NAME),
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_VERIFY_SSL: verify_ssl,
                        CONF_DEVICES: user_input.get(CONF_DEVICES, "0,1,2"),
                    },
                )
            else:
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_GATEWAY_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                vol.Required(CONF_DEVICES, default="0,1,2"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
