import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import EntityDescription
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TIMEZONE_OPTIONS = [str(i) for i in range(-12, 13)]
UPDATE_RATE_OPTIONS = [str(i) for i in [1, 2, 5, 10, 15, 30, 60]]
UPDATE_RATE_DESCRIPTION = SelectEntityDescription(
    key="refresh_rate",
    name=None,
    icon="mdi:history",
    translation_key="refresh_rate"
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entry_id = entry.entry_id

    async_add_entities([
        TimeZoneSelect(coordinator, entry_id),
        UpdateRateSelect(hass, entry, entry_id)
    ])

class TimeZoneSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._entry_id = entry_id
        self._attr_name = "Часова зона"
        self._attr_translation_key = "time_zone"
        self.entity_description = SelectEntityDescription(
            key="time_zone",
            translation_key="time_zone",
            icon="mdi:map-clock-outline"
        )
        self._attr_has_entity_name = True
        self._attr_unique_id = f"time_zone_{entry_id}"
        self._attr_options = TIMEZONE_OPTIONS
        self._attr_current_option = None

        raw = self.coordinator.data.get("timeZone", "0")
        try:
            tz_int = int(float(str(raw).strip()))
            tz_str = str(tz_int)
        except Exception:
            tz_str = "0"

        if tz_str in self._attr_options:
            self._attr_current_option = tz_str
            _LOGGER.debug("select.py → timeZone з /init: %s (%s)", tz_str, type(raw).__name__)
        else:
            self._attr_current_option = None
            _LOGGER.warning("select.py → невірне значення timeZone з /init: '%s'", raw)

    async def async_select_option(self, option: str):
        session = async_get_clientsession(self.coordinator.hass)
        payload = f"isAlarm=false&startTime=None&stopTime=None&timeZone={option}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            await session.post(
                f"http://{self.coordinator.host}/timer",
                data=payload,
                headers=headers
            )
            self._attr_current_option = option
            await self.coordinator.async_request_refresh()
            self.async_write_ha_state()
            _LOGGER.debug("select.py → timeZone змінено на %s через /timer", option)
        except Exception as err:
            _LOGGER.error("select.py → помилка запиту /timer: timeZone=%s → %s", option, repr(err))

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"EVSE Energy Star ({self.coordinator.host})",
            "manufacturer": "Energy Star",
            "model": "EVSE",
            "sw_version": self.coordinator.data.get("fwVersion")
        }

class UpdateRateSelect(SelectEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, entry_id: str):
        super().__init__()
        self.hass = hass
        self.config_entry = config_entry
        self._entry_id = entry_id
        self._attr_name = "Частота оновлення"
        self._attr_translation_key = "refresh_rate"
        self.entity_description = SelectEntityDescription(
            key="refresh_rate",
            translation_key="refresh_rate",
            icon="mdi:history"
        )
        self._attr_has_entity_name = True
        self._attr_unique_id = f"refresh_rate_{entry_id}"
        self._attr_options = UPDATE_RATE_OPTIONS
        self._attr_current_option = str(config_entry.options.get("update_rate", 10))

    async def async_select_option(self, option: str):
        try:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={**self.config_entry.options, "update_rate": int(option)}
            )
            self._attr_current_option = option
            self.async_write_ha_state()
            _LOGGER.info("select.py → update_rate змінено на %s сек", option)
        except Exception as err:
            _LOGGER.error("select.py → помилка запису update_rate=%s → %s", option, repr(err))

    @property
    def available(self):
        return True

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"EVSE Energy Star ({self.config_entry.data.get('host')})",
            "manufacturer": "Energy Star",
            "model": "EVSE",
            "sw_version": self.config_entry.options.get("fwVersion")
        }