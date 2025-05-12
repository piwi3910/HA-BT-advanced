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

from .const import DOMAIN, ATTR_LAST_SEEN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors for BLE Triangulation component."""
    manager = hass.data[DOMAIN][config_entry.entry_id]["manager"]
    
    @callback
    def async_add_beacon_binary_sensors(beacon_id: str, beacon_name: str) -> None:
        """Add binary sensors for a beacon."""
        entities = [
            BLEPresenceSensor(hass, manager, beacon_id, beacon_name),
        ]
        async_add_entities(entities)
    
    # Register callback to add binary sensors when beacons are discovered
    manager.register_beacon_callback(async_add_beacon_binary_sensors)
    
    # Add existing beacons
    for beacon_id, beacon_info in manager.beacons.items():
        async_add_beacon_binary_sensors(
            beacon_id, 
            beacon_info.get("name", f"Beacon {beacon_id}")
        )


class BLEPresenceSensor(BinarySensorEntity):
    """Binary sensor for BLE beacon presence."""

    def __init__(
        self, 
        hass: HomeAssistant,
        manager,
        beacon_id: str,
        beacon_name: str,
    ) -> None:
        """Initialize the binary sensor."""
        self.hass = hass
        self._manager = manager
        self._beacon_id = beacon_id
        self._beacon_name = beacon_name
        self._unique_id = f"beacon_{beacon_id.lower().replace(':', '_')}_presence"
        
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
        self.async_write_ha_state()