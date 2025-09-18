"""Binary sensor platform for BLE Triangulation."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .const import (
    DOMAIN, 
    ATTR_LAST_SEEN, 
    ATTR_ZONE,
    CONF_BEACON_CATEGORY,
    CATEGORY_ICONS,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors for BLE Triangulation component."""
    from .const import DATA_MANAGER
    manager = hass.data[DOMAIN][config_entry.entry_id][DATA_MANAGER]
    
    # Add proxy connectivity sensors first
    proxy_entities = []
    for proxy_id in manager.proxies:
        proxy_entities.append(BLEProxyConnectivitySensor(hass, manager, proxy_id))
    
    if proxy_entities:
        async_add_entities(proxy_entities)
    
    @callback
    def async_add_beacon_binary_sensors(beacon_id: str, beacon_name: str) -> None:
        """Add binary sensors for a beacon."""
        # Get beacon info
        beacon_info = manager.beacons.get(beacon_id, {})
        category = beacon_info.get(CONF_BEACON_CATEGORY)
        icon = beacon_info.get("icon", CATEGORY_ICONS.get(category))
        
        entities = [
            BLEPresenceSensor(hass, manager, beacon_id, beacon_name, icon),
        ]
        async_add_entities(entities)
    
    # Register callback for future beacon discoveries
    manager.register_beacon_callback(async_add_beacon_binary_sensors)
    
    # Add existing beacons
    for beacon_id, beacon_info in manager.beacons.items():
        async_add_beacon_binary_sensors(
            beacon_id, 
            beacon_info.get("name", f"Beacon {beacon_id}")
        )
    
    # Register for proxy added/removed events
    @callback
    def async_add_proxy_sensor(proxy_id: str) -> None:
        """Add a new proxy connectivity sensor."""
        async_add_entities([BLEProxyConnectivitySensor(hass, manager, proxy_id)])
        
    # We need to monitor the manager's proxies dict for changes
    # For this example, we'll re-check periodically
    # In a production system, you would set up proper event listeners
    
    # Listen for zone-specific presence sensors
    @callback
    def async_add_zone_presence_sensors() -> None:
        """Add zone presence sensors for all beacons and zones."""
        zone_entities = []
        
        for beacon_id, beacon_info in manager.beacons.items():
            beacon_name = beacon_info.get("name", f"Beacon {beacon_id}")
            category = beacon_info.get(CONF_BEACON_CATEGORY)
            icon = beacon_info.get("icon", CATEGORY_ICONS.get(category))
            
            for zone in manager.zone_manager.get_all_zones():
                zone_entities.append(
                    BLEZonePresenceSensor(
                        hass, manager, beacon_id, beacon_name, 
                        zone.zone_id, zone.name, icon
                    )
                )
                
        if zone_entities:
            async_add_entities(zone_entities)
    
    # Create zone presence sensors if we have both beacons and zones
    if manager.beacons and manager.zone_manager.get_all_zones():
        async_add_zone_presence_sensors()


class BLEPresenceSensor(BinarySensorEntity):
    """Binary sensor for BLE beacon presence."""

    def __init__(
        self, 
        hass: HomeAssistant,
        manager,
        beacon_id: str,
        beacon_name: str,
        icon: Optional[str] = None,
    ) -> None:
        """Initialize the binary sensor."""
        self.hass = hass
        self._manager = manager
        self._beacon_id = beacon_id
        self._beacon_name = beacon_name
        self._unique_id = f"beacon_{beacon_id.lower().replace(':', '_')}_presence"
        self._attr_icon = icon
        
        # Initialize state
        self._is_present = False
        self._last_seen = None
        self._attr_device_class = BinarySensorDeviceClass.PRESENCE
        
        # Register for updates
        manager.register_update_callback(self._unique_id, self._async_update)
        
    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return f"{self._beacon_name} Presence"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the binary sensor."""
        return self._unique_id

    @property
    def is_on(self) -> bool:
        """Return true if the beacon is present."""
        return self._is_present

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, f"beacon_{self._beacon_id.lower().replace(':', '_')}")},
            "name": self._beacon_name,
            "manufacturer": "iBeacon",
            "model": "BLE Beacon",
        }

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes of the binary sensor."""
        return {
            ATTR_LAST_SEEN: self._last_seen,
        }

    @callback
    def _async_update(self, data: Dict[str, Any]) -> None:
        """Update the binary sensor state."""
        self._is_present = True  # If we receive an update, beacon is present
        self._last_seen = data.get(ATTR_LAST_SEEN)
        
        # Check if beacon has been seen recently
        if self._last_seen:
            # For this basic implementation, we'll consider the beacon present
            # The manager's _check_devices_status method will handle "missing" beacons
            # and create notifications for them
            self._is_present = True
            
        self.async_write_ha_state()


class BLEZonePresenceSensor(BinarySensorEntity):
    """Binary sensor for BLE beacon presence in a specific zone."""

    def __init__(
        self, 
        hass: HomeAssistant,
        manager,
        beacon_id: str,
        beacon_name: str,
        zone_id: str,
        zone_name: str,
        icon: Optional[str] = None,
    ) -> None:
        """Initialize the binary sensor."""
        self.hass = hass
        self._manager = manager
        self._beacon_id = beacon_id
        self._beacon_name = beacon_name
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._unique_id = f"beacon_{beacon_id.lower().replace(':', '_')}_zone_{zone_id}"
        self._attr_icon = icon
        
        # Initialize state
        self._is_in_zone = False
        self._last_seen = None
        self._attr_device_class = BinarySensorDeviceClass.PRESENCE
        
        # Register for updates
        entity_id = f"beacon_{self._beacon_id.lower().replace(':', '_')}"
        manager.register_update_callback(entity_id, self._async_update)
        
    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return f"{self._beacon_name} in {self._zone_name}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the binary sensor."""
        return self._unique_id

    @property
    def is_on(self) -> bool:
        """Return true if the beacon is in the zone."""
        return self._is_in_zone

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, f"beacon_{self._beacon_id.lower().replace(':', '_')}")},
            "name": self._beacon_name,
            "manufacturer": "iBeacon",
            "model": "BLE Beacon",
        }

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes of the binary sensor."""
        return {
            ATTR_LAST_SEEN: self._last_seen,
            "zone_id": self._zone_id,
            "zone_name": self._zone_name,
        }

    @callback
    def _async_update(self, data: Dict[str, Any]) -> None:
        """Update the binary sensor state."""
        self._last_seen = data.get(ATTR_LAST_SEEN)
        
        # Check if the beacon is in this zone
        current_zone = data.get(ATTR_ZONE)
        self._is_in_zone = current_zone == self._zone_id
            
        self.async_write_ha_state()


class BLEProxyConnectivitySensor(BinarySensorEntity):
    """Binary sensor for BLE proxy connectivity."""

    def __init__(
        self, 
        hass: HomeAssistant,
        manager,
        proxy_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        self.hass = hass
        self._manager = manager
        self._proxy_id = proxy_id
        self._unique_id = f"proxy_{proxy_id}_connectivity"
        self._name = f"BLE Proxy {proxy_id}"
        self._attr_icon = "mdi:bluetooth-transfer"
        
        # Initialize state
        self._is_connected = False
        self._last_seen = None
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        
        # We need a reference to the last_seen timestamp for this proxy
        # from the manager's _proxy_last_seen dict
        self._proxy_last_seen = manager._proxy_last_seen
        
        # Set a large max age threshold for connectivity (twice the regular threshold)
        self._max_age = manager.max_reading_age * 2
        
    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the binary sensor."""
        return self._unique_id

    @property
    def is_on(self) -> bool:
        """Return true if the proxy is connected."""
        # Calculate from last_seen timestamp
        if self._proxy_id in self._proxy_last_seen:
            last_seen = self._proxy_last_seen[self._proxy_id]
            if last_seen is not None:
                # Check if the proxy has been seen within the max age
                now = dt_util.utcnow().timestamp()
                self._is_connected = (now - last_seen) <= self._max_age
                
        return self._is_connected

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, f"proxy_{self._proxy_id}")},
            "name": f"BLE Proxy {self._proxy_id}",
            "manufacturer": "ESPHome",
            "model": "BLE Proxy",
        }

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes of the binary sensor."""
        attrs = {"proxy_id": self._proxy_id}
        
        # Add last_seen if available
        if self._proxy_id in self._proxy_last_seen:
            last_seen = self._proxy_last_seen[self._proxy_id]
            if last_seen is not None:
                # Convert to ISO format datetime string
                attrs[ATTR_LAST_SEEN] = dt_util.utc_from_timestamp(last_seen).isoformat()
                
        # Add proxy location if available
        proxy_info = self._manager.proxies.get(self._proxy_id, {})
        if "latitude" in proxy_info and "longitude" in proxy_info:
            attrs["latitude"] = proxy_info["latitude"]
            attrs["longitude"] = proxy_info["longitude"]
            
        return attrs
        
    async def async_update(self) -> None:
        """Update the sensor state (called periodically)."""
        # The is_on property will calculate the current state based on the timestamp
        # Just trigger a state update
        self.async_write_ha_state()