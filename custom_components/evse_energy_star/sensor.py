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
    # key, id_, name, unit, state_class, device_class
    ("state", "status", "Статус зарядки", None, None, None),
    ("currentSet", "current_set", "Струм (встановлений)", "A", SensorStateClass.MEASUREMENT, SensorDeviceClass.CURRENT),
    ("curMeas1", "current_phase_1", "Струм фаза 1", "A", SensorStateClass.MEASUREMENT, SensorDeviceClass.CURRENT),
    ("voltMeas1", "voltage_phase_1", "Напруга фаза 1", "V", SensorStateClass.MEASUREMENT, SensorDeviceClass.VOLTAGE),
    ("temperature1", "temperature_box", "Темп. корпусу", "°C", SensorStateClass.MEASUREMENT, SensorDeviceClass.TEMPERATURE),
    ("temperature2", "temperature_socket", "Темп. роз'єму", "°C", SensorStateClass.MEASUREMENT, SensorDeviceClass.TEMPERATURE),
    ("leakValue", "leakage", "Витік", "мА", SensorStateClass.MEASUREMENT, None),
    ("sessionEnergy", "session_energy", "Енергія сесії", "kWh", SensorStateClass.TOTAL_INCREASING, SensorDeviceClass.ENERGY),
    ("sessionTime", "session_time", "Час сесії", None, None, None),
    ("totalEnergy", "total_energy", "Загальна енергія", "kWh", SensorStateClass.TOTAL_INCREASING, SensorDeviceClass.ENERGY),
    ("systemTime", "system_time", "Системний час", None, None, None),
]

THREE_PHASE_SENSORS = [
    ("curMeas2", "current_phase_2", "Струм фаза 2", "A", SensorStateClass.MEASUREMENT, SensorDeviceClass.CURRENT),
    ("curMeas3", "current_phase_3", "Струм фаза 3", "A", SensorStateClass.MEASUREMENT, SensorDeviceClass.CURRENT),
    ("voltMeas2", "voltage_phase_2", "Напруга фаза 2", "V", SensorStateClass.MEASUREMENT, SensorDeviceClass.VOLTAGE),
    ("voltMeas3", "voltage_phase_3", "Напруга фаза 3", "V", SensorStateClass.MEASUREMENT, SensorDeviceClass.VOLTAGE),
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entry_id = entry.entry_id

    device_type = entry.options.get("device_type", entry.data.get("device_type", "1_phase"))

    entities = [
        EVSESensor(coordinator, key, id_, name, unit, state_class, device_class, entry_id)
        for key, id_, name, unit, state_class, device_class in SENSOR_DEFINITIONS
    ]

    if device_type == "3_phase":
        entities += [
            EVSESensor(coordinator, key, id_, name, unit, state_class, device_class, entry_id)
            for key, id_, name, unit, state_class, device_class in THREE_PHASE_SENSORS
        ]

    entities.append(EVSEGroundStatus(coordinator, entry_id))
    async_add_entities(entities)

class EVSESensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key, id_, name, unit, state_class, device_class, entry_id):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._key = key
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{id_}_{entry_id}"
        self._entry_id = entry_id
        self._attr_state_class = state_class
        self._attr_device_class = device_class

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