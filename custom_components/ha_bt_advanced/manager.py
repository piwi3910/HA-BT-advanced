"""BLE Triangulation manager."""
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import yaml
from homeassistant.components import mqtt
from homeassistant.components.persistent_notification import async_create as async_create_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_LATITUDE,
    CONF_LONGITUDE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import template
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import slugify
import homeassistant.util.dt as dt_util

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
    CONF_MQTT_TOPIC,
    CONF_SIGNAL_PARAMETERS,
    CONF_BEACON_CATEGORY,
    CONF_BEACON_ICON,
    DEFAULT_MQTT_TOPIC_PREFIX,
    DEFAULT_MQTT_STATE_PREFIX,
    BEACON_CATEGORY_PERSON,
    BEACON_CATEGORY_ITEM,
    BEACON_CATEGORY_PET,
    BEACON_CATEGORY_VEHICLE,
    BEACON_CATEGORY_OTHER,
    CATEGORY_ICONS,
    PROXY_CONFIG_DIR,
    BEACON_CONFIG_DIR,
    ATTR_RSSI,
    ATTR_BEACON_MAC,
    ATTR_PROXY_ID,
    ATTR_TIMESTAMP,
    ATTR_DISTANCE,
    ATTR_GPS_ACCURACY,
    ATTR_LAST_SEEN,
    ATTR_SOURCE_PROXIES,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_ZONE,
    ATTR_CATEGORY,
    ATTR_ICON,
    EVENT_BEACON_DISCOVERED,
    EVENT_BEACON_SEEN,
    EVENT_BEACON_ZONE_CHANGE,
    EVENT_PROXY_STATUS_CHANGE,
    NOTIFICATION_NEW_BEACON,
    NOTIFICATION_BEACON_MISSING,
    NOTIFICATION_PROXY_OFFLINE,
)
from .triangulation import BeaconTracker, Triangulator
from .zones import ZoneManager
from .discovery import DiscoveryManager

_LOGGER = logging.getLogger(__name__)

class TriangulationManager:
    """Manage BLE Triangulation service."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the manager."""
        self.hass = hass
        self.config_entry = config_entry
        self.config = dict(config_entry.data)
        
        # Get signal parameters
        signal_params = self.config.get(CONF_SIGNAL_PARAMETERS, {})
        self.tx_power = signal_params.get(CONF_TX_POWER, -59)
        self.path_loss_exponent = signal_params.get(CONF_PATH_LOSS_EXPONENT, 2.0)
        self.rssi_smoothing = signal_params.get(CONF_RSSI_SMOOTHING, 0.3)
        self.position_smoothing = signal_params.get(CONF_POSITION_SMOOTHING, 0.2)
        self.max_reading_age = signal_params.get(CONF_MAX_READING_AGE, 30)
        self.min_proxies = signal_params.get(CONF_MIN_PROXIES, 2)
        
        # MQTT topics
        self.mqtt_topic_prefix = self.config.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC_PREFIX)
        self.mqtt_state_prefix = DEFAULT_MQTT_STATE_PREFIX
        
        # Callback registries
        self._beacon_callbacks = set()
        self._update_callbacks = {}
        
        # Beacon and proxy tracking (will be loaded async in start())
        self.beacons = {}
        self.proxies = {}
        
        # Initialize zone manager
        self.zone_manager = ZoneManager(hass)

        # Initialize discovery manager
        self.discovery_manager = DiscoveryManager(hass)

        # Initialize the triangulator
        self.triangulator = Triangulator()

        # Initialize beacon trackers
        self._trackers = {}
        self._initialize_trackers()
        
        # MQTT subscription
        self._mqtt_subscription = None
        
        # Proxy and beacon status tracking
        self._proxy_last_seen = {}
        self._beacon_last_seen = {}
        self._proxy_offline_notifications = {}
        self._proxy_metadata = {}  # Store proxy metadata from status messages

        # Calibration data
        self._calibration_mode = {}  # proxy_id -> {start_time, reference_distance, duration, rssi_samples}
        self._calibration_results = {}  # proxy_id -> {tx_power, path_loss_exponent, avg_rssi, std_dev}
        self._beacon_missing_notifications = {}
        
        # Schedule periodic cleanup and status check
        self._cleanup_interval = async_track_time_interval(
            hass, self._clean_old_readings, timedelta(seconds=60)
        )
        self._status_check_interval = async_track_time_interval(
            hass, self._check_devices_status, timedelta(seconds=300)
        )

    def _initialize_trackers(self) -> None:
        """Initialize beacon trackers from configurations."""
        for mac, beacon_info in self.beacons.items():
            name = beacon_info.get(CONF_NAME, f"Beacon {mac}")
            category = beacon_info.get(CONF_BEACON_CATEGORY, BEACON_CATEGORY_ITEM)
            icon = beacon_info.get(CONF_BEACON_ICON, CATEGORY_ICONS.get(category))
            
            # Use beacon-specific signal parameters if available
            tx_power = beacon_info.get(CONF_TX_POWER, self.tx_power)
            path_loss_exponent = beacon_info.get(CONF_PATH_LOSS_EXPONENT, self.path_loss_exponent)
            
            self._trackers[mac] = BeaconTracker(
                mac=mac,
                name=name,
                tx_power=tx_power,
                path_loss_exponent=path_loss_exponent,
                rssi_smoothing=self.rssi_smoothing,
                position_smoothing=self.position_smoothing,
                max_reading_age=self.max_reading_age,
                icon=icon,
                category=category,
            )

    async def _async_load_beacons(self) -> Dict[str, Dict[str, Any]]:
        """Load beacon configuration from files asynchronously."""
        beacons = {}
        beacon_dir = Path(self.hass.config.path(BEACON_CONFIG_DIR))

        if not beacon_dir.exists():
            await self.hass.async_add_executor_job(lambda: beacon_dir.mkdir(parents=True, exist_ok=True))
            return beacons

        file_paths = await self.hass.async_add_executor_job(
            lambda: list(beacon_dir.glob("*.yaml"))
        )

        for file_path in file_paths:
            try:
                content = await self.hass.async_add_executor_job(file_path.read_text)
                beacon_config = yaml.safe_load(content)
                if beacon_config and isinstance(beacon_config, dict):
                    mac = file_path.stem.upper()
                    beacons[mac] = beacon_config
                    # Add to onboarded list in discovery manager
                    self.discovery_manager.add_onboarded_beacon(mac)
            except Exception as e:
                _LOGGER.error(f"Error loading beacon config from {file_path}: {e}")

        return beacons

    async def _async_load_proxies(self) -> Dict[str, Dict[str, Any]]:
        """Load proxy configuration from files asynchronously."""
        proxies = {}
        proxy_dir = Path(self.hass.config.path(PROXY_CONFIG_DIR))

        if not proxy_dir.exists():
            await self.hass.async_add_executor_job(lambda: proxy_dir.mkdir(parents=True, exist_ok=True))
            return proxies

        file_paths = await self.hass.async_add_executor_job(
            lambda: list(proxy_dir.glob("*.yaml"))
        )

        for file_path in file_paths:
            try:
                content = await self.hass.async_add_executor_job(file_path.read_text)
                proxy_config = yaml.safe_load(content)
                if proxy_config and isinstance(proxy_config, dict):
                    proxy_id = file_path.stem
                    proxies[proxy_id] = proxy_config
            except Exception as e:
                _LOGGER.error(f"Error loading proxy config from {file_path}: {e}")

        return proxies

    def register_beacon_callback(self, callback_func: Callable[[str, str], None]) -> None:
        """Register callback for beacon discovery."""
        self._beacon_callbacks.add(callback_func)
        
        # Call callback for existing beacons
        for beacon_id, beacon_info in self.beacons.items():
            name = beacon_info.get(CONF_NAME, f"Beacon {beacon_id}")
            callback_func(beacon_id, name)

    def register_update_callback(self, entity_id: str, callback_func: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for entity state updates."""
        self._update_callbacks[entity_id] = callback_func

    def _validate_mac_address(self, mac_address: str) -> bool:
        """Validate MAC address format."""
        mac = mac_address.upper().replace(":", "").replace("-", "")
        # Check if it's a valid MAC address (12 hex digits)
        return len(mac) == 12 and all(c in "0123456789ABCDEF" for c in mac)

    def _format_mac_address(self, mac_address: str) -> str:
        """Format MAC address consistently (AA:BB:CC:DD:EE:FF)."""
        mac = mac_address.upper().replace(":", "").replace("-", "")
        return ":".join([mac[i:i+2] for i in range(0, 12, 2)])

    async def add_beacon(
        self, 
        mac_address: str, 
        name: str, 
        category: Optional[str] = BEACON_CATEGORY_ITEM, 
        icon: Optional[str] = None,
        tx_power: Optional[float] = None,
        path_loss_exponent: Optional[float] = None,
    ) -> None:
        """Add a new beacon."""
        # Validate MAC address
        if not self._validate_mac_address(mac_address):
            _LOGGER.error(f"Invalid MAC address: {mac_address}")
            return
            
        # Format MAC address
        mac = self._format_mac_address(mac_address)
        
        # Validate name
        if not name or not isinstance(name, str):
            name = f"Beacon {mac[-6:]}"
            
        # Validate category
        valid_categories = [
            BEACON_CATEGORY_PERSON,
            BEACON_CATEGORY_ITEM,
            BEACON_CATEGORY_PET,
            BEACON_CATEGORY_VEHICLE,
            BEACON_CATEGORY_OTHER,
        ]
        if not category or category not in valid_categories:
            category = BEACON_CATEGORY_ITEM
        
        # Determine icon based on category if not provided
        if not icon and category:
            icon = CATEGORY_ICONS.get(category)
        
        # Create beacon config with optional signal parameters
        beacon_config = {
            CONF_NAME: name,
            CONF_BEACON_CATEGORY: category,
            CONF_BEACON_ICON: icon,
        }
        
        # Add optional signal parameters if provided
        if tx_power is not None:
            beacon_config[CONF_TX_POWER] = tx_power
            
        if path_loss_exponent is not None:
            beacon_config[CONF_PATH_LOSS_EXPONENT] = path_loss_exponent
        
        # Save to file
        beacon_dir = Path(self.hass.config.path(BEACON_CONFIG_DIR))
        if not beacon_dir.exists():
            await self.hass.async_add_executor_job(lambda: beacon_dir.mkdir(parents=True, exist_ok=True))
        
        beacon_file = beacon_dir / f"{mac}.yaml"
        content = yaml.dump(beacon_config)
        await self.hass.async_add_executor_job(beacon_file.write_text, content)
            
        # Add to in-memory config
        self.beacons[mac] = beacon_config

        # Mark beacon as onboarded
        self.discovery_manager.add_onboarded_beacon(mac)

        # Create tracker if it doesn't exist
        if mac not in self._trackers:
            # Use beacon-specific signal parameters if provided
            beacon_tx_power = tx_power if tx_power is not None else self.tx_power
            beacon_path_loss = path_loss_exponent if path_loss_exponent is not None else self.path_loss_exponent
            
            self._trackers[mac] = BeaconTracker(
                mac=mac,
                name=name,
                tx_power=beacon_tx_power,
                path_loss_exponent=beacon_path_loss,
                rssi_smoothing=self.rssi_smoothing,
                position_smoothing=self.position_smoothing,
                max_reading_age=self.max_reading_age,
                icon=icon,
                category=category,
            )
        
        # Update config entry
        config = dict(self.config_entry.data)
        config[CONF_BEACONS] = {**config.get(CONF_BEACONS, {}), mac: beacon_config}
        self.hass.config_entries.async_update_entry(self.config_entry, data=config)
        
        # Notify callbacks
        for callback_func in self._beacon_callbacks:
            callback_func(mac, name)
            
        # Fire event for new beacon discovery
        self.hass.bus.async_fire(
            EVENT_BEACON_DISCOVERED,
            {
                ATTR_BEACON_MAC: mac,
                CONF_NAME: name,
                ATTR_CATEGORY: category,
                ATTR_ICON: icon,
            }
        )
        
        # Update beacon last seen timestamp
        self._beacon_last_seen[mac] = time.time()
        
        # Clear any missing notifications for this beacon
        notification_id = NOTIFICATION_BEACON_MISSING.format(mac)
        if notification_id in self._beacon_missing_notifications:
            del self._beacon_missing_notifications[notification_id]
            
        _LOGGER.info(f"Added new beacon: {name} ({mac})")

    async def remove_beacon(self, mac_address: str) -> None:
        """Remove a beacon."""
        # Validate and format MAC address
        if not self._validate_mac_address(mac_address):
            _LOGGER.error(f"Invalid MAC address: {mac_address}")
            return
            
        # Format MAC address
        mac = self._format_mac_address(mac_address)
        
        # Remove file
        beacon_dir = Path(self.hass.config.path(BEACON_CONFIG_DIR))
        beacon_file = beacon_dir / f"{mac}.yaml"
        
        if beacon_file.exists():
            await self.hass.async_add_executor_job(beacon_file.unlink)
            
        # Remove from in-memory config
        if mac in self.beacons:
            del self.beacons[mac]

        # Remove from onboarded list
        self.discovery_manager.remove_onboarded_beacon(mac)
            
        # Remove tracker
        if mac in self._trackers:
            del self._trackers[mac]
            
        # Remove from beacon status tracking
        if mac in self._beacon_last_seen:
            del self._beacon_last_seen[mac]
            
        # Clear any missing notifications
        notification_id = NOTIFICATION_BEACON_MISSING.format(mac)
        if notification_id in self._beacon_missing_notifications:
            del self._beacon_missing_notifications[notification_id]
            
        # Update config entry
        config = dict(self.config_entry.data)
        beacons = config.get(CONF_BEACONS, {})
        if mac in beacons:
            del beacons[mac]
            config[CONF_BEACONS] = beacons
            self.hass.config_entries.async_update_entry(self.config_entry, data=config)
            
        _LOGGER.info(f"Removed beacon: {mac}")

    async def add_proxy(
        self, 
        proxy_id: str, 
        latitude: float, 
        longitude: float
    ) -> None:
        """Add a new proxy."""
        # Validate proxy ID
        if not proxy_id or not isinstance(proxy_id, str):
            _LOGGER.error(f"Invalid proxy ID: {proxy_id}")
            return
            
        # Validate coordinates
        try:
            lat = float(latitude)
            lng = float(longitude)
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                _LOGGER.error(f"Invalid coordinates: {lat}, {lng}")
                return
        except (ValueError, TypeError):
            _LOGGER.error(f"Invalid coordinates: {latitude}, {longitude}")
            return
        
        # Create proxy config
        proxy_config = {
            CONF_LATITUDE: lat,
            CONF_LONGITUDE: lng,
        }
        
        # Save to file
        proxy_dir = Path(self.hass.config.path(PROXY_CONFIG_DIR))
        if not proxy_dir.exists():
            await self.hass.async_add_executor_job(lambda: proxy_dir.mkdir(parents=True, exist_ok=True))
        
        proxy_file = proxy_dir / f"{proxy_id}.yaml"
        content = yaml.dump(proxy_config)
        await self.hass.async_add_executor_job(proxy_file.write_text, content)
            
        # Add to in-memory config
        self.proxies[proxy_id] = proxy_config
        
        # Update config entry
        config = dict(self.config_entry.data)
        config[CONF_PROXIES] = {
            **config.get(CONF_PROXIES, {}), 
            proxy_id: {
                CONF_LATITUDE: lat,
                CONF_LONGITUDE: lng,
            }
        }
        self.hass.config_entries.async_update_entry(self.config_entry, data=config)
        
        # Restart service if running
        if self._mqtt_subscription is not None:
            await self.restart_service()
            
        _LOGGER.info(f"Added new proxy: {proxy_id} at ({lat}, {lng})")

    async def remove_proxy(self, proxy_id: str) -> None:
        """Remove a proxy."""
        # Validate proxy ID
        if not proxy_id or proxy_id not in self.proxies:
            _LOGGER.error(f"Unknown proxy ID: {proxy_id}")
            return
            
        # Remove file
        proxy_dir = Path(self.hass.config.path(PROXY_CONFIG_DIR))
        proxy_file = proxy_dir / f"{proxy_id}.yaml"
        
        if proxy_file.exists():
            await self.hass.async_add_executor_job(proxy_file.unlink)
            
        # Remove from in-memory config
        if proxy_id in self.proxies:
            del self.proxies[proxy_id]
            
        # Remove from proxy status tracking
        if proxy_id in self._proxy_last_seen:
            del self._proxy_last_seen[proxy_id]
            
        # Remove any offline notifications
        notification_id = NOTIFICATION_PROXY_OFFLINE.format(proxy_id)
        if notification_id in self._proxy_offline_notifications:
            del self._proxy_offline_notifications[notification_id]
            
        # Update config entry
        config = dict(self.config_entry.data)
        proxies = config.get(CONF_PROXIES, {})
        if proxy_id in proxies:
            del proxies[proxy_id]
            config[CONF_PROXIES] = proxies
            self.hass.config_entries.async_update_entry(self.config_entry, data=config)
            
        # Restart service if running
        if self._mqtt_subscription is not None:
            await self.restart_service()
            
        _LOGGER.info(f"Removed proxy: {proxy_id}")

    async def generate_config_yaml(self) -> str:
        """Generate YAML configuration for the triangulation service."""
        config = {
            "proxies": self.proxies,
            "beacons": {
                mac: {
                    "name": info.get(CONF_NAME, f"Beacon {mac}"),
                    "category": info.get(CONF_BEACON_CATEGORY, BEACON_CATEGORY_ITEM),
                    "icon": info.get(CONF_BEACON_ICON),
                    "tx_power": info.get(CONF_TX_POWER, self.tx_power),
                    "path_loss_exponent": info.get(CONF_PATH_LOSS_EXPONENT, self.path_loss_exponent),
                } for mac, info in self.beacons.items()
            },
            "signal": {
                "tx_power": self.tx_power,
                "path_loss_exponent": self.path_loss_exponent,
                "rssi_smoothing": self.rssi_smoothing,
                "position_smoothing": self.position_smoothing,
                "max_reading_age": self.max_reading_age,
                "min_proxies": self.min_proxies,
            }
        }
        
        return yaml.dump(config, default_flow_style=False)

    async def _mqtt_message_received(self, msg) -> None:
        """Handle received MQTT message."""
        try:
            # Parse topic to determine message type
            topic_parts = msg.topic.split("/")
            if len(topic_parts) < 2:
                return

            # Parse payload
            payload = json.loads(msg.payload)
            if not isinstance(payload, dict):
                return

            # Check if this is a proxy status message
            if "proxy" in topic_parts and "status" in topic_parts:
                # Handle proxy status message
                proxy_id = topic_parts[-2]  # proxy_id is before "status"
                await self._handle_proxy_status(proxy_id, payload)
                return

            # Otherwise it's a beacon message
            proxy_id = topic_parts[-1]

            # Update proxy last seen timestamp
            current_time = time.time()
            self._proxy_last_seen[proxy_id] = current_time

            # Auto-detect new proxy if not already known
            if proxy_id not in self.proxies:
                _LOGGER.info(f"Auto-detected new proxy: {proxy_id}")
                # Try to get coordinates from payload or use home coordinates as default
                latitude = self.hass.config.latitude
                longitude = self.hass.config.longitude

                # Check if payload contains proxy location
                if "proxy_location" in payload:
                    loc = payload["proxy_location"]
                    if isinstance(loc, dict):
                        latitude = loc.get("latitude", latitude)
                        longitude = loc.get("longitude", longitude)

                # Add the proxy automatically
                await self.add_proxy(proxy_id, latitude, longitude)

                # Log that a new proxy was auto-detected
                _LOGGER.info(f"Added auto-detected proxy {proxy_id} at ({latitude}, {longitude})")

            # Clear any offline notifications for this proxy
            notification_id = NOTIFICATION_PROXY_OFFLINE.format(proxy_id)
            if notification_id in self._proxy_offline_notifications:
                del self._proxy_offline_notifications[notification_id]

                # Fire event for proxy coming back online
                self.hass.bus.async_fire(
                    EVENT_PROXY_STATUS_CHANGE,
                    {
                        ATTR_PROXY_ID: proxy_id,
                        "status": "online",
                        ATTR_LAST_SEEN: current_time,
                    }
                )
                
            beacon_mac = payload.get(ATTR_BEACON_MAC)
            rssi = payload.get(ATTR_RSSI)

            if not beacon_mac or rssi is None:
                return

            # Check if this proxy is in calibration mode
            if self.is_proxy_calibrating(proxy_id):
                calibration_data = self._calibration_mode.get(proxy_id)
                if calibration_data:
                    # Collect RSSI samples for calibration
                    calibration_data["rssi_samples"].append(rssi)
                    _LOGGER.debug(
                        f"Calibration sample for {proxy_id}: RSSI={rssi} dBm "
                        f"(sample #{len(calibration_data['rssi_samples'])})"
                    )
                    # Don't process beacon normally during calibration
                    return

            # Extract beacon data including Eddystone telemetry
            beacon_data = {
                # iBeacon data
                'uuid': payload.get('uuid'),
                'major': payload.get('major'),
                'minor': payload.get('minor'),
                'tx_power': payload.get('tx_power'),
                'manufacturer_id': payload.get('manufacturer_id'),
                'service_uuids': payload.get('service_uuids', []),
                # Eddystone data
                'eddystone_uid': payload.get('eddystone_uid'),
                'eddystone_url': payload.get('eddystone_url'),
                'eddystone_namespace': payload.get('eddystone_namespace'),
                'eddystone_instance': payload.get('eddystone_instance'),
                # Eddystone telemetry (TLM frame)
                'battery_voltage': payload.get('battery_voltage'),
                'temperature': payload.get('temperature'),
                'packet_count': payload.get('packet_count'),
                'uptime_seconds': payload.get('uptime_seconds'),
                # Generic telemetry
                'battery_level': payload.get('battery_level'),
                'frame_type': payload.get('frame_type'),
            }

            # Check if beacon should be processed
            if not self.discovery_manager.should_process_beacon(beacon_mac, rssi, beacon_data):
                # If in discovery mode, add to discovered beacons
                if self.discovery_manager.discovery_mode:
                    self.discovery_manager.process_discovery_beacon(beacon_mac, rssi, beacon_data, proxy_id)
                return

            # Parse timestamp or use current time
            ts_str = payload.get(ATTR_TIMESTAMP)
            if ts_str:
                try:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    timestamp = dt.timestamp()
                except ValueError:
                    timestamp = current_time
            else:
                timestamp = current_time
                
            # Format MAC address consistently
            if not self._validate_mac_address(beacon_mac):
                _LOGGER.warning(f"Invalid MAC address received: {beacon_mac}")
                return
                
            mac = self._format_mac_address(beacon_mac)
            
            # Update beacon last seen timestamp
            self._beacon_last_seen[mac] = current_time
            
            # Clear any missing notifications for this beacon
            notification_id = NOTIFICATION_BEACON_MISSING.format(mac)
            if notification_id in self._beacon_missing_notifications:
                del self._beacon_missing_notifications[notification_id]
            
            # Only process onboarded beacons
            if mac not in self.beacons:
                _LOGGER.debug(f"Ignoring non-onboarded beacon: {mac}")
                return
                
            # Update beacon tracker
            if mac not in self._trackers:
                # Should not happen with the code above, but just in case
                beacon_info = self.beacons.get(mac, {})
                name = beacon_info.get(CONF_NAME, f"Beacon {mac}")
                category = beacon_info.get(CONF_BEACON_CATEGORY, BEACON_CATEGORY_ITEM)
                icon = beacon_info.get(CONF_BEACON_ICON, CATEGORY_ICONS.get(category))
                tx_power = beacon_info.get(CONF_TX_POWER, self.tx_power)
                path_loss_exponent = beacon_info.get(CONF_PATH_LOSS_EXPONENT, self.path_loss_exponent)
                
                self._trackers[mac] = BeaconTracker(
                    mac=mac,
                    name=name,
                    tx_power=tx_power,
                    path_loss_exponent=path_loss_exponent,
                    rssi_smoothing=self.rssi_smoothing,
                    position_smoothing=self.position_smoothing,
                    max_reading_age=self.max_reading_age,
                    icon=icon,
                    category=category,
                )
                
            # Update readings in tracker with beacon data
            tracker = self._trackers[mac]
            tracker.update_reading(proxy_id, rssi, timestamp, beacon_data)
            
            # Get proxy positions for triangulation
            proxy_positions = {
                p_id: {
                    CONF_LATITUDE: info.get(CONF_LATITUDE),
                    CONF_LONGITUDE: info.get(CONF_LONGITUDE),
                }
                for p_id, info in self.proxies.items()
            }
            
            # Get distances from each proxy
            distances = tracker.get_proxy_distances(proxy_positions)
            _LOGGER.debug(f"Beacon {mac} distances: {distances}")
            
            # Only attempt triangulation if we have enough proxies
            update_position = False
            
            if len(distances) >= self.min_proxies:
                # Perform triangulation
                latitude, longitude, accuracy = self.triangulator.trilaterate_2d(distances)
                
                if latitude is not None and longitude is not None:
                    # Update tracker position
                    tracker.update_position(latitude, longitude, accuracy, timestamp)
                    update_position = True
                    
                    # Check if beacon has moved to a different zone
                    prev_zone = tracker.zone
                    current_zone = self.zone_manager.get_zone_for_point(latitude, longitude)
                    
                    # Update zone information
                    tracker.prev_zone = prev_zone
                    if current_zone:
                        tracker.zone = current_zone.zone_id
                    else:
                        tracker.zone = None
                        
                    # Fire zone change event if zone has changed
                    if prev_zone != tracker.zone:
                        zone_name = None
                        if tracker.zone:
                            zone_obj = self.zone_manager.get_zone_by_id(tracker.zone)
                            if zone_obj:
                                zone_name = zone_obj.name
                                
                        _LOGGER.info(
                            f"Beacon {tracker.name} ({mac}) moved from zone "
                            f"{prev_zone or 'None'} to {tracker.zone or 'None'}"
                        )
                        
                        self.hass.bus.async_fire(
                            EVENT_BEACON_ZONE_CHANGE,
                            {
                                ATTR_BEACON_MAC: mac,
                                CONF_NAME: tracker.name,
                                ATTR_ZONE: tracker.zone,
                                "zone_name": zone_name,
                                "prev_zone": prev_zone,
                                ATTR_LATITUDE: latitude,
                                ATTR_LONGITUDE: longitude,
                                ATTR_GPS_ACCURACY: accuracy,
                            }
                        )
                else:
                    _LOGGER.debug(f"Triangulation failed for beacon {mac} with {len(distances)} proxies")
            else:
                _LOGGER.debug(
                    f"Not enough proxies for triangulation. Beacon {mac} has {len(distances)} "
                    f"proxies, need at least {self.min_proxies}"
                )
            
            # Fire beacon seen event
            self.hass.bus.async_fire(
                EVENT_BEACON_SEEN,
                {
                    ATTR_BEACON_MAC: mac,
                    CONF_NAME: tracker.name,
                    ATTR_PROXY_ID: proxy_id,
                    ATTR_RSSI: rssi,
                    ATTR_TIMESTAMP: timestamp,
                    ATTR_DISTANCE: tracker.rssi_to_distance(rssi),
                }
            )
            
            # Update the device tracker entity
            entity_id = f"beacon_{mac.lower().replace(':', '_')}"
            if entity_id in self._update_callbacks:
                # Get the source proxies (those that contributed to the position calculation)
                source_proxies = [p_id for p_id, _, _ in distances]
                
                # Call the entity callback with the updated state
                self._update_callbacks[entity_id]({
                    ATTR_LATITUDE: tracker.latitude,
                    ATTR_LONGITUDE: tracker.longitude,
                    ATTR_GPS_ACCURACY: tracker.accuracy,
                    ATTR_LAST_SEEN: datetime.now(timezone.utc).isoformat(),
                    ATTR_SOURCE_PROXIES: source_proxies,
                    ATTR_ZONE: tracker.zone,
                    ATTR_CATEGORY: tracker.category,
                    ATTR_ICON: tracker.icon,
                })
                
        except json.JSONDecodeError:
            _LOGGER.error(f"Invalid JSON payload: {msg.payload}")
        except Exception as e:
            _LOGGER.exception(f"Error processing MQTT message: {e}")

    async def _handle_proxy_status(self, proxy_id: str, payload: Dict[str, Any]) -> None:
        """Handle proxy status message with metadata."""
        try:
            current_time = time.time()

            # Update proxy last seen timestamp
            self._proxy_last_seen[proxy_id] = current_time

            # Auto-detect new proxy if not already known
            if proxy_id not in self.proxies:
                _LOGGER.info(f"Auto-detected new proxy from status message: {proxy_id}")
                # Use home coordinates as default
                latitude = self.hass.config.latitude
                longitude = self.hass.config.longitude

                # Add the proxy automatically
                await self.add_proxy(proxy_id, latitude, longitude)
                _LOGGER.info(f"Added auto-detected proxy {proxy_id} at ({latitude}, {longitude})")

            # Store proxy metadata
            if proxy_id not in self._proxy_metadata:
                self._proxy_metadata[proxy_id] = {}

            # Update metadata fields
            metadata = self._proxy_metadata[proxy_id]
            metadata['status'] = payload.get('status', 'online')
            metadata['ip_address'] = payload.get('ip_address')
            metadata['mac_address'] = payload.get('mac_address')
            metadata['wifi_ssid'] = payload.get('wifi_ssid')
            metadata['wifi_rssi'] = payload.get('wifi_rssi')
            metadata['hardware'] = payload.get('hardware', 'ESP32')
            metadata['board'] = payload.get('board')
            metadata['esphome_version'] = payload.get('esphome_version')
            metadata['temperature'] = payload.get('temperature')
            metadata['free_heap'] = payload.get('free_heap')
            metadata['uptime'] = payload.get('uptime')
            metadata['cpu_frequency'] = payload.get('cpu_frequency')
            metadata['flash_size'] = payload.get('flash_size')
            metadata['timestamp'] = payload.get('timestamp')
            metadata['last_seen'] = current_time

            # Clear any offline notifications for this proxy
            notification_id = NOTIFICATION_PROXY_OFFLINE.format(proxy_id)
            if notification_id in self._proxy_offline_notifications:
                del self._proxy_offline_notifications[notification_id]

                # Fire event for proxy coming back online
                self.hass.bus.async_fire(
                    EVENT_PROXY_STATUS_CHANGE,
                    {
                        ATTR_PROXY_ID: proxy_id,
                        "status": metadata.get('status', 'online'),
                        ATTR_LAST_SEEN: current_time,
                        "ip_address": metadata.get('ip_address'),
                        "wifi_ssid": metadata.get('wifi_ssid'),
                        "wifi_rssi": metadata.get('wifi_rssi'),
                        "temperature": metadata.get('temperature'),
                        "uptime": metadata.get('uptime'),
                    }
                )

            # Log status update
            _LOGGER.debug(
                f"Updated proxy {proxy_id} status: "
                f"IP={metadata.get('ip_address')}, "
                f"WiFi={metadata.get('wifi_ssid')}@{metadata.get('wifi_rssi')}dBm, "
                f"Temp={metadata.get('temperature')}°C, "
                f"Uptime={metadata.get('uptime')}s"
            )

        except Exception as e:
            _LOGGER.error(f"Error handling proxy status for {proxy_id}: {e}")

    async def _subscribe_mqtt(self) -> None:
        """Subscribe to MQTT topics."""
        if self._mqtt_subscription is not None:
            return
            
        try:
            self._mqtt_subscription = await mqtt.async_subscribe(
                self.hass,
                f"{self.mqtt_topic_prefix}/#",
                self._mqtt_message_received,
            )
            _LOGGER.debug(f"Subscribed to MQTT topic: {self.mqtt_topic_prefix}/#")
        except Exception as e:
            _LOGGER.error(f"Error subscribing to MQTT: {e}")

    async def _unsubscribe_mqtt(self) -> None:
        """Unsubscribe from MQTT topics."""
        if self._mqtt_subscription is not None:
            self._mqtt_subscription()
            self._mqtt_subscription = None
            _LOGGER.debug("Unsubscribed from MQTT topics")

    async def _clean_old_readings(self, now=None) -> None:
        """Clean old readings in all trackers."""
        # Clean old readings in all trackers
        for tracker in self._trackers.values():
            tracker.clean_old_readings()

    async def _check_devices_status(self, now=None) -> None:
        """Check status of proxies and beacons."""
        current_time = time.time()
        
        # Check for offline proxies
        for proxy_id in self.proxies:
            last_seen = self._proxy_last_seen.get(proxy_id)
            
            if last_seen is None or (current_time - last_seen) > self.max_reading_age * 2:
                # Proxy is considered offline
                notification_id = NOTIFICATION_PROXY_OFFLINE.format(proxy_id)
                
                # Only create notification if we haven't already
                if notification_id not in self._proxy_offline_notifications:
                    self._proxy_offline_notifications[notification_id] = True
                    
                    async_create_notification(
                        self.hass,
                        f"Proxy {proxy_id} has not been seen for more than "
                        f"{self.max_reading_age * 2} seconds and is considered offline.",
                        title="BLE Proxy Offline",
                        notification_id=notification_id,
                    )
                    
                    # Fire event for proxy status change
                    self.hass.bus.async_fire(
                        EVENT_PROXY_STATUS_CHANGE,
                        {
                            ATTR_PROXY_ID: proxy_id,
                            "status": "offline",
                            ATTR_LAST_SEEN: last_seen,
                        }
                    )
                    
                    _LOGGER.warning(f"Proxy {proxy_id} is offline (last seen: {last_seen})")
        
        # Check for missing beacons
        for mac, beacon_info in self.beacons.items():
            last_seen = self._beacon_last_seen.get(mac)
            name = beacon_info.get(CONF_NAME, f"Beacon {mac}")
            
            if last_seen is None or (current_time - last_seen) > self.max_reading_age * 3:
                # Beacon is considered missing
                notification_id = NOTIFICATION_BEACON_MISSING.format(mac)
                
                # Only create notification if we haven't already
                if notification_id not in self._beacon_missing_notifications:
                    self._beacon_missing_notifications[notification_id] = True
                    
                    async_create_notification(
                        self.hass,
                        f"Beacon {name} ({mac}) has not been seen for more than "
                        f"{self.max_reading_age * 3} seconds and may be out of range or powered off.",
                        title="BLE Beacon Missing",
                        notification_id=notification_id,
                    )
                    
                    _LOGGER.warning(f"Beacon {name} ({mac}) is missing (last seen: {last_seen})")

    async def set_beacon_position(
        self, 
        mac_address: str, 
        latitude: float, 
        longitude: float, 
        accuracy: float = 3.0
    ) -> bool:
        """Manually set a beacon's position (for testing or calibration)."""
        # Validate and format MAC address
        if not self._validate_mac_address(mac_address):
            _LOGGER.error(f"Invalid MAC address: {mac_address}")
            return False
            
        mac = self._format_mac_address(mac_address)
        
        # Check if beacon exists
        if mac not in self._trackers:
            _LOGGER.error(f"Unknown beacon MAC address: {mac}")
            return False
            
        # Validate coordinates
        try:
            lat = float(latitude)
            lng = float(longitude)
            acc = float(accuracy)
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180) or acc <= 0:
                _LOGGER.error(f"Invalid coordinates or accuracy: {lat}, {lng}, {acc}")
                return False
        except (ValueError, TypeError):
            _LOGGER.error(f"Invalid coordinates or accuracy: {latitude}, {longitude}, {accuracy}")
            return False
            
        # Update tracker position
        tracker = self._trackers[mac]
        timestamp = time.time()
        tracker.update_position(lat, lng, acc, timestamp)
        
        # Check for zone change
        prev_zone = tracker.zone
        current_zone = self.zone_manager.get_zone_for_point(lat, lng)
        
        # Update zone information
        tracker.prev_zone = prev_zone
        if current_zone:
            tracker.zone = current_zone.zone_id
        else:
            tracker.zone = None
            
        # Fire zone change event if zone has changed
        if prev_zone != tracker.zone:
            zone_name = None
            if tracker.zone:
                zone_obj = self.zone_manager.get_zone_by_id(tracker.zone)
                if zone_obj:
                    zone_name = zone_obj.name
                    
            _LOGGER.info(
                f"Beacon {tracker.name} ({mac}) moved from zone "
                f"{prev_zone or 'None'} to {tracker.zone or 'None'}"
            )
            
            self.hass.bus.async_fire(
                EVENT_BEACON_ZONE_CHANGE,
                {
                    ATTR_BEACON_MAC: mac,
                    CONF_NAME: tracker.name,
                    ATTR_ZONE: tracker.zone,
                    "zone_name": zone_name,
                    "prev_zone": prev_zone,
                    ATTR_LATITUDE: lat,
                    ATTR_LONGITUDE: lng,
                    ATTR_GPS_ACCURACY: acc,
                }
            )
        
        # Update the device tracker entity
        entity_id = f"beacon_{mac.lower().replace(':', '_')}"
        if entity_id in self._update_callbacks:
            # Call the entity callback with the updated state
            self._update_callbacks[entity_id]({
                ATTR_LATITUDE: lat,
                ATTR_LONGITUDE: lng,
                ATTR_GPS_ACCURACY: acc,
                ATTR_LAST_SEEN: datetime.now(timezone.utc).isoformat(),
                ATTR_SOURCE_PROXIES: [],  # No source proxies for manual position
                ATTR_ZONE: tracker.zone,
                ATTR_CATEGORY: tracker.category,
                ATTR_ICON: tracker.icon,
            })
            
        _LOGGER.info(f"Manually set position for beacon {tracker.name} ({mac}) to ({lat}, {lng})")
        return True

    async def start(self) -> None:
        """Start the triangulation service."""
        # Load configurations asynchronously
        self.beacons = await self._async_load_beacons()
        self.proxies = await self._async_load_proxies()

        # Load virtual users
        await self.discovery_manager.load_virtual_users()

        # Subscribe to MQTT
        await self._subscribe_mqtt()
        
        # Initialize timestamps for all beacons and proxies
        for mac in self.beacons:
            if mac not in self._beacon_last_seen:
                self._beacon_last_seen[mac] = 0
                
        for proxy_id in self.proxies:
            if proxy_id not in self._proxy_last_seen:
                self._proxy_last_seen[proxy_id] = 0
                
        _LOGGER.info("HA-BT-Advanced triangulation service started")

    async def start_discovery(self, duration: int = 60) -> bool:
        """Start beacon discovery mode."""
        result = await self.discovery_manager.start_discovery(duration)
        _LOGGER.info(f"Discovery mode started for {duration} seconds")
        return result

    def stop_discovery(self) -> None:
        """Stop beacon discovery mode."""
        self.discovery_manager._stop_discovery()
        _LOGGER.info("Discovery mode stopped")

    def get_discovered_beacons(self) -> List[Dict[str, Any]]:
        """Get list of discovered beacons."""
        return self.discovery_manager.get_discovered_beacons()

    async def onboard_beacon(
        self,
        mac_address: str,
        name: str,
        owner: Optional[str] = None,
        category: str = BEACON_CATEGORY_ITEM,
        icon: Optional[str] = None,
        notifications_enabled: bool = True,
        tracking_precision: str = "medium",
    ) -> bool:
        """Onboard a discovered beacon."""
        # Validate MAC address
        if not self._validate_mac_address(mac_address):
            _LOGGER.error(f"Invalid MAC address: {mac_address}")
            return False

        mac = self._format_mac_address(mac_address)

        # Get beacon data from discovered beacons
        discovered_info = self.discovery_manager.discovered_beacons.get(mac, {})
        beacon_data = discovered_info.get('beacon_data', {})

        # Build beacon configuration
        beacon_config = {
            'name': name,
            'mac': mac,
            'owner': owner,
            'category': category,
            'icon': icon or CATEGORY_ICONS.get(category),
            'beacon_type': discovered_info.get('beacon_type', 'unknown'),
            'beacon_data': beacon_data,
            'onboarded_at': datetime.now().isoformat(),
            'notifications': {
                'enabled': notifications_enabled,
                'on_arrive': True,
                'on_leave': True,
                'on_not_seen_for': 1800,  # 30 minutes
            },
            'tracking': {
                'enabled': True,
                'precision': tracking_precision,
            },
        }

        # Save beacon configuration
        beacon_dir = Path(self.hass.config.path(BEACON_CONFIG_DIR))
        if not beacon_dir.exists():
            await self.hass.async_add_executor_job(lambda: beacon_dir.mkdir(parents=True, exist_ok=True))

        beacon_file = beacon_dir / f"{mac}.yaml"
        content = yaml.dump(beacon_config)
        await self.hass.async_add_executor_job(beacon_file.write_text, content)

        # Add to in-memory config
        self.beacons[mac] = beacon_config

        # Mark beacon as onboarded
        self.discovery_manager.add_onboarded_beacon(mac)

        # Create tracker for the beacon
        if mac not in self._trackers:
            self._trackers[mac] = BeaconTracker(
                mac=mac,
                name=name,
                rssi_smoothing_factor=self.rssi_smoothing,
                position_smoothing_factor=self.position_smoothing,
                max_reading_age=self.max_reading_age,
                tx_power=self.tx_power,
                path_loss_exponent=self.path_loss_exponent,
            )

        # Register beacon with callbacks
        for callback in self._beacon_callbacks:
            callback(mac, name)

        _LOGGER.info(f"Successfully onboarded beacon {name} ({mac})")
        return True

    async def onboard_multiple_beacons(
        self,
        beacons: List[Dict[str, Any]],
        default_owner: Optional[str] = None,
        default_category: str = BEACON_CATEGORY_ITEM,
        notifications_enabled: bool = True,
    ) -> Dict[str, bool]:
        """Onboard multiple beacons at once."""
        results = {}
        for beacon in beacons:
            mac = beacon.get('mac')
            name = beacon.get('name', f"Beacon {mac[-6:]}")
            owner = beacon.get('owner', default_owner)
            category = beacon.get('category', default_category)
            icon = beacon.get('icon')

            success = await self.onboard_beacon(
                mac_address=mac,
                name=name,
                owner=owner,
                category=category,
                icon=icon,
                notifications_enabled=notifications_enabled,
            )
            results[mac] = success

        return results

    async def create_virtual_user(self, name: str) -> str:
        """Create a virtual user for guests."""
        return await self.discovery_manager.create_virtual_user(name)

    def get_all_users(self) -> List[Dict[str, str]]:
        """Get all available users (HA users + virtual users)."""
        return self.discovery_manager.get_all_users()

    def set_discovery_filters(self, filters: Dict[str, Any]) -> None:
        """Set filters for beacon discovery."""
        self.discovery_manager.set_beacon_filters(filters)

    async def stop(self) -> None:
        """Stop the triangulation service."""
        # Unsubscribe from MQTT
        await self._unsubscribe_mqtt()
        
        # Cancel cleanup interval
        if self._cleanup_interval:
            self._cleanup_interval()
            self._cleanup_interval = None
            
        # Cancel status check interval
        if self._status_check_interval:
            self._status_check_interval()
            self._status_check_interval = None
            
        _LOGGER.info("HA-BT-Advanced triangulation service stopped")

    async def restart_service(self) -> None:
        """Restart the triangulation service."""
        await self.stop()
        await self.start()
        
    async def calibrate_beacon(
        self, 
        mac_address: str, 
        tx_power: Optional[float] = None,
        path_loss_exponent: Optional[float] = None
    ) -> bool:
        """Calibrate a beacon with new signal parameters."""
        # Validate and format MAC address
        if not self._validate_mac_address(mac_address):
            _LOGGER.error(f"Invalid MAC address: {mac_address}")
            return False
            
        mac = self._format_mac_address(mac_address)
        
        if mac not in self.beacons:
            _LOGGER.error(f"Cannot calibrate unknown beacon: {mac}")
            return False
            
        # Update beacon configuration
        beacon_config = self.beacons[mac]
        
        if tx_power is not None:
            beacon_config[CONF_TX_POWER] = tx_power
            
        if path_loss_exponent is not None:
            beacon_config[CONF_PATH_LOSS_EXPONENT] = path_loss_exponent
            
        # Update tracker
        if mac in self._trackers:
            tracker = self._trackers[mac]
            if tx_power is not None:
                tracker.tx_power = tx_power
            if path_loss_exponent is not None:
                tracker.path_loss_exponent = path_loss_exponent
                
        # Save to file
        beacon_dir = Path(self.hass.config.path(BEACON_CONFIG_DIR))
        beacon_file = beacon_dir / f"{mac}.yaml"
        
        content = yaml.dump(beacon_config)
        await self.hass.async_add_executor_job(beacon_file.write_text, content)
            
        # Update config entry
        config = dict(self.config_entry.data)
        config[CONF_BEACONS] = {**config.get(CONF_BEACONS, {}), mac: beacon_config}
        self.hass.config_entries.async_update_entry(self.config_entry, data=config)
        
        _LOGGER.info(
            f"Calibrated beacon {beacon_config.get(CONF_NAME, mac)} ({mac}): "
            f"tx_power={tx_power}, path_loss_exponent={path_loss_exponent}"
        )
        return True

    async def start_proxy_calibration(
        self,
        proxy_id: str,
        reference_distance: float = 1.0,
        duration: int = 30
    ) -> bool:
        """Start calibration mode for a proxy."""
        if proxy_id not in self.proxies:
            _LOGGER.error(f"Proxy {proxy_id} not found")
            return False

        # Initialize calibration data
        self._calibration_mode[proxy_id] = {
            "start_time": time.time(),
            "reference_distance": reference_distance,
            "duration": duration,
            "rssi_samples": []
        }

        _LOGGER.info(
            f"Started calibration for proxy {proxy_id}. "
            f"Place beacon at {reference_distance}m from the proxy. "
            f"Collecting RSSI samples for {duration} seconds."
        )

        # Create notification for user
        await async_create_notification(
            self.hass,
            title="Proxy Calibration Started",
            message=(
                f"Calibration started for proxy {proxy_id}.\n\n"
                f"1. Place a beacon exactly {reference_distance} meters from the proxy\n"
                f"2. Keep the beacon stationary during calibration\n"
                f"3. Ensure clear line of sight between beacon and proxy\n"
                f"4. Wait {duration} seconds for calibration to complete\n\n"
                f"Call the 'get_calibration_results' service when complete."
            ),
            notification_id=f"proxy_calibration_{proxy_id}"
        )

        # Schedule calibration completion
        async def complete_calibration():
            await asyncio.sleep(duration)
            await self._complete_proxy_calibration(proxy_id)

        self.hass.async_create_task(complete_calibration())
        return True

    async def _complete_proxy_calibration(self, proxy_id: str) -> None:
        """Complete proxy calibration and calculate results."""
        if proxy_id not in self._calibration_mode:
            return

        calibration_data = self._calibration_mode[proxy_id]
        rssi_samples = calibration_data["rssi_samples"]

        if len(rssi_samples) < 5:
            _LOGGER.warning(
                f"Insufficient RSSI samples for proxy {proxy_id}: {len(rssi_samples)}. "
                "Need at least 5 samples for reliable calibration."
            )
            # Notify user of failure
            await async_create_notification(
                self.hass,
                title="Calibration Failed",
                message=(
                    f"Calibration failed for proxy {proxy_id}.\n"
                    f"Only received {len(rssi_samples)} RSSI samples (minimum 5 required).\n"
                    "Please ensure the beacon is transmitting and try again."
                ),
                notification_id=f"proxy_calibration_{proxy_id}"
            )
            del self._calibration_mode[proxy_id]
            return

        # Calculate statistics
        import statistics
        avg_rssi = statistics.mean(rssi_samples)
        std_dev = statistics.stdev(rssi_samples) if len(rssi_samples) > 1 else 0

        # Calculate TX power at 1m using the reference distance
        # RSSI = TX_Power - 10 * n * log10(distance)
        # TX_Power = RSSI + 10 * n * log10(distance)
        reference_distance = calibration_data["reference_distance"]

        # Use current path loss exponent or default
        n = self.path_loss_exponent

        # Calculate TX power at 1m
        import math
        tx_power_at_1m = avg_rssi + 10 * n * math.log10(reference_distance)

        # Store results
        self._calibration_results[proxy_id] = {
            "tx_power": round(tx_power_at_1m, 1),
            "path_loss_exponent": n,
            "avg_rssi": round(avg_rssi, 1),
            "std_dev": round(std_dev, 2),
            "sample_count": len(rssi_samples),
            "reference_distance": reference_distance,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Remove from calibration mode
        del self._calibration_mode[proxy_id]

        # Notify user of completion
        await async_create_notification(
            self.hass,
            title="Calibration Complete",
            message=(
                f"Calibration completed for proxy {proxy_id}.\n\n"
                f"Results:\n"
                f"• Average RSSI: {round(avg_rssi, 1)} dBm\n"
                f"• Standard Deviation: {round(std_dev, 2)} dBm\n"
                f"• Calculated TX Power at 1m: {round(tx_power_at_1m, 1)} dBm\n"
                f"• Samples collected: {len(rssi_samples)}\n\n"
                f"Call 'get_calibration_results' service for detailed results."
            ),
            notification_id=f"proxy_calibration_{proxy_id}"
        )

        _LOGGER.info(
            f"Calibration complete for proxy {proxy_id}: "
            f"TX Power={round(tx_power_at_1m, 1)} dBm, "
            f"Avg RSSI={round(avg_rssi, 1)} dBm, "
            f"Std Dev={round(std_dev, 2)} dBm"
        )

    def get_calibration_results(self, proxy_id: str) -> Optional[Dict[str, Any]]:
        """Get calibration results for a proxy."""
        return self._calibration_results.get(proxy_id)

    def get_proxy_metadata(self, proxy_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a proxy from status messages."""
        return self._proxy_metadata.get(proxy_id)

    def get_all_proxy_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata for all proxies."""
        return self._proxy_metadata.copy()

    def is_proxy_calibrating(self, proxy_id: str) -> bool:
        """Check if a proxy is currently in calibration mode."""
        if proxy_id not in self._calibration_mode:
            return False

        calibration_data = self._calibration_mode[proxy_id]
        elapsed = time.time() - calibration_data["start_time"]

        # Check if calibration is still active
        if elapsed > calibration_data["duration"]:
            # Calibration should have completed, clean up if needed
            if proxy_id in self._calibration_mode:
                del self._calibration_mode[proxy_id]
            return False

        return True