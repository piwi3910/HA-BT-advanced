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
    LENGTH_METERS,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ATTR_RSSI

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for BLE Triangulation component."""
    manager = hass.data[DOMAIN][config_entry.entry_id]["manager"]
    
    @callback
    def async_add_beacon_sensors(beacon_id: str, beacon_name: str) -> None:
        """Add sensors for a beacon."""
        entities = [
            BLESignalStrengthSensor(hass, manager, beacon_id, beacon_name),
            BLEDistanceSensor(hass, manager, beacon_id, beacon_name),
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
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._manager = manager
        self._beacon_id = beacon_id
        self._beacon_name = beacon_name
        self._unique_id = f"beacon_{beacon_id.lower().replace(':', '_')}_signal"
        
        # Initialize state
        self._rssi = None
        self._proxy_id = None
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_state_class = SensorStateClass.MEASUREMENT
        
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
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._manager = manager
        self._beacon_id = beacon_id
        self._beacon_name = beacon_name
        self._unique_id = f"beacon_{beacon_id.lower().replace(':', '_')}_distance"
        
        # Initialize state
        self._distance = None
        self._proxy_id = None
        self._attr_native_unit_of_measurement = LENGTH_METERS
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        
        # Register for updates
        manager.register_update_callback(self._unique_id, self._async_update)
        
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
        if "distance" in data:
            self._distance = data["distance"]
            self._proxy_id = data.get("proxy_id")
            self.async_write_ha_state()