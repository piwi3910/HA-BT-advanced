"""ESPHome configuration wizard for BLE Triangulation."""
import logging
import os
from pathlib import Path
from typing import Dict, Any

import yaml

_LOGGER = logging.getLogger(__name__)

ESPHOME_TEMPLATE = """# Auto-generated ESPHome configuration for BLE Triangulation
# Proxy ID: {proxy_id}

substitutions:
  proxy_id: {proxy_id}
  name: "${proxy_id}"
  friendly_name: "${proxy_id} BLE Proxy"

esphome:
  name: "${name}"
  friendly_name: "${friendly_name}"

esp32:
  board: esp32dev
  framework:
    type: arduino

# Enable logging
logger:

# Enable Home Assistant API
api:
  encryption:
    key: "{api_encryption_key}"

# Enable OTA updates
ota:
  password: "{ota_password}"

# Enable WiFi
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  
  # Enable fallback hotspot in case of connection failure
  ap:
    ssid: "${name} Fallback Hotspot"
    password: !secret fallback_ap_password

# Enable MQTT for proxying BLE data
mqtt:
  broker: {mqtt_broker}
  username: {mqtt_username}
  password: {mqtt_password}
  client_id: "${name}"

# Enable BLE tracking
esp32_ble_tracker:
  scan_parameters:
    interval: 1100ms
    window: 1100ms
    active: false

# Time component to provide accurate timestamps
time:
  - platform: homeassistant
    id: homeassistant_time

# Custom BLE scanner component
ibeacon:
  - id: ble_scanner
    on_ibeacon:
      then:
        - mqtt.publish:
            topic: "{mqtt_topic_prefix}/${proxy_id}"
            payload: |-
              {{
                "proxy_id": "${proxy_id}",
                "beacon_mac": "{{ format('%02X:%02X:%02X:%02X:%02X:%02X', 
                                   x.address[0], x.address[1], x.address[2], 
                                   x.address[3], x.address[4], x.address[5]) }}",
                "rssi": {{ x.rssi }},
                "timestamp": "{{ now().strftime('%Y-%m-%dT%H:%M:%SZ') }}"
              }}

# Sensor to monitor system health
sensor:
  - platform: wifi_signal
    name: "${name} WiFi Signal"
    update_interval: 60s
    
  - platform: uptime
    name: "${name} Uptime"
    update_interval: 60s
    
  - platform: internal_temperature
    name: "${name} Temperature"
    id: internal_temperature
    update_interval: 60s
"""

def generate_esphome_config(
    proxy_id: str,
    mqtt_config: Dict[str, Any],
    mqtt_topic_prefix: str,
) -> str:
    """Generate ESPHome configuration for a proxy."""
    # Generate random API encryption key and OTA password
    import random
    import string
    
    def random_string(length=32):
        """Generate a random string."""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
        
    api_encryption_key = random_string(32)
    ota_password = random_string(16)
    
    # Format the template
    config = ESPHOME_TEMPLATE.format(
        proxy_id=proxy_id,
        api_encryption_key=api_encryption_key,
        ota_password=ota_password,
        mqtt_broker=mqtt_config.get("broker", "homeassistant.local"),
        mqtt_username=mqtt_config.get("username", ""),
        mqtt_password=mqtt_config.get("password", ""),
        mqtt_topic_prefix=mqtt_topic_prefix,
    )
    
    return config

def save_esphome_config(proxy_id: str, config: str, config_dir: str) -> str:
    """Save ESPHome configuration to a file."""
    output_dir = Path(config_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = output_dir / f"{proxy_id}.yaml"
    with open(file_path, "w") as f:
        f.write(config)
        
    return str(file_path)

def create_esphome_secrets(config_dir: str, wifi_ssid: str, wifi_password: str, fallback_password: str) -> str:
    """Create ESPHome secrets.yaml file."""
    output_dir = Path(config_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    secrets = {
        "wifi_ssid": wifi_ssid,
        "wifi_password": wifi_password,
        "fallback_ap_password": fallback_password,
    }
    
    file_path = output_dir / "secrets.yaml"
    with open(file_path, "w") as f:
        yaml.dump(secrets, f, default_flow_style=False)
        
    return str(file_path)