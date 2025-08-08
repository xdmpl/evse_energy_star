from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN
from .options_flow import EVSEEnergyStarOptionsFlow
from homeassistant.helpers import selector
from homeassistant.helpers.translation import async_get_translations
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
            device_name = user_input.get("device_name", "").strip()

            if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
                errors["host"] = "invalid_ip"

            if not device_name:
                errors["device_name"] = "required"

            if not errors:
                # Отримуємо перекладений заголовок з translations/<lang>.json
                translations = await async_get_translations(
                    self.hass,
                    self.hass.config.language,
                    "title"
                )
                integration_title = translations.get(
                    f"component.{DOMAIN}.title",
                    "EVSE Energy Star"
                )

                # Назва інтеграції = введене ім'я пристрою
                return self.async_create_entry(
                    title=device_name,
                    data={
                        "host": host,
                        "username": user_input.get("username", ""),
                        "password": user_input.get("password", ""),
                        "device_type": user_input.get("device_type"),
                        "device_name": device_name,
                        "integration_title": integration_title
                    }
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("device_name", default="Eveus Pro"): str,
                vol.Required("host", default=""): str,
                vol.Optional("username", default=""): str,
                vol.Optional("password", default=""): str,
                vol.Required("device_type", default="1_phase"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=DEVICE_TYPES,
                        translation_key="device_type",
                        sort=True,
                    )
                ),
            }),
            errors=errors
        )

    async def async_step_reauth(self, user_input=None):
        return await self.async_step_user(user_input)
