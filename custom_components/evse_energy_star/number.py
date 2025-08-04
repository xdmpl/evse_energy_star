import logging
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

NUMBER_DEFINITIONS = [
    {
        "key": "currentSet",
        "id": "current_limit",
        "name": "Обмеження струму",
        "icon": "mdi:current-dc",
        "min": 6,
        "max": 32,
        "step": 1,
        "unit": "A"
    },
    {
        "key": "aiVoltage",
        "id": "voltage_adaptive",
        "name": "Адаптивна напруга",
        "icon": "mdi:flash-outline",
        "min": 180,
        "max": 240,
        "step": 1,
        "unit": "V"
    }
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entry_id = entry.entry_id

    entities = [
        EVSENumber(coordinator, entry_id, definition)
        for definition in NUMBER_DEFINITIONS
    ]
    async_add_entities(entities)

class EVSENumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, entry_id, config):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._host = coordinator.host
        self._key = config["key"]
        self._id = config["id"]
        self._config = config
        self._entry_id = entry_id

        self._attr_name = config["name"]
        self._attr_icon = config["icon"]
        self._attr_native_unit_of_measurement = config["unit"]
        self._attr_native_step = config["step"]
        self._attr_native_min_value = config["min"]
        self._attr_unique_id = f"{self._id}_{entry_id}"
        self._restricted_mode = False

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        value = self.coordinator.data.get(self._key)
        return float(value) if value is not None else None

    @property
    def native_max_value(self):
        if self._key == "currentSet":
            current = self.coordinator.data.get("currentSet")
            if current is not None:
                self._restricted_mode = float(current) <= 16
            design_max = float(self.coordinator.data.get("curDesign", 32))
            return 16 if self._restricted_mode else design_max
        return self._config["max"]

    async def async_set_native_value(self, value: float):
        payload = f"{self._key}={value}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "pageEvent": self._key
        }

        try:
            session = async_get_clientsession(self.coordinator.hass)
            await session.post(
                f"http://{self._host}/pageEvent",
                data=payload,
                headers=headers
            )
            await self.coordinator.async_request_refresh()
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error("number.py → помилка запису %s = %s → %s", self._key, value, repr(err))

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"EVSE Energy Star ({self._host})",
            "manufacturer": "Energy Star",
            "model": "EVSE",
            "sw_version": self.coordinator.data.get("fwVersion")
        }