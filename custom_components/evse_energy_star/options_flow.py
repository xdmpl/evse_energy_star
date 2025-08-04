from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class EVSEEnergyStarOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=user_input
            )

            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]["coordinator"]
            coordinator.host = user_input.get("host")
            await coordinator.async_request_refresh()

            return self.async_create_entry(title=DOMAIN, data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("host", default=self.config_entry.data.get("host", "")): str,
                vol.Optional("username", default=self.config_entry.data.get("username", "")): str,
                vol.Optional("password", default=self.config_entry.data.get("password", "")): str,
            }),
        )

def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    return EVSEEnergyStarOptionsFlow(config_entry)