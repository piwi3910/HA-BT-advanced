"""BLE Triangulation integration for Home Assistant."""
import logging
import os
import shutil
from pathlib import Path

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    Platform,
)
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_BEACONS,
    CONF_PROXIES,
    CONF_PROXY_ID,
    CONF_MAC_ADDRESS,
    CONF_TX_POWER,
    CONF_PATH_LOSS_EXPONENT,
    CONF_RSSI_SMOOTHING,
    CONF_POSITION_SMOOTHING,
    CONF_SERVICE_ENABLED,
    DATA_CONFIG,
    DEFAULT_TX_POWER,
    DEFAULT_PATH_LOSS_EXPONENT,
    DEFAULT_RSSI_SMOOTHING,
    DEFAULT_POSITION_SMOOTHING,
    PROXY_CONFIG_DIR,
    BEACON_CONFIG_DIR,
    SERVICE_RESTART,
    SERVICE_ADD_BEACON,
    SERVICE_REMOVE_BEACON,
)
from .manager import TriangulationManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CONFIG]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the BLE Triangulation integration."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BLE Triangulation from a config entry."""
    # Store the entry data
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_CONFIG: dict(entry.data)
    }
    
    # Create config directories if they don't exist
    for directory in [PROXY_CONFIG_DIR, BEACON_CONFIG_DIR]:
        config_dir = Path(hass.config.path(directory))
        if not config_dir.exists():
            _LOGGER.info(f"Creating configuration directory: {config_dir}")
            config_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize manager
    manager = TriangulationManager(hass, entry)
    hass.data[DOMAIN][entry.entry_id]["manager"] = manager
    
    # Register services
    async def handle_restart(call: ServiceCall) -> None:
        """Handle the restart service call."""
        await manager.restart_service()
    
    hass.services.async_register(
        DOMAIN, SERVICE_RESTART, handle_restart
    )
    
    async def handle_add_beacon(call: ServiceCall) -> None:
        """Handle the add_beacon service call."""
        mac_address = call.data.get(CONF_MAC_ADDRESS)
        name = call.data.get(CONF_NAME)
        await manager.add_beacon(mac_address, name)
    
    hass.services.async_register(
        DOMAIN, 
        SERVICE_ADD_BEACON, 
        handle_add_beacon, 
        schema=vol.Schema({
            vol.Required(CONF_MAC_ADDRESS): cv.string,
            vol.Required(CONF_NAME): cv.string,
        })
    )
    
    async def handle_remove_beacon(call: ServiceCall) -> None:
        """Handle the remove_beacon service call."""
        mac_address = call.data.get(CONF_MAC_ADDRESS)
        await manager.remove_beacon(mac_address)
    
    hass.services.async_register(
        DOMAIN, 
        SERVICE_REMOVE_BEACON, 
        handle_remove_beacon, 
        schema=vol.Schema({
            vol.Required(CONF_MAC_ADDRESS): cv.string,
        })
    )
    
    # Start the manager
    if entry.data.get(CONF_SERVICE_ENABLED, True):
        await manager.start()
    
    # Load the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop the manager
    manager = hass.data[DOMAIN][entry.entry_id]["manager"]
    await manager.stop()
    
    # Unload the platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    # Remove the entry data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)