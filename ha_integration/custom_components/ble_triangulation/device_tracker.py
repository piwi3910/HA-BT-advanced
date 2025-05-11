"""Support for BLE Triangulation device trackers."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTR_GPS_ACCURACY,
    ATTR_LAST_SEEN,
    ATTR_SOURCE_PROXIES,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device tracker for BLE Triangulation component."""
    manager = hass.data[DOMAIN][config_entry.entry_id]["manager"]
    
    @callback
    def async_add_beacon(beacon_id: str, beacon_name: str) -> None:
        """Add beacon as device tracker."""
        _LOGGER.debug(f"Adding device tracker for beacon: {beacon_id}")
        async_add_entities([BLEBeaconTracker(hass, manager, beacon_id, beacon_name)])
    
    # Register callback to add device trackers when beacons are discovered
    manager.register_beacon_callback(async_add_beacon)
    
    # Add existing beacons
    for beacon_id, beacon_info in manager.beacons.items():
        async_add_beacon(beacon_id, beacon_info.get("name", f"Beacon {beacon_id}"))


class BLEBeaconTracker(TrackerEntity):
    """Represent a tracked BLE beacon."""

    def __init__(
        self, 
        hass: HomeAssistant,
        manager,
        beacon_id: str,
        beacon_name: str,
    ) -> None:
        """Initialize the tracker."""
        self.hass = hass
        self._manager = manager
        self._beacon_id = beacon_id
        self._name = beacon_name
        self._unique_id = f"beacon_{beacon_id.lower().replace(':', '_')}"
        
        # Initialize state
        self._latitude = None
        self._longitude = None
        self._accuracy = None
        self._last_seen = None
        self._source_proxies = []
        
        # Register for updates
        manager.register_update_callback(self._unique_id, self._async_update)

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the device."""
        return self._unique_id

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self._unique_id)},
            "name": self._name,
            "manufacturer": "iBeacon",
            "model": "BLE Beacon",
        }

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.GPS

    @property
    def latitude(self) -> Optional[float]:
        """Return latitude value of the device."""
        return self._latitude

    @property
    def longitude(self) -> Optional[float]:
        """Return longitude value of the device."""
        return self._longitude

    @property
    def location_accuracy(self) -> Optional[int]:
        """Return the location accuracy of the device."""
        return self._accuracy

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes of the device."""
        return {
            ATTR_LAST_SEEN: self._last_seen,
            ATTR_SOURCE_PROXIES: self._source_proxies,
        }

    @callback
    def _async_update(self, data: Dict[str, Any]) -> None:
        """Update the device tracker state."""
        self._latitude = data.get(ATTR_LATITUDE)
        self._longitude = data.get(ATTR_LONGITUDE)
        self._accuracy = data.get(ATTR_GPS_ACCURACY)
        self._last_seen = data.get(ATTR_LAST_SEEN)
        self._source_proxies = data.get(ATTR_SOURCE_PROXIES, [])
        
        # Update the entity state
        self.async_write_ha_state()