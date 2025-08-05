from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN
from .options_flow import EVSEEnergyStarOptionsFlow
from homeassistant.helpers import selector
import re

DEVICE_TYPES = ["1_phase", "3_phase"]

class EVSEEnergyStarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """EVSE Energy Star Config Flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    def async_get_options_flow(config_entry):
        return EVSEEnergyStarOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input.get("host")

            if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
                errors["host"] = "invalid_ip"

            if not errors:
                return self.async_create_entry(title=DOMAIN, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host", default=""): str,
                vol.Optional("username", default=""): str,
                vol.Optional("password", default=""): str,
                vol.Required("device_type", default="1_phase"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=DEVICE_TYPES,
                        translation_key="device_type",  # ✅ Це дозволено тут
                        sort=True,
                    )
                ),
            }),
            errors=errors
        )

    async def async_step_reauth(self, user_input=None):
        return await self.async_step_user(user_input)