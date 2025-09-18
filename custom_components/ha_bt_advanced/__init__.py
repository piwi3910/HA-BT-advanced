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
    CONF_ICON,
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
    CONF_MAX_READING_AGE,
    CONF_MIN_PROXIES,
    CONF_SERVICE_ENABLED,
    CONF_BEACON_CATEGORY,
    CONF_BEACON_ICON,
    CONF_ZONE_ID,
    CONF_ZONE_NAME,
    CONF_ZONE_TYPE,
    CONF_ZONE_COORDINATES,
    DATA_CONFIG,
    DATA_MANAGER,
    DEFAULT_TX_POWER,
    DEFAULT_PATH_LOSS_EXPONENT,
    DEFAULT_RSSI_SMOOTHING,
    DEFAULT_POSITION_SMOOTHING,
    PROXY_CONFIG_DIR,
    BEACON_CONFIG_DIR,
    ZONE_CONFIG_DIR,
    SERVICE_RESTART,
    SERVICE_ADD_BEACON,
    SERVICE_REMOVE_BEACON,
    SERVICE_ADD_PROXY,
    SERVICE_REMOVE_PROXY,
    SERVICE_ADD_ZONE,
    SERVICE_REMOVE_ZONE,
    SERVICE_CALIBRATE,
    BEACON_CATEGORY_PERSON,
    BEACON_CATEGORY_ITEM,
    BEACON_CATEGORY_PET,
    BEACON_CATEGORY_VEHICLE,
    BEACON_CATEGORY_OTHER,
)
from .manager import TriangulationManager
import homeassistant.helpers.entity_component

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR, Platform.BINARY_SENSOR]

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
    for directory in [PROXY_CONFIG_DIR, BEACON_CONFIG_DIR, ZONE_CONFIG_DIR]:
        config_dir = Path(hass.config.path(directory))
        if not config_dir.exists():
            _LOGGER.info(f"Creating configuration directory: {config_dir}")
            config_dir.mkdir(parents=True, exist_ok=True)

    # Initialize manager
    manager = TriangulationManager(hass, entry)
    hass.data[DOMAIN][entry.entry_id][DATA_MANAGER] = manager

    # For backward compatibility with any code that might use 'manager' string key
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
        category = call.data.get(CONF_BEACON_CATEGORY, BEACON_CATEGORY_ITEM)
        icon = call.data.get(CONF_BEACON_ICON)
        tx_power = call.data.get(CONF_TX_POWER)
        path_loss_exponent = call.data.get(CONF_PATH_LOSS_EXPONENT)
        
        await manager.add_beacon(
            mac_address=mac_address,
            name=name,
            category=category,
            icon=icon,
            tx_power=tx_power,
            path_loss_exponent=path_loss_exponent
        )
    
    hass.services.async_register(
        DOMAIN, 
        SERVICE_ADD_BEACON, 
        handle_add_beacon, 
        schema=vol.Schema({
            vol.Required(CONF_MAC_ADDRESS): cv.string,
            vol.Required(CONF_NAME): cv.string,
            vol.Optional(CONF_BEACON_CATEGORY): vol.In([
                BEACON_CATEGORY_PERSON,
                BEACON_CATEGORY_ITEM,
                BEACON_CATEGORY_PET,
                BEACON_CATEGORY_VEHICLE,
                BEACON_CATEGORY_OTHER,
            ]),
            vol.Optional(CONF_BEACON_ICON): cv.string,
            vol.Optional(CONF_TX_POWER): vol.Coerce(float),
            vol.Optional(CONF_PATH_LOSS_EXPONENT): vol.Coerce(float),
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
    
    async def handle_add_proxy(call: ServiceCall) -> None:
        """Handle the add_proxy service call."""
        proxy_id = call.data.get(CONF_PROXY_ID)
        latitude = call.data.get(CONF_LATITUDE)
        longitude = call.data.get(CONF_LONGITUDE)
        
        await manager.add_proxy(proxy_id, latitude, longitude)
    
    hass.services.async_register(
        DOMAIN, 
        SERVICE_ADD_PROXY, 
        handle_add_proxy, 
        schema=vol.Schema({
            vol.Required(CONF_PROXY_ID): cv.string,
            vol.Required(CONF_LATITUDE): cv.latitude,
            vol.Required(CONF_LONGITUDE): cv.longitude,
        })
    )
    
    async def handle_remove_proxy(call: ServiceCall) -> None:
        """Handle the remove_proxy service call."""
        proxy_id = call.data.get(CONF_PROXY_ID)
        await manager.remove_proxy(proxy_id)
    
    hass.services.async_register(
        DOMAIN, 
        SERVICE_REMOVE_PROXY, 
        handle_remove_proxy, 
        schema=vol.Schema({
            vol.Required(CONF_PROXY_ID): cv.string,
        })
    )
    
    async def handle_add_zone(call: ServiceCall) -> None:
        """Handle the add_zone service call."""
        zone_id = call.data.get(CONF_ZONE_ID)
        name = call.data.get(CONF_ZONE_NAME)
        zone_type = call.data.get(CONF_ZONE_TYPE)
        coordinates = call.data.get(CONF_ZONE_COORDINATES)
        icon = call.data.get(CONF_ICON)
        
        await manager.zone_manager.add_zone(
            zone_id=zone_id,
            name=name,
            zone_type=zone_type,
            coordinates=coordinates,
            icon=icon,
        )
    
    hass.services.async_register(
        DOMAIN, 
        SERVICE_ADD_ZONE, 
        handle_add_zone, 
        schema=vol.Schema({
            vol.Required(CONF_ZONE_ID): cv.string,
            vol.Required(CONF_ZONE_NAME): cv.string,
            vol.Required(CONF_ZONE_TYPE): cv.string,
            vol.Required(CONF_ZONE_COORDINATES): vol.All(
                cv.ensure_list, [vol.All(cv.ensure_list, [cv.latitude, cv.longitude])]
            ),
            vol.Optional(CONF_ICON): cv.string,
        })
    )
    
    async def handle_remove_zone(call: ServiceCall) -> None:
        """Handle the remove_zone service call."""
        zone_id = call.data.get(CONF_ZONE_ID)
        await manager.zone_manager.remove_zone(zone_id)
    
    hass.services.async_register(
        DOMAIN, 
        SERVICE_REMOVE_ZONE, 
        handle_remove_zone, 
        schema=vol.Schema({
            vol.Required(CONF_ZONE_ID): cv.string,
        })
    )
    
    async def handle_calibrate(call: ServiceCall) -> None:
        """Handle the calibrate service call."""
        mac_address = call.data.get(CONF_MAC_ADDRESS)
        tx_power = call.data.get(CONF_TX_POWER)
        path_loss_exponent = call.data.get(CONF_PATH_LOSS_EXPONENT)

        await manager.calibrate_beacon(
            mac_address=mac_address,
            tx_power=tx_power,
            path_loss_exponent=path_loss_exponent,
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CALIBRATE,
        handle_calibrate,
        schema=vol.Schema({
            vol.Required(CONF_MAC_ADDRESS): cv.string,
            vol.Optional(CONF_TX_POWER): vol.Coerce(float),
            vol.Optional(CONF_PATH_LOSS_EXPONENT): vol.Coerce(float),
        })
    )

    # ESPHome configuration is now handled via example YAML files
    # See the README.md and esphome_ble_proxy.yaml for more information
    
    # Start the manager
    if entry.data.get(CONF_SERVICE_ENABLED, True):
        await manager.start()
    
    # Load the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register the configuration panel
    hass.http.async_register_static_paths(
        [
            (
                f"/ha_bt_advanced_panel/{entry.entry_id}",
                str(Path(__file__).parent / "panel"),
                False,
            )
        ]
    )

    await hass.components.frontend.async_register_web_panel(
        component_name="custom",
        sidebar_title="BT Advanced",
        sidebar_icon="mdi:bluetooth",
        frontend_url_path=f"ha-bt-advanced-{entry.entry_id}",
        config={"entry_id": entry.entry_id},
        module_url=f"/ha_bt_advanced_panel/{entry.entry_id}/ha-bt-advanced-panel.js",
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop the manager
    # Try both keys for backward compatibility
    if DATA_MANAGER in hass.data[DOMAIN][entry.entry_id]:
        manager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]
    else:
        manager = hass.data[DOMAIN][entry.entry_id]["manager"]

    await manager.stop()

    # Unload the platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Unregister the panel
    hass.components.frontend.async_remove_web_panel(f"ha-bt-advanced-{entry.entry_id}")

    # Remove the entry data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)