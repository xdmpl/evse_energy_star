import logging
from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, STATUS_MAP

_LOGGER = logging.getLogger(__name__)

SENSOR_DEFINITIONS = [
    ("state", "status", "Статус зарядки", None),
    ("currentSet", "current_set", "Струм (встановлений)", "A"),
    ("curMeas1", "current_phase_1", "Струм фаза 1", "A"),
    ("voltMeas1", "voltage_phase_1", "Напруга фаза 1", "V"),
    ("temperature1", "temperature_box", "Темп. корпусу", "°C"),
    ("temperature2", "temperature_socket", "Темп. роз'єму", "°C"),
    ("leakValue", "leakage", "Витік", "мА"),
    ("sessionEnergy", "session_energy", "Енергія сесії", "kWh"),
    ("sessionTime", "session_time", "Час сесії", None),
    ("totalEnergy", "total_energy", "Загальна енергія", "kWh"),
    ("systemTime", "system_time", "Системний час", None),
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entry_id = entry.entry_id

    entities = [
        EVSESensor(coordinator, key, id_, name, unit, entry_id)
        for key, id_, name, unit in SENSOR_DEFINITIONS
    ]

    entities.append(EVSEGroundStatus(coordinator, entry_id))
    async_add_entities(entities)

class EVSESensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key, id_, name, unit, entry_id):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._key = key
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{id_}_{entry_id}"
        self._entry_id = entry_id

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        value = self.coordinator.data.get(self._key)
        if value is None:
            return None
        try:
            if self._key == "curMeas1":
                return round(float(value) / 10, 2)
            if self._key in ["sessionEnergy", "totalEnergy"]:
                return round(float(value) / 10, 3)
            if self._key == "sessionTime":
                total_sec = int(float(value))
                h = total_sec // 3600
                m = (total_sec % 3600) // 60
                s = total_sec % 60
                return f"{h:02}:{m:02}:{s:02}"
            if self._key == "state":
                return STATUS_MAP.get(value, "Невідомо")
            return value
        except Exception as err:
            _LOGGER.warning("sensor.py → помилка в обробці %s: %s", self._key, repr(err))
            return str(value)

    def _handle_coordinator_update(self):
        new_value = self.coordinator.data.get(self._key)
        if self._key == "systemTime":
            try:
                old_str = str(self._attr_native_value)
                new_str = str(new_value)
                fmt = "%H:%M:%S"
                old_dt = datetime.strptime(old_str, fmt)
                new_dt = datetime.strptime(new_str, fmt)
                if abs((new_dt - old_dt).total_seconds()) <= 2:
                    return
            except Exception as err:
                _LOGGER.debug("sensor.py → systemTime порівняння: %s", repr(err))

        self._attr_native_value = new_value
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"EVSE Energy Star ({self.coordinator.host})",
            "manufacturer": "Energy Star",
            "model": "EVSE",
            "sw_version": self.coordinator.data.get("fwVersion")
        }

class EVSEGroundStatus(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._entry_id = entry_id
        self._attr_name = "Заземлення"
        self._attr_unique_id = f"ground_status_{entry_id}"

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        return "✅" if bool(self.coordinator.data.get("ground", 0)) else "❌"

    @property
    def icon(self):
        return "mdi:checkbox-marked-circle" if self.native_value == "✅" else "mdi:close-circle-outline"

    def _handle_coordinator_update(self):
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"EVSE Energy Star ({self.coordinator.host})",
            "manufacturer": "Energy Star",
            "model": "EVSE",
            "sw_version": self.coordinator.data.get("fwVersion")
        }