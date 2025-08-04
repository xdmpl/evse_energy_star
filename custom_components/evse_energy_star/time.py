import logging
import aiohttp
import async_timeout
from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TEXT_DEFINITIONS = [
    ("startTime", "start_time", "Час початку зарядки"),
    ("stopTime", "stop_time", "Час завершення зарядки")
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    host = hass.data[DOMAIN][entry.entry_id]["host"]
    entry_id = entry.entry_id
    async_add_entities([
        EVSETimeField(host, key, id_, name, entry_id)
        for key, id_, name in TEXT_DEFINITIONS
    ])

class EVSETimeField(TextEntity):
    def __init__(self, host, key, id_, name, entry_id):
        self._host = host
        self._key = key
        self._id = id_
        self._entry_id = entry_id
        self._attr_name = name
        self._attr_unique_id = f"{id_}_{entry_id}"
        self._attr_native_value = None
        self._attr_min_length = 4
        self._attr_max_length = 5
        self._attr_mode = "text"

    async def async_update(self):
        try:
            async with async_timeout.timeout(5):
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"http://{self._host}/init") as resp:
                        data = await resp.json()
                        value = data.get(self._key)
                        if value is not None:
                            self._attr_native_value = str(value)
        except Exception as err:
            _LOGGER.warning("text.py → помилка оновлення %s → %s", self._key, err)

    async def async_set_value(self, value: str):
        try:
            async with async_timeout.timeout(5):
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"http://{self._host}/init") as resp:
                        data = await resp.json()

                    updated = {
                        "startTime": data.get("startTime"),
                        "stopTime": data.get("stopTime"),
                        "timeZone": data.get("timeZone"),
                        "isAlarm": str(data.get("isAlarm")).lower()
                    }
                    updated[self._key] = value

                    payload = (
                        f"isAlarm={updated['isAlarm']}&"
                        f"startTime={updated['startTime']}&"
                        f"stopTime={updated['stopTime']}&"
                        f"timeZone={updated['timeZone']}"
                    )

                    await session.post(
                        f"http://{self._host}/timer",
                        data=payload,
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                    self._attr_native_value = value
                    self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error("text.py → помилка запису %s = %s → %s", self._key, value, err)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"EVSE Energy Star ({self._host})",
            "manufacturer": "Energy Star",
            "model": "EVSE"
        }