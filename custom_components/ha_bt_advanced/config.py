"""HA-BT-Advanced configuration panel."""
import logging
import voluptuous as vol
import json
from aiohttp import web

from homeassistant.const import (
    CONF_NAME,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_ICON,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.http import HomeAssistantView

from .const import (
    DOMAIN,
    CONF_PROXY_ID,
    CONF_MAC_ADDRESS,
    CONF_BEACON_ICON,
    CONF_BEACON_CATEGORY,
    CONF_ZONE_ID,
    CONF_ZONE_NAME,
    CONF_ZONE_TYPE,
    CONF_ZONE_COORDINATES,
    DATA_MANAGER,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HA-BT-Advanced configuration panel."""
    # Register API views
    hass.http.register_view(ProxyListView(hass, config_entry))
    hass.http.register_view(ProxyView(hass, config_entry))
    hass.http.register_view(BeaconListView(hass, config_entry))
    hass.http.register_view(BeaconView(hass, config_entry))
    hass.http.register_view(ZoneListView(hass, config_entry))
    hass.http.register_view(ZoneView(hass, config_entry))
    
    return True


class ProxyListView(HomeAssistantView):
    """API View for listing and creating proxies."""
    url = "/api/ha_bt_advanced/proxies"
    name = "api:ha_bt_advanced:proxies"
    
    def __init__(self, hass, config_entry):
        """Initialize the view."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id][DATA_MANAGER]
    
    async def get(self, request):
        """Handle GET request."""
        proxies = []
        for proxy_id, proxy in self.manager.proxies.items():
            proxies.append({
                "id": proxy_id,
                "latitude": proxy.latitude,
                "longitude": proxy.longitude,
                "online": proxy.online,
            })
        return web.json_response(proxies)
    
    async def post(self, request):
        """Handle POST request."""
        try:
            data = await request.json()
            proxy_id = data.get(CONF_PROXY_ID)
            latitude = data.get(CONF_LATITUDE)
            longitude = data.get(CONF_LONGITUDE)
            
            if not proxy_id or latitude is None or longitude is None:
                return web.json_response({"error": "Missing required fields"}, status=400)
            
            await self.manager.add_proxy(proxy_id, latitude, longitude)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error adding proxy: {e}")
            return web.json_response({"error": str(e)}, status=500)


class ProxyView(HomeAssistantView):
    """API View for individual proxy operations."""
    url = "/api/ha_bt_advanced/proxies/{proxy_id}"
    name = "api:ha_bt_advanced:proxy"
    
    def __init__(self, hass, config_entry):
        """Initialize the view."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id][DATA_MANAGER]
    
    async def get(self, request, proxy_id):
        """Handle GET request."""
        if proxy_id not in self.manager.proxies:
            return web.json_response({"error": "Proxy not found"}, status=404)
        
        proxy = self.manager.proxies[proxy_id]
        return web.json_response({
            "id": proxy_id,
            "latitude": proxy.latitude,
            "longitude": proxy.longitude,
            "online": proxy.online,
        })
    
    async def put(self, request, proxy_id):
        """Handle PUT request."""
        try:
            data = await request.json()
            
            new_proxy_id = data.get(CONF_PROXY_ID, proxy_id)
            latitude = data.get(CONF_LATITUDE)
            longitude = data.get(CONF_LONGITUDE)
            
            if latitude is None or longitude is None:
                return web.json_response({"error": "Missing required fields"}, status=400)
            
            # If ID has changed, remove the old one
            if new_proxy_id != proxy_id:
                await self.manager.remove_proxy(proxy_id)
                
            # Add with new ID and data
            await self.manager.add_proxy(new_proxy_id, latitude, longitude)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error updating proxy: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def delete(self, request, proxy_id):
        """Handle DELETE request."""
        try:
            await self.manager.remove_proxy(proxy_id)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error removing proxy: {e}")
            return web.json_response({"error": str(e)}, status=500)


class BeaconListView(HomeAssistantView):
    """API View for listing and creating beacons."""
    url = "/api/ha_bt_advanced/beacons"
    name = "api:ha_bt_advanced:beacons"
    
    def __init__(self, hass, config_entry):
        """Initialize the view."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id][DATA_MANAGER]
    
    async def get(self, request):
        """Handle GET request."""
        beacons = []
        for mac, beacon in self.manager.beacons.items():
            beacons.append({
                "mac": mac,
                "name": beacon.name,
                "category": beacon.category,
                "icon": beacon.icon,
                "tx_power": beacon.tx_power,
                "path_loss_exponent": beacon.path_loss_exponent,
            })
        return web.json_response(beacons)
    
    async def post(self, request):
        """Handle POST request."""
        try:
            data = await request.json()
            mac = data.get(CONF_MAC_ADDRESS)
            name = data.get(CONF_NAME)
            category = data.get(CONF_BEACON_CATEGORY)
            icon = data.get(CONF_BEACON_ICON)
            
            if not mac or not name:
                return web.json_response({"error": "Missing required fields"}, status=400)
            
            await self.manager.add_beacon(mac, name, category, icon)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error adding beacon: {e}")
            return web.json_response({"error": str(e)}, status=500)


class BeaconView(HomeAssistantView):
    """API View for individual beacon operations."""
    url = "/api/ha_bt_advanced/beacons/{mac}"
    name = "api:ha_bt_advanced:beacon"
    
    def __init__(self, hass, config_entry):
        """Initialize the view."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id][DATA_MANAGER]
    
    async def get(self, request, mac):
        """Handle GET request."""
        if mac not in self.manager.beacons:
            return web.json_response({"error": "Beacon not found"}, status=404)
        
        beacon = self.manager.beacons[mac]
        return web.json_response({
            "mac": mac,
            "name": beacon.name,
            "category": beacon.category,
            "icon": beacon.icon,
            "tx_power": beacon.tx_power,
            "path_loss_exponent": beacon.path_loss_exponent,
        })
    
    async def put(self, request, mac):
        """Handle PUT request."""
        try:
            data = await request.json()
            
            new_mac = data.get(CONF_MAC_ADDRESS, mac)
            name = data.get(CONF_NAME)
            category = data.get(CONF_BEACON_CATEGORY)
            icon = data.get(CONF_BEACON_ICON)
            
            if not name:
                return web.json_response({"error": "Missing required fields"}, status=400)
            
            # If MAC has changed, remove the old one
            if new_mac != mac:
                await self.manager.remove_beacon(mac)
                
            # Add with new MAC and data
            await self.manager.add_beacon(new_mac, name, category, icon)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error updating beacon: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def delete(self, request, mac):
        """Handle DELETE request."""
        try:
            await self.manager.remove_beacon(mac)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error removing beacon: {e}")
            return web.json_response({"error": str(e)}, status=500)


class ZoneListView(HomeAssistantView):
    """API View for listing and creating zones."""
    url = "/api/ha_bt_advanced/zones"
    name = "api:ha_bt_advanced:zones"
    
    def __init__(self, hass, config_entry):
        """Initialize the view."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id][DATA_MANAGER]
    
    async def get(self, request):
        """Handle GET request."""
        zones = []
        for zone_id, zone in self.manager.zone_manager.zones.items():
            zones.append({
                "id": zone_id,
                "name": zone.name,
                "type": zone.zone_type,
                "coordinates": zone.coordinates,
                "icon": zone.icon,
            })
        return web.json_response(zones)
    
    async def post(self, request):
        """Handle POST request."""
        try:
            data = await request.json()
            zone_id = data.get(CONF_ZONE_ID)
            name = data.get(CONF_ZONE_NAME)
            zone_type = data.get(CONF_ZONE_TYPE)
            coordinates = data.get(CONF_ZONE_COORDINATES)
            icon = data.get(CONF_ICON)
            
            if not zone_id or not name or not zone_type or not coordinates or len(coordinates) < 3:
                return web.json_response({"error": "Invalid zone data"}, status=400)
            
            await self.manager.zone_manager.add_zone(zone_id, name, zone_type, coordinates, icon)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error adding zone: {e}")
            return web.json_response({"error": str(e)}, status=500)


class ZoneView(HomeAssistantView):
    """API View for individual zone operations."""
    url = "/api/ha_bt_advanced/zones/{zone_id}"
    name = "api:ha_bt_advanced:zone"
    
    def __init__(self, hass, config_entry):
        """Initialize the view."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id][DATA_MANAGER]
    
    async def get(self, request, zone_id):
        """Handle GET request."""
        if zone_id not in self.manager.zone_manager.zones:
            return web.json_response({"error": "Zone not found"}, status=404)
        
        zone = self.manager.zone_manager.zones[zone_id]
        return web.json_response({
            "id": zone_id,
            "name": zone.name,
            "type": zone.zone_type,
            "coordinates": zone.coordinates,
            "icon": zone.icon,
        })
    
    async def put(self, request, zone_id):
        """Handle PUT request."""
        try:
            data = await request.json()
            
            new_zone_id = data.get(CONF_ZONE_ID, zone_id)
            name = data.get(CONF_ZONE_NAME)
            zone_type = data.get(CONF_ZONE_TYPE)
            coordinates = data.get(CONF_ZONE_COORDINATES)
            icon = data.get(CONF_ICON)
            
            if not name or not zone_type or not coordinates or len(coordinates) < 3:
                return web.json_response({"error": "Invalid zone data"}, status=400)
            
            # If ID has changed, remove the old one
            if new_zone_id != zone_id:
                await self.manager.zone_manager.remove_zone(zone_id)
                
            # Add with new ID and data
            await self.manager.zone_manager.add_zone(new_zone_id, name, zone_type, coordinates, icon)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error updating zone: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def delete(self, request, zone_id):
        """Handle DELETE request."""
        try:
            await self.manager.zone_manager.remove_zone(zone_id)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error removing zone: {e}")
            return web.json_response({"error": str(e)}, status=500)