import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SWITCH_DEFINITIONS = [
    ("groundCtrl", "control_pe", "Контроль заземлення"),
    ("restrictedMode", "restricted_mode", "Режим 16А"),
]

async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entry_id = entry.entry_id

    entities = [
        EVSESwitch(coordinator, key, id_, name, entry_id)
        for key, id_, name in SWITCH_DEFINITIONS
    ]

    entities.append(EVSEScheduleSwitch(coordinator, entry_id))
    entities.append(EVSESimpleSwitch(coordinator, "oneCharge", "one_charge", "Один заряд", entry_id))
    entities.append(EVSESimpleSwitch(coordinator, "aiMode", "adaptive_mode", "Адаптивний режим", entry_id))

    async_add_entities(entities)

class EVSESwitch(SwitchEntity):
    def __init__(self, coordinator, key, id_, name, entry_id):
        self.coordinator = coordinator
        self._host = coordinator.host
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{id_}_{entry_id}"
        self._entry_id = entry_id

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def is_on(self):
        if self._key == "restrictedMode":
            return float(self.coordinator.data.get("currentSet", 32)) <= 16
        return bool(self.coordinator.data.get(self._key))

    async def async_turn_on(self):
        if self._key == "restrictedMode":
            await self._set_current_if_needed(12, only_if_high=True)
        else:
            await self._send_event(True)

    async def async_turn_off(self):
        if self._key == "restrictedMode":
            await self._set_current_if_needed(16, only_if_low=True)
        else:
            await self._send_event(False)

    async def _send_event(self, state: bool):
        payload = f"{self._key}={'1' if state else '0'}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "pageEvent": self._key
        }
        session = async_get_clientsession(self.coordinator.hass)
        try:
            await session.post(f"http://{self._host}/pageEvent", data=payload, headers=headers)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("switch.py → помилка запиту %s → %s", self._key, repr(err))

    async def _set_current_if_needed(self, target, only_if_high=False, only_if_low=False):
        current = float(self.coordinator.data.get("currentSet", 32))
        if (only_if_high and current > target) or (only_if_low and current <= target):
            payload = f"currentSet={target}"
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "pageEvent": "currentSet"
            }
            session = async_get_clientsession(self.coordinator.hass)
            await session.post(f"http://{self._host}/pageEvent", data=payload, headers=headers)
            await self.coordinator.async_request_refresh()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"EVSE Energy Star ({self._host})",
            "manufacturer": "Energy Star",
            "model": "EVSE",
            "sw_version": self.coordinator.data.get("fwVersion")
        }

class EVSEScheduleSwitch(SwitchEntity):
    def __init__(self, coordinator, entry_id):
        self.coordinator = coordinator
        self._host = coordinator.host
        self._entry_id = entry_id
        self._attr_name = "Заряджати за розкладом"
        self._attr_unique_id = f"schedule_{entry_id}"

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def is_on(self):
        value = self.coordinator.data.get("isAlarm")
        return str(value).lower() in ["true", "1"]

    async def async_turn_on(self):
        await self._send(True)

    async def async_turn_off(self):
        await self._send(False)

    async def _send(self, state: bool):
        data = self.coordinator.data
        if not data:
            _LOGGER.warning("switch.py → coordinator.data порожній, розклад не оновлено")
            return

        payload = (
            f"isAlarm={'true' if state else 'false'}&"
            f"startTime={data.get('startTime')}&"
            f"stopTime={data.get('stopTime')}&"
            f"timeZone={data.get('timeZone')}"
        )
        session = async_get_clientsession(self.coordinator.hass)
        try:
            await session.post(f"http://{self._host}/timer", data=payload, headers={
                "Content-Type": "application/x-www-form-urlencoded"
            })
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("switch.py → помилка оновлення розкладу → %s", repr(err))

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"EVSE Energy Star ({self._host})",
            "manufacturer": "Energy Star",
            "model": "EVSE",
            "sw_version": self.coordinator.data.get("fwVersion")
        }

class EVSESimpleSwitch(SwitchEntity):
    def __init__(self, coordinator, key, id_, name, entry_id):
        self.coordinator = coordinator
        self._host = coordinator.host
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{id_}_{entry_id}"
        self._entry_id = entry_id

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def is_on(self):
        val = self.coordinator.data.get(self._key) or self.coordinator.data.get("aiStatus") if self._key == "aiMode" else None
        return str(val).lower() in ["true", "1"]

    async def async_turn_on(self):
        await self._send(True)

    async def async_turn_off(self):
        await self._send(False)

    async def _send(self, state: bool):
        payload = f"{self._key}={'1' if state else '0'}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "pageEvent": self._key
        }
        session = async_get_clientsession(self.coordinator.hass)
        try:
            await session.post(f"http://{self._host}/pageEvent", data=payload, headers=headers)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("switch.py → помилка запиту %s → %s", self._key, repr(err))

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"EVSE Energy Star ({self._host})",
            "manufacturer": "Energy Star",
            "model": "EVSE",
            "sw_version": self.coordinator.data.get("fwVersion")
        }