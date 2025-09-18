#!/usr/bin/env python3
"""
BLE iBeacon Triangulation Service

This service connects to MQTT, listens for BLE advertisements from
multiple ESP32 proxies, performs triangulation, and publishes device_tracker
entities to Home Assistant via MQTT Auto-discovery.
"""

import asyncio
import json
import logging
import os
import re
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import yaml
import asyncio_mqtt as mqtt
from paho.mqtt import client as mqtt_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ble_triangulation")

# Constants
DEFAULT_CONFIG_PATH = "proxies.yaml"
MQTT_DISCOVERY_PREFIX = "homeassistant"
MQTT_STATE_PREFIX = "ble-location"
MQTT_PROXY_PREFIX = "ble-triangulation"


class RSSIBuffer:
    """Maintains a rolling buffer of RSSI readings with timestamps."""

    def __init__(self, max_age: float = 30.0, smoothing_factor: float = 0.3):
        self.readings = []
        self.max_age = max_age
        self.smoothing_factor = smoothing_factor
        self.smoothed_rssi = None

    def add_reading(self, rssi: int, timestamp: float):
        """Add a new RSSI reading with timestamp."""
        self.readings.append((rssi, timestamp))
        
        # Update smoothed RSSI using exponential moving average
        if self.smoothed_rssi is None:
            self.smoothed_rssi = rssi
        else:
            self.smoothed_rssi = (
                self.smoothing_factor * rssi + 
                (1 - self.smoothing_factor) * self.smoothed_rssi
            )

    def clean_old_readings(self, current_time: float):
        """Remove readings older than max_age."""
        self.readings = [
            (rssi, ts) for rssi, ts in self.readings 
            if current_time - ts <= self.max_age
        ]

    def get_average_rssi(self) -> Optional[float]:
        """Get the average RSSI from recent readings."""
        if not self.readings:
            return None
        
        # Return the smoothed value instead of simple average
        return self.smoothed_rssi


class BeaconTracker:
    """Tracks RSSI readings from multiple proxies for a single beacon."""

    def __init__(
        self, 
        mac: str, 
        name: str, 
        tx_power: float, 
        path_loss_exponent: float,
        rssi_smoothing: float,
        position_smoothing: float,
        max_reading_age: float,
    ):
        self.mac = mac
        self.name = name
        self.tx_power = tx_power
        self.path_loss_exponent = path_loss_exponent
        self.max_reading_age = max_reading_age
        self.position_smoothing = position_smoothing
        
        # Dictionary of proxy_id -> RSSIBuffer
        self.proxy_readings: Dict[str, RSSIBuffer] = {}
        
        # Last calculated position
        self.latitude = None
        self.longitude = None
        self.accuracy = None
        self.last_update = None

    def update_reading(self, proxy_id: str, rssi: int, timestamp: float):
        """Update RSSI reading for a specific proxy."""
        if proxy_id not in self.proxy_readings:
            self.proxy_readings[proxy_id] = RSSIBuffer(
                max_age=self.max_reading_age,
                smoothing_factor=rssi_smoothing,
            )
        
        self.proxy_readings[proxy_id].add_reading(rssi, timestamp)

    def clean_old_readings(self):
        """Remove old readings from all proxy buffers."""
        current_time = time.time()
        for buffer in self.proxy_readings.values():
            buffer.clean_old_readings(current_time)

    def rssi_to_distance(self, rssi: float) -> float:
        """Convert RSSI to distance in meters using path loss model."""
        if rssi == 0:
            return 100.0  # Arbitrary large distance for zero RSSI
            
        ratio = (self.tx_power - rssi) / (10 * self.path_loss_exponent)
        return 10 ** ratio

    def get_proxy_distances(self, proxy_positions: Dict[str, Dict[str, float]]) -> List[Tuple]:
        """Get list of (lat, lng, distance) tuples for trilateration."""
        result = []
        current_time = time.time()
        
        for proxy_id, buffer in self.proxy_readings.items():
            buffer.clean_old_readings(current_time)
            avg_rssi = buffer.get_average_rssi()
            
            if avg_rssi is not None and proxy_id in proxy_positions:
                distance = self.rssi_to_distance(avg_rssi)
                lat = proxy_positions[proxy_id]['latitude']
                lng = proxy_positions[proxy_id]['longitude']
                result.append((lat, lng, distance))
                
        return result

    def update_position(
        self, 
        lat: float, 
        lng: float, 
        accuracy: float, 
        timestamp: float
    ):
        """Update beacon position with smoothing."""
        if self.latitude is None or self.longitude is None:
            # First position update
            self.latitude = lat
            self.longitude = lng
            self.accuracy = accuracy
        else:
            # Apply exponential moving average smoothing
            self.latitude = (
                self.position_smoothing * lat + 
                (1 - self.position_smoothing) * self.latitude
            )
            self.longitude = (
                self.position_smoothing * lng + 
                (1 - self.position_smoothing) * self.longitude
            )
            self.accuracy = (
                self.position_smoothing * accuracy + 
                (1 - self.position_smoothing) * self.accuracy
            )
            
        self.last_update = timestamp


class Triangulator:
    """Performs triangulation based on distances from known points."""

    @staticmethod
    def trilaterate_2d(points: List[Tuple]) -> Tuple[float, float, float]:
        """
        Perform 2D trilateration to find the most likely position.
        points: List of (lat, lng, distance) tuples
        returns: (latitude, longitude, accuracy)
        """
        if len(points) < 2:
            return None, None, None
            
        # If only 2 points, use simpler method
        if len(points) == 2:
            return Triangulator.bilaterate_2d(points)
            
        # Convert lat/lng to x/y using simple approximation
        # (this works for small areas, for larger areas use proper projection)
        earth_radius = 6371000  # meters
        
        # Use first point as origin
        origin_lat, origin_lng, _ = points[0]
        
        # Convert to radians
        origin_lat_rad = origin_lat * (3.141592653589793 / 180)
        
        # Scale factors
        lat_scale = earth_radius  # meters per radian
        lng_scale = earth_radius * math.cos(origin_lat_rad)  # meters per radian
        
        # Convert all points to local x/y coordinates
        xy_points = []
        for lat, lng, distance in points:
            x = (lng - origin_lng) * (3.141592653589793 / 180) * lng_scale
            y = (lat - origin_lat) * (3.141592653589793 / 180) * lat_scale
            xy_points.append((x, y, distance))
        
        # Perform trilateration in x/y space (simplified least squares)
        # This is a simplification of the full least squares solution
        weights = [1/(d*d) if d > 0 else 1.0 for _, _, d in xy_points]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return None, None, None
            
        # Weighted average of circle intersections
        x_sum = 0
        y_sum = 0
        
        for i, (x1, y1, r1) in enumerate(xy_points):
            for j in range(i+1, len(xy_points)):
                x2, y2, r2 = xy_points[j]
                
                # Distance between centers
                d = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                
                # No solution if circles are too far apart or one contains the other
                if d > r1 + r2 or d < abs(r1 - r2):
                    continue
                
                # Math for circle intersection
                a = (r1*r1 - r2*r2 + d*d) / (2*d)
                h = math.sqrt(max(0, r1*r1 - a*a))  # Use max to avoid negative sqrt
                
                x3 = x1 + a * (x2 - x1) / d
                y3 = y1 + a * (y2 - y1) / d
                
                # Two intersection points
                x4_1 = x3 + h * (y2 - y1) / d
                y4_1 = y3 - h * (x2 - x1) / d
                
                x4_2 = x3 - h * (y2 - y1) / d
                y4_2 = y3 + h * (x2 - x1) / d
                
                # Calculate the weight for this pair based on distance measurement confidence
                pair_weight = weights[i] * weights[j]
                
                # Add both intersection points with weight
                x_sum += (x4_1 + x4_2) * pair_weight / 2
                y_sum += (y4_1 + y4_2) * pair_weight / 2
        
        # Check if we have any valid intersections
        if x_sum == 0 and y_sum == 0:
            # Fallback to weighted centroid of circles
            for i, ((x, y, r), w) in enumerate(zip(xy_points, weights)):
                x_sum += x * w
                y_sum += y * w
                
            x_result = x_sum / total_weight
            y_result = y_sum / total_weight
        else:
            # Normalize by weight sum
            x_result = x_sum / total_weight
            y_result = y_sum / total_weight
            
        # Calculate accuracy from residuals
        residuals = []
        for x, y, r in xy_points:
            actual_dist = math.sqrt((x_result - x)**2 + (y_result - y)**2)
            residuals.append(abs(actual_dist - r))
            
        # Use the average residual as our accuracy estimate
        if residuals:
            accuracy = sum(residuals) / len(residuals)
            # Ensure minimum accuracy of 1m
            accuracy = max(1.0, accuracy)
        else:
            accuracy = 10.0  # default when we can't estimate
            
        # Convert back to lat/lng
        result_lng = origin_lng + (x_result / lng_scale) * (180 / 3.141592653589793)
        result_lat = origin_lat + (y_result / lat_scale) * (180 / 3.141592653589793)
        
        return result_lat, result_lng, accuracy

    @staticmethod
    def bilaterate_2d(points: List[Tuple]) -> Tuple[float, float, float]:
        """
        Calculate position based on two distance measurements.
        This is a special case of trilateration with just 2 points.
        """
        (lat1, lng1, r1), (lat2, lng2, r2) = points
        
        # Convert to a local x-y coordinate system
        # (simple approximation assuming small distances)
        earth_radius = 6371000  # meters
        
        # Convert to radians
        lat1_rad = lat1 * (3.141592653589793 / 180)
        lat2_rad = lat2 * (3.141592653589793 / 180)
        lng1_rad = lng1 * (3.141592653589793 / 180)
        lng2_rad = lng2 * (3.141592653589793 / 180)
        
        # Calculate x-y coordinates
        x1, y1 = 0, 0  # First point is origin
        
        # Distance between points
        d_lat = (lat2_rad - lat1_rad) * earth_radius
        d_lng = (lng2_rad - lng1_rad) * earth_radius * math.cos(lat1_rad)
        
        x2 = d_lng
        y2 = d_lat
        
        d = math.sqrt(x2*x2 + y2*y2)
        
        # Handle edge cases
        if d == 0:
            # Points are in the same location, can't determine position
            return lat1, lng1, max(r1, r2)
            
        if d > r1 + r2:
            # Circles don't intersect, find point between them
            ratio = r1 / (r1 + r2)
            x = x1 + (x2 - x1) * ratio
            y = y1 + (y2 - y1) * ratio
            accuracy = d - (r1 + r2)
        elif d < abs(r1 - r2):
            # One circle contains the other
            if r1 > r2:
                ratio = r2 / r1
                x = x1 + (x2 - x1) * ratio
                y = y1 + (y2 - y1) * ratio
            else:
                ratio = r1 / r2
                x = x2 + (x1 - x2) * ratio
                y = y2 + (y1 - y2) * ratio
            accuracy = abs(r1 - r2) - d
        else:
            # Standard case - circles intersect
            a = (r1*r1 - r2*r2 + d*d) / (2*d)
            h = math.sqrt(r1*r1 - a*a)
            
            x3 = x1 + a * (x2 - x1) / d
            y3 = y1 + a * (y2 - y1) / d
            
            # We have two intersection points, choose the one that makes most sense
            # For now, just take average of the two points
            x4_1 = x3 + h * (y2 - y1) / d
            y4_1 = y3 - h * (x2 - x1) / d
            
            x4_2 = x3 - h * (y2 - y1) / d
            y4_2 = y3 + h * (x2 - x1) / d
            
            x = (x4_1 + x4_2) / 2
            y = (y4_1 + y4_2) / 2
            
            # Calculate accuracy based on how well circles fit
            accuracy = max(1.0, h)
            
        # Convert back to lat/lng
        result_lat = lat1 + (y / earth_radius) * (180 / 3.141592653589793)
        result_lng = lng1 + (x / (earth_radius * math.cos(lat1_rad))) * (180 / 3.141592653589793)
        
        return result_lat, result_lng, accuracy


class MQTTHandler:
    """Handles MQTT communication for device tracking."""

    def __init__(
        self, 
        client: mqtt.Client, 
        proxy_positions: Dict[str, Dict[str, float]],
        beacon_names: Dict[str, str],
        signal_config: Dict[str, float],
        min_proxies: int,
    ):
        self.client = client
        self.proxy_positions = proxy_positions
        self.beacon_names = beacon_names
        self.min_proxies = min_proxies
        
        # Extract signal configuration
        self.tx_power = signal_config.get("tx_power", -59)
        self.path_loss_exponent = signal_config.get("path_loss_exponent", 2.0)
        self.rssi_smoothing = signal_config.get("rssi_smoothing", 0.3)
        self.position_smoothing = signal_config.get("position_smoothing", 0.2)
        self.max_reading_age = signal_config.get("max_reading_age", 30)
        
        # Dictionary of beacon MAC -> BeaconTracker
        self.beacons: Dict[str, BeaconTracker] = {}
        
        # Set for tracking which beacons have been registered via discovery
        self.registered_beacons = set()

    def mac_to_topic(self, mac: str) -> str:
        """Convert a MAC address to a safe topic name."""
        return f"beacon_{mac.lower().replace(':', '_')}"

    async def process_beacon_message(self, proxy_id: str, payload: dict):
        """Process a BLE beacon message from a proxy."""
        try:
            beacon_mac = payload["beacon_mac"]
            rssi = payload["rssi"]
            
            # Parse timestamp or use current time
            ts_str = payload.get("timestamp")
            if ts_str:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                timestamp = dt.timestamp()
            else:
                timestamp = time.time()
                
            # Initialize beacon tracker if needed
            if beacon_mac not in self.beacons:
                beacon_name = self.beacon_names.get(beacon_mac, f"Beacon {beacon_mac}")
                self.beacons[beacon_mac] = BeaconTracker(
                    mac=beacon_mac,
                    name=beacon_name,
                    tx_power=self.tx_power,
                    path_loss_exponent=self.path_loss_exponent,
                    rssi_smoothing=self.rssi_smoothing,
                    position_smoothing=self.position_smoothing,
                    max_reading_age=self.max_reading_age,
                )
                
            # Update the reading
            self.beacons[beacon_mac].update_reading(proxy_id, rssi, timestamp)
            
            # Register discovery if needed
            if beacon_mac not in self.registered_beacons:
                await self.register_beacon_discovery(beacon_mac)
                
            # Update position if we have enough data
            await self.update_beacon_position(beacon_mac)
                
        except KeyError as e:
            logger.error(f"Missing required field in message: {e}")
        except Exception as e:
            logger.exception(f"Error processing beacon message: {e}")

    async def register_beacon_discovery(self, mac: str):
        """Register a beacon with Home Assistant via MQTT discovery."""
        try:
            beacon = self.beacons[mac]
            topic_name = self.mac_to_topic(mac)
            
            # Device tracker config
            config = {
                "name": beacon.name,
                "state_topic": f"{MQTT_STATE_PREFIX}/{topic_name}",
                "json_attributes_topic": f"{MQTT_STATE_PREFIX}/{topic_name}",
                "unique_id": topic_name,
                "source_type": "gps",
                "device": {
                    "identifiers": [topic_name],
                    "name": beacon.name,
                    "manufacturer": "iBeacon",
                },
            }
            
            # Publish discovery message
            discovery_topic = f"{MQTT_DISCOVERY_PREFIX}/device_tracker/{topic_name}/config"
            await self.client.publish(discovery_topic, json.dumps(config), qos=1, retain=True)
            
            logger.info(f"Registered beacon {mac} as {beacon.name}")
            self.registered_beacons.add(mac)
            
        except Exception as e:
            logger.exception(f"Error registering beacon discovery: {e}")

    async def update_beacon_position(self, mac: str):
        """Calculate and publish updated beacon position."""
        try:
            beacon = self.beacons[mac]
            beacon.clean_old_readings()
            
            # Get distance estimates from each proxy
            distances = beacon.get_proxy_distances(self.proxy_positions)
            
            # Only proceed if we have enough proxies
            if len(distances) < self.min_proxies:
                return
                
            # Perform triangulation
            lat, lng, accuracy = Triangulator.trilaterate_2d(distances)
            
            if lat is None or lng is None:
                return
                
            # Update beacon position
            current_time = time.time()
            beacon.update_position(lat, lng, accuracy, current_time)
            
            # Publish updated position
            topic_name = self.mac_to_topic(mac)
            payload = {
                "latitude": beacon.latitude,
                "longitude": beacon.longitude,
                "gps_accuracy": beacon.accuracy,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            await self.client.publish(
                f"{MQTT_STATE_PREFIX}/{topic_name}", 
                json.dumps(payload), 
                qos=0
            )
            
        except Exception as e:
            logger.exception(f"Error updating beacon position: {e}")


async def main():
    """Main entry point for the BLE triangulation service."""
    # Load configuration
    config_path = os.environ.get("CONFIG_PATH", DEFAULT_CONFIG_PATH)
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return 1
        
    # Extract configuration
    proxy_positions = config.get("proxies", {})
    if not proxy_positions:
        logger.error("No proxies defined in configuration")
        return 1
        
    signal_config = config.get("signal", {})
    beacon_names = config.get("beacons", {})
    min_proxies = signal_config.get("min_proxies", 2)
    
    # MQTT connection parameters (from env or defaults)
    mqtt_host = os.environ.get("MQTT_HOST", "localhost")
    mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))
    mqtt_user = os.environ.get("MQTT_USERNAME", "")
    mqtt_password = os.environ.get("MQTT_PASSWORD", "")
    
    # Create stop event for clean shutdown
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()
        
    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(sig, signal_handler)
        
    client_id = f"ble_triangulation_{os.getpid()}"
    
    try:
        # Connect to MQTT broker
        async with mqtt.Client(
            hostname=mqtt_host,
            port=mqtt_port,
            username=mqtt_user,
            password=mqtt_password,
            client_id=client_id,
        ) as client:
            logger.info(f"Connected to MQTT broker at {mqtt_host}:{mqtt_port}")
            
            # Initialize MQTT handler
            handler = MQTTHandler(
                client, 
                proxy_positions, 
                beacon_names, 
                signal_config,
                min_proxies,
            )
            
            # Subscribe to proxy topics
            await client.subscribe(f"{MQTT_PROXY_PREFIX}/#")
            logger.info(f"Subscribed to {MQTT_PROXY_PREFIX}/#")
            
            # Process messages
            async with client.messages() as messages:
                async for message in messages:
                    # Extract proxy ID from topic
                    topic_parts = message.topic.split("/")
                    if len(topic_parts) < 2:
                        continue
                        
                    proxy_id = topic_parts[-1]
                    
                    try:
                        payload = json.loads(message.payload)
                        await handler.process_beacon_message(proxy_id, payload)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON payload: {message.payload}")
                    except Exception as e:
                        logger.exception(f"Error processing message: {e}")
                        
                    # Check if we should stop
                    if stop_event.is_set():
                        break
    
    except mqtt.MqttError as e:
        logger.error(f"MQTT Error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1
        
    logger.info("BLE triangulation service stopped")
    return 0


if __name__ == "__main__":
    # Import math here to avoid circular import in class definitions
    import math
    sys.exit(asyncio.run(main()))