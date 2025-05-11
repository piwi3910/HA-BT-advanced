"""BLE Triangulation manager."""
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import yaml
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_LATITUDE,
    CONF_LONGITUDE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import template
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import slugify

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
    DEFAULT_MQTT_TOPIC_PREFIX,
    DEFAULT_MQTT_STATE_PREFIX,
    PROXY_CONFIG_DIR,
    BEACON_CONFIG_DIR,
    ATTR_RSSI,
    ATTR_BEACON_MAC,
    ATTR_PROXY_ID,
    ATTR_TIMESTAMP,
    ATTR_GPS_ACCURACY,
    ATTR_LAST_SEEN,
    ATTR_SOURCE_PROXIES,
)

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
        
        # Beacon and proxy tracking
        self.beacons = self._load_beacons()
        self.proxies = self._load_proxies()
        
        # BeaconTracker instances
        self._trackers = {}
        
        # MQTT subscription
        self._mqtt_subscription = None
        
        # Triangulation service process
        self._process = None
        self._process_task = None
        self._stopping = False

    def _load_beacons(self) -> Dict[str, Dict[str, Any]]:
        """Load beacon configuration from files."""
        beacons = {}
        beacon_dir = Path(self.hass.config.path(BEACON_CONFIG_DIR))
        
        if not beacon_dir.exists():
            return beacons
            
        for file_path in beacon_dir.glob("*.yaml"):
            try:
                with open(file_path, "r") as f:
                    beacon_config = yaml.safe_load(f)
                    if beacon_config and isinstance(beacon_config, dict):
                        mac = file_path.stem.upper()
                        beacons[mac] = beacon_config
            except Exception as e:
                _LOGGER.error(f"Error loading beacon config from {file_path}: {e}")
                
        return beacons

    def _load_proxies(self) -> Dict[str, Dict[str, Any]]:
        """Load proxy configuration from files."""
        proxies = {}
        proxy_dir = Path(self.hass.config.path(PROXY_CONFIG_DIR))
        
        if not proxy_dir.exists():
            return proxies
            
        for file_path in proxy_dir.glob("*.yaml"):
            try:
                with open(file_path, "r") as f:
                    proxy_config = yaml.safe_load(f)
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
            name = beacon_info.get("name", f"Beacon {beacon_id}")
            callback_func(beacon_id, name)

    def register_update_callback(self, entity_id: str, callback_func: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for entity state updates."""
        self._update_callbacks[entity_id] = callback_func

    async def add_beacon(self, mac_address: str, name: str) -> None:
        """Add a new beacon."""
        # Format MAC address
        mac = mac_address.upper()
        
        # Create beacon config
        beacon_config = {
            "name": name,
        }
        
        # Save to file
        beacon_dir = Path(self.hass.config.path(BEACON_CONFIG_DIR))
        beacon_dir.mkdir(parents=True, exist_ok=True)
        
        beacon_file = beacon_dir / f"{mac}.yaml"
        with open(beacon_file, "w") as f:
            yaml.dump(beacon_config, f)
            
        # Add to in-memory config
        self.beacons[mac] = beacon_config
        
        # Update config entry
        config = dict(self.config_entry.data)
        config[CONF_BEACONS] = {**config.get(CONF_BEACONS, {}), mac: {"name": name}}
        self.hass.config_entries.async_update_entry(self.config_entry, data=config)
        
        # Notify callbacks
        for callback_func in self._beacon_callbacks:
            callback_func(mac, name)

    async def remove_beacon(self, mac_address: str) -> None:
        """Remove a beacon."""
        # Format MAC address
        mac = mac_address.upper()
        
        # Remove file
        beacon_dir = Path(self.hass.config.path(BEACON_CONFIG_DIR))
        beacon_file = beacon_dir / f"{mac}.yaml"
        
        if beacon_file.exists():
            beacon_file.unlink()
            
        # Remove from in-memory config
        if mac in self.beacons:
            del self.beacons[mac]
            
        # Update config entry
        config = dict(self.config_entry.data)
        beacons = config.get(CONF_BEACONS, {})
        if mac in beacons:
            del beacons[mac]
            config[CONF_BEACONS] = beacons
            self.hass.config_entries.async_update_entry(self.config_entry, data=config)

    async def add_proxy(self, proxy_id: str, latitude: float, longitude: float) -> None:
        """Add a new proxy."""
        # Create proxy config
        proxy_config = {
            CONF_LATITUDE: latitude,
            CONF_LONGITUDE: longitude,
        }
        
        # Save to file
        proxy_dir = Path(self.hass.config.path(PROXY_CONFIG_DIR))
        proxy_dir.mkdir(parents=True, exist_ok=True)
        
        proxy_file = proxy_dir / f"{proxy_id}.yaml"
        with open(proxy_file, "w") as f:
            yaml.dump(proxy_config, f)
            
        # Add to in-memory config
        self.proxies[proxy_id] = proxy_config
        
        # Update config entry
        config = dict(self.config_entry.data)
        config[CONF_PROXIES] = {
            **config.get(CONF_PROXIES, {}), 
            proxy_id: {
                CONF_LATITUDE: latitude,
                CONF_LONGITUDE: longitude,
            }
        }
        self.hass.config_entries.async_update_entry(self.config_entry, data=config)
        
        # Restart service if running
        if self._process is not None:
            await self.restart_service()

    async def remove_proxy(self, proxy_id: str) -> None:
        """Remove a proxy."""
        # Remove file
        proxy_dir = Path(self.hass.config.path(PROXY_CONFIG_DIR))
        proxy_file = proxy_dir / f"{proxy_id}.yaml"
        
        if proxy_file.exists():
            proxy_file.unlink()
            
        # Remove from in-memory config
        if proxy_id in self.proxies:
            del self.proxies[proxy_id]
            
        # Update config entry
        config = dict(self.config_entry.data)
        proxies = config.get(CONF_PROXIES, {})
        if proxy_id in proxies:
            del proxies[proxy_id]
            config[CONF_PROXIES] = proxies
            self.hass.config_entries.async_update_entry(self.config_entry, data=config)
            
        # Restart service if running
        if self._process is not None:
            await self.restart_service()

    async def generate_config_yaml(self) -> str:
        """Generate YAML configuration for the triangulation service."""
        config = {
            "proxies": self.proxies,
            "beacons": {mac: info.get("name", f"Beacon {mac}") for mac, info in self.beacons.items()},
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
            # Extract proxy ID from topic
            topic_parts = msg.topic.split("/")
            if len(topic_parts) < 2:
                return
                
            proxy_id = topic_parts[-1]
            
            # Parse payload
            payload = json.loads(msg.payload)
            if not isinstance(payload, dict):
                return
                
            beacon_mac = payload.get(ATTR_BEACON_MAC)
            rssi = payload.get(ATTR_RSSI)
            
            if not beacon_mac or rssi is None:
                return
                
            # Parse timestamp or use current time
            ts_str = payload.get(ATTR_TIMESTAMP)
            if ts_str:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                timestamp = dt.timestamp()
            else:
                timestamp = time.time()
                
            # Format MAC address consistently
            mac = beacon_mac.upper()
            
            # Check if this is a new beacon
            if mac not in self.beacons:
                await self.add_beacon(mac, f"Beacon {mac}")
                
            # Update beacon state
            entity_id = f"beacon_{mac.lower().replace(':', '_')}"
            if entity_id in self._update_callbacks:
                # In a real implementation, this would trigger the triangulation
                # calculation. For this example, we're just updating the entity
                # with the raw data.
                self._update_callbacks[entity_id]({
                    ATTR_LAST_SEEN: datetime.now(timezone.utc).isoformat(),
                    ATTR_SOURCE_PROXIES: [proxy_id],
                })
                
        except json.JSONDecodeError:
            _LOGGER.error(f"Invalid JSON payload: {msg.payload}")
        except Exception as e:
            _LOGGER.exception(f"Error processing MQTT message: {e}")

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

    async def start(self) -> None:
        """Start the triangulation service."""
        # Subscribe to MQTT
        await self._subscribe_mqtt()
        
        # If we're not using the Python service, this is enough
        # For this example, we'll implement the full service below
        if not self.config.get(CONF_SERVICE_ENABLED, True):
            return
            
        # For a full implementation, we would start our Python service here
        # This would involve generating the config file and starting the process
        try:
            # Generate configuration file
            config_yaml = await self.generate_config_yaml()
            config_path = Path(self.hass.config.path("ble_triangulation_config.yaml"))
            
            with open(config_path, "w") as f:
                f.write(config_yaml)
                
            # Start the service (this is just a placeholder - integrate with your Python service)
            _LOGGER.info("Starting BLE Triangulation service")
            
            # In a real implementation, you would start the Python service here
            # For example, using asyncio.create_subprocess_exec
            
        except Exception as e:
            _LOGGER.error(f"Error starting triangulation service: {e}")

    async def stop(self) -> None:
        """Stop the triangulation service."""
        self._stopping = True
        
        # Unsubscribe from MQTT
        await self._unsubscribe_mqtt()
        
        # Stop the service process if running
        if self._process is not None:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
            except Exception as e:
                _LOGGER.error(f"Error stopping triangulation service: {e}")
            finally:
                self._process = None
                
        if self._process_task is not None:
            self._process_task.cancel()
            self._process_task = None
            
        self._stopping = False
        _LOGGER.info("BLE Triangulation service stopped")

    async def restart_service(self) -> None:
        """Restart the triangulation service."""
        await self.stop()
        await self.start()