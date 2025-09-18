"""Sensor platform for BLE Triangulation."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    PERCENTAGE,
    UnitOfLength,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ATTR_RSSI,
    ATTR_DISTANCE,
    ATTR_GPS_ACCURACY,
    ATTR_ZONE,
    CONF_BEACON_CATEGORY,
    CATEGORY_ICONS,
    DATA_MANAGER,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for BLE Triangulation component."""
    manager = hass.data[DOMAIN][config_entry.entry_id][DATA_MANAGER]
    
    @callback
    def async_add_beacon_sensors(beacon_id: str, beacon_name: str) -> None:
        """Add sensors for a beacon."""
        # Get beacon info
        beacon_info = manager.beacons.get(beacon_id, {})
        category = beacon_info.get(CONF_BEACON_CATEGORY)
        icon = beacon_info.get("icon", CATEGORY_ICONS.get(category))
        
        entities = [
            BLESignalStrengthSensor(hass, manager, beacon_id, beacon_name, icon),
            BLEDistanceSensor(hass, manager, beacon_id, beacon_name, icon),
            BLEAccuracySensor(hass, manager, beacon_id, beacon_name, icon),
            BLEZoneSensor(hass, manager, beacon_id, beacon_name, icon),
        ]
        async_add_entities(entities)
    
    # Register callback to add sensors when beacons are discovered
    manager.register_beacon_callback(async_add_beacon_sensors)
    
    # Add existing beacons
    for beacon_id, beacon_info in manager.beacons.items():
        async_add_beacon_sensors(
            beacon_id, 
            beacon_info.get("name", f"Beacon {beacon_id}")
        )


class BLESignalStrengthSensor(SensorEntity):
    """Sensor for BLE signal strength."""

    def __init__(
        self, 
        hass: HomeAssistant,
        manager,
        beacon_id: str,
        beacon_name: str,
        icon: Optional[str] = None,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._manager = manager
        self._beacon_id = beacon_id
        self._beacon_name = beacon_name
        self._unique_id = f"beacon_{beacon_id.lower().replace(':', '_')}_signal"
        self._attr_icon = icon or "mdi:signal"
        
        # Initialize state
        self._rssi = None
        self._proxy_id = None
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_state_class = SensorStateClass.MEASUREMENT
        
        # Register for updates
        entity_id = f"beacon_{self._beacon_id.lower().replace(':', '_')}"
        manager.register_update_callback(entity_id, self._async_update)
        
    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self._beacon_name} Signal Strength"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def native_value(self) -> Optional[int]:
        """Return the RSSI value."""
        return self._rssi

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
        """Return additional attributes of the sensor."""
        return {
            "proxy_id": self._proxy_id,
        }

    @callback
    def _async_update(self, data: Dict[str, Any]) -> None:
        """Update the sensor state."""
        if ATTR_RSSI in data:
            self._rssi = data[ATTR_RSSI]
            self._proxy_id = data.get("proxy_id")
            self.async_write_ha_state()


class BLEDistanceSensor(SensorEntity):
    """Sensor for estimated BLE beacon distance."""

    def __init__(
        self, 
        hass: HomeAssistant,
        manager,
        beacon_id: str,
        beacon_name: str,
        icon: Optional[str] = None,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._manager = manager
        self._beacon_id = beacon_id
        self._beacon_name = beacon_name
        self._unique_id = f"beacon_{beacon_id.lower().replace(':', '_')}_distance"
        self._attr_icon = icon or "mdi:ruler"
        
        # Initialize state
        self._distance = None
        self._proxy_id = None
        self._attr_native_unit_of_measurement = UnitOfLength.METERS
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        
        # Register for updates
        entity_id = f"beacon_{self._beacon_id.lower().replace(':', '_')}"
        manager.register_update_callback(entity_id, self._async_update)
        
    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self._beacon_name} Distance"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def native_value(self) -> Optional[float]:
        """Return the distance value."""
        return self._distance

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
        """Return additional attributes of the sensor."""
        return {
            "proxy_id": self._proxy_id,
        }

    @callback
    def _async_update(self, data: Dict[str, Any]) -> None:
        """Update the sensor state."""
        if ATTR_DISTANCE in data:
            self._distance = data[ATTR_DISTANCE]
            self._proxy_id = data.get("proxy_id")
            self.async_write_ha_state()


class BLEAccuracySensor(SensorEntity):
    """Sensor for BLE triangulation accuracy."""

    def __init__(
        self, 
        hass: HomeAssistant,
        manager,
        beacon_id: str,
        beacon_name: str,
        icon: Optional[str] = None,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._manager = manager
        self._beacon_id = beacon_id
        self._beacon_name = beacon_name
        self._unique_id = f"beacon_{beacon_id.lower().replace(':', '_')}_accuracy"
        self._attr_icon = icon or "mdi:target"
        
        # Initialize state
        self._accuracy = None
        self._attr_native_unit_of_measurement = UnitOfLength.METERS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        
        # Register for updates
        entity_id = f"beacon_{self._beacon_id.lower().replace(':', '_')}"
        manager.register_update_callback(entity_id, self._async_update)
        
    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self._beacon_name} Accuracy"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def native_value(self) -> Optional[float]:
        """Return the accuracy value."""
        return self._accuracy

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
        """Return additional attributes of the sensor."""
        # Get the corresponding tracker
        tracker = self._manager._trackers.get(self._beacon_id)
        attrs = {}
        
        if tracker:
            # Add number of contributing proxies
            proxy_readings = tracker.proxy_readings
            if proxy_readings:
                attrs["num_proxies"] = len(proxy_readings)
                attrs["contributing_proxies"] = list(proxy_readings.keys())
                
        return attrs

    @callback
    def _async_update(self, data: Dict[str, Any]) -> None:
        """Update the sensor state."""
        if ATTR_GPS_ACCURACY in data:
            self._accuracy = data[ATTR_GPS_ACCURACY]
            self.async_write_ha_state()


class BLEZoneSensor(SensorEntity):
    """Sensor for BLE beacon current zone."""

    def __init__(
        self, 
        hass: HomeAssistant,
        manager,
        beacon_id: str,
        beacon_name: str,
        icon: Optional[str] = None,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._manager = manager
        self._beacon_id = beacon_id
        self._beacon_name = beacon_name
        self._unique_id = f"beacon_{beacon_id.lower().replace(':', '_')}_zone"
        self._attr_icon = icon or "mdi:map-marker"
        
        # Initialize state
        self._zone_id = None
        self._zone_name = None
        
        # Register for updates
        entity_id = f"beacon_{self._beacon_id.lower().replace(':', '_')}"
        manager.register_update_callback(entity_id, self._async_update)
        
    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self._beacon_name} Zone"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def native_value(self) -> Optional[str]:
        """Return the zone name as the value."""
        return self._zone_name

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
        """Return additional attributes of the sensor."""
        attrs = {
            "zone_id": self._zone_id,
        }
        
        # Add zone info if available
        if self._zone_id and self._manager.zone_manager:
            zone = self._manager.zone_manager.get_zone_by_id(self._zone_id)
            if zone:
                attrs["zone_type"] = zone.zone_type
                
        return attrs

    @callback
    def _async_update(self, data: Dict[str, Any]) -> None:
        """Update the sensor state."""
        if ATTR_ZONE in data:
            self._zone_id = data[ATTR_ZONE]
            
            # Look up zone name
            if self._zone_id and self._manager.zone_manager:
                zone = self._manager.zone_manager.get_zone_by_id(self._zone_id)
                if zone:
                    self._zone_name = zone.name
                else:
                    self._zone_name = f"Unknown Zone ({self._zone_id})"
            else:
                self._zone_name = "Not in a zone"
                
            self.async_write_ha_state()