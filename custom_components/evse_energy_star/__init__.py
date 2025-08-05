import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from .coordinator import EVSECoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "select", "button", "number", "switch", "time"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data.get("host")
    coordinator = EVSECoordinator(hass, host, entry)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "host": host
    }

    _LOGGER.warning("__init__.py → Створено coordinator з host: %s", host)

    await coordinator.async_config_entry_first_refresh()
    # Завантаження платформ
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Гарантоване автоматичне розвантаження при видаленні інтеграції
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload EVSE config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)