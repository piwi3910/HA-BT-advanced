"""Zone management for BLE Triangulation."""
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import yaml
from homeassistant.const import CONF_NAME, CONF_ICON
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_ZONE_ID,
    CONF_ZONE_NAME,
    CONF_ZONE_TYPE,
    CONF_ZONE_COORDINATES,
    ZONE_CONFIG_DIR,
    ZONE_TYPE_HOME,
    ZONE_TYPE_WORK,
    ZONE_TYPE_ROOM,
    ZONE_TYPE_CUSTOM,
)
from .triangulation import Triangulator

_LOGGER = logging.getLogger(__name__)

class Zone:
    """Represent a zone for BLE tracking."""

    def __init__(
        self,
        zone_id: str,
        name: str,
        zone_type: str,
        coordinates: List[Tuple[float, float]],
        icon: str = None,
    ):
        """Initialize a Zone."""
        self.zone_id = zone_id
        self.name = name
        self.zone_type = zone_type
        self.coordinates = coordinates
        self.icon = icon

    def contains_point(self, lat: float, lng: float) -> bool:
        """Check if this zone contains a specific point."""
        return Triangulator.check_point_in_polygon((lat, lng), self.coordinates)

    def to_dict(self) -> Dict[str, Any]:
        """Convert zone to dictionary for storage."""
        return {
            CONF_ZONE_ID: self.zone_id,
            CONF_ZONE_NAME: self.name,
            CONF_ZONE_TYPE: self.zone_type,
            CONF_ZONE_COORDINATES: self.coordinates,
            CONF_ICON: self.icon,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Zone':
        """Create a Zone from a dictionary."""
        return cls(
            zone_id=data[CONF_ZONE_ID],
            name=data[CONF_ZONE_NAME],
            zone_type=data[CONF_ZONE_TYPE],
            coordinates=data[CONF_ZONE_COORDINATES],
            icon=data.get(CONF_ICON),
        )


class ZoneManager:
    """Manage zones for BLE Triangulation."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the ZoneManager."""
        self.hass = hass
        self.zones: Dict[str, Zone] = {}
        self._load_zones()

    def _load_zones(self) -> None:
        """Load zones from configuration files."""
        zone_dir = Path(self.hass.config.path(ZONE_CONFIG_DIR))
        
        if not zone_dir.exists():
            zone_dir.mkdir(parents=True, exist_ok=True)
            return
            
        for file_path in zone_dir.glob("*.yaml"):
            try:
                with open(file_path, "r") as f:
                    zone_data = yaml.safe_load(f)
                    if zone_data and isinstance(zone_data, dict):
                        zone_id = file_path.stem
                        if CONF_ZONE_NAME in zone_data and CONF_ZONE_TYPE in zone_data and CONF_ZONE_COORDINATES in zone_data:
                            self.zones[zone_id] = Zone.from_dict({
                                CONF_ZONE_ID: zone_id,
                                **zone_data
                            })
                        else:
                            _LOGGER.warning(f"Zone file {file_path} missing required fields")
            except Exception as e:
                _LOGGER.error(f"Error loading zone from {file_path}: {e}")

    async def add_zone(
        self,
        zone_id: str,
        name: str,
        zone_type: str,
        coordinates: List[Tuple[float, float]],
        icon: str = None,
    ) -> Zone:
        """Add a new zone."""
        # Create zone
        zone = Zone(
            zone_id=zone_id,
            name=name,
            zone_type=zone_type,
            coordinates=coordinates,
            icon=icon,
        )
        
        # Save to file
        zone_dir = Path(self.hass.config.path(ZONE_CONFIG_DIR))
        zone_dir.mkdir(parents=True, exist_ok=True)
        
        zone_file = zone_dir / f"{zone_id}.yaml"
        with open(zone_file, "w") as f:
            yaml.dump(zone.to_dict(), f, default_flow_style=False)
            
        # Add to in-memory zones
        self.zones[zone_id] = zone
        
        return zone

    async def remove_zone(self, zone_id: str) -> bool:
        """Remove a zone."""
        # Remove file
        zone_dir = Path(self.hass.config.path(ZONE_CONFIG_DIR))
        zone_file = zone_dir / f"{zone_id}.yaml"
        
        if zone_file.exists():
            zone_file.unlink()
            
        # Remove from in-memory zones
        if zone_id in self.zones:
            del self.zones[zone_id]
            return True
            
        return False

    def get_zone_for_point(self, lat: float, lng: float) -> Optional[Zone]:
        """Find the zone containing a specific point."""
        for zone in self.zones.values():
            if zone.contains_point(lat, lng):
                return zone
        return None

    def get_zone_by_id(self, zone_id: str) -> Optional[Zone]:
        """Get a zone by ID."""
        return self.zones.get(zone_id)

    def get_all_zones(self) -> List[Zone]:
        """Get all zones."""
        return list(self.zones.values())