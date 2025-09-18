# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project implements a BLE iBeacon triangulation system with ESPHome Bluetooth proxies and MQTT auto-discovery in Home Assistant. The system tracks Bluetooth beacons using multiple ESP32 devices and displays their estimated positions on a Home Assistant map.

## Project Structure

- `esphome_ble_proxy.yaml`: ESPHome configuration for ESP32 BLE proxies
- `triangulation_service/`: Python service for BLE triangulation
  - `main.py`: Main Python service that performs triangulation
  - `proxies.yaml`: Configuration for proxy positions and signal parameters
  - `requirements.txt`: Python dependencies
  - `Dockerfile`: Container definition for the service
- `docker-compose.yml`: Deployment configuration
- `home_assistant_example.yaml`: Example Home Assistant configuration
- `custom_components/ha_bt_advanced/`: Home Assistant integration files
  - `__init__.py`: Integration setup
  - `config_flow.py`: Configuration flow
  - `const.py`: Constants
  - `manager.py`: Core functionality manager
  - `device_tracker.py`: Device tracker entities
  - `sensor.py`: Sensor entities
  - `binary_sensor.py`: Binary sensor entities
  - `config.py`: Configuration panel
  - `esphome_wizard.py`: ESPHome configuration generator
- `README.md`: Project documentation

## Development Commands

### Python Triangulation Service

```bash
# Install dependencies
cd triangulation_service
pip install -r requirements.txt

# Run the service
python main.py

# Run with custom config
CONFIG_PATH=custom_proxies.yaml python main.py

# Run with specific MQTT settings
MQTT_HOST=homeassistant.local MQTT_PORT=1883 MQTT_USERNAME=user MQTT_PASSWORD=pass python main.py
```

### Docker Deployment

```bash
# Build the container
docker-compose build

# Run the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### ESPHome Development

```bash
# Validate ESPHome configuration
esphome config esphome_ble_proxy.yaml

# Deploy to ESP32 device
esphome run esphome_ble_proxy.yaml
```

### Home Assistant Integration Development

```bash
# Install the integration
cp -r custom_components/ha_bt_advanced ~/homeassistant/config/custom_components/

# Restart Home Assistant
ha core restart
```

## Key Components and Architecture

1. **ESPHome BLE Proxies**: ESP32 devices scan for iBeacon advertisements and publish to MQTT
2. **MQTT Messaging**: Central communication method for all components
3. **Triangulation Service**: Core Python service that:
   - Subscribes to BLE advertisement data
   - Performs triangulation calculations
   - Estimates beacon positions and accuracy
   - Publishes to Home Assistant via MQTT auto-discovery
4. **Home Assistant Integration**:
   - Integrates the triangulation service directly into HA
   - Provides a visual GUI for configuration
   - Creates device tracker entities on the map
   - Manages proxy and beacon configuration
   - Implements custom configuration UI panel

## Critical Design Requirements

**GUI-ONLY CONFIGURATION**: ALL configuration and management MUST be done through the integration's GUI config flow. NEVER require users to:
- Use Developer Tools > Services to call services manually
- Edit YAML files manually
- Use the command line
- Access any other part of Home Assistant outside the integration settings

Everything must be accessible through:
Settings > Devices & Services > HA-BT-Advanced > Configure

All features including calibration, beacon management, proxy management, and zone configuration must be available in the GUI options flow.

## Important Implementation Notes

1. The triangulation algorithm in `Triangulator` class handles both 2-point (bilateration) and 3+ point (multilateration) cases
2. RSSI values are smoothed using exponential moving average in the `RSSIBuffer` class
3. Position estimates are also smoothed in the `BeaconTracker` class
4. Accuracy values (uncertainty) are calculated from triangulation residuals
5. The Home Assistant integration provides two installation methods:
   - Built-in triangulation service 
   - Configuration for external service

## Configuration Parameters

The main configuration parameters for triangulation are:

1. Proxy positions (latitude/longitude)
2. Signal propagation parameters:
   - TX power (-59 to -75 dBm at 1m)
   - Path loss exponent (2.0-4.0)
   - RSSI smoothing factor (0-1)
   - Position smoothing factor (0-1)
   - Maximum reading age (seconds)
   - Minimum proxies for triangulation (2+)

## Extending the Project

When adding new features to the project, consider:

1. For ESPHome modifications:
   - Update both the standalone YAML and the template in `esphome_wizard.py`

2. For triangulation algorithm improvements:
   - Update both `triangulation_service/main.py` and `manager.py`

3. For UI enhancements:
   - Update the config panel in `config.py`
   - Add translations in `translations/en.json`

## Validation Steps

To ensure the integration meets Home Assistant and HACS requirements:

1. Run the comprehensive validation script:
   ```bash
   ./tools/validate.sh
   ```

2. This script checks:
   - Basic validation for manifest.json, HACS.json, services.yaml, and translations
   - Docker-based hassfest validation (same as GitHub Actions uses)
   - Docker-based HACS validation

3. Common validation issues and fixes:
   - Manifest.json keys must be properly ordered: domain, name, then alphabetical
   - Services.yaml number selectors sometimes need specific formatting for step values
   - HACS.json should only include allowed fields: name, render_readme, homeassistant

4. GitHub-specific validation requirements:
   - Add repository description and topics in GitHub settings
   - Consider adding to Home Assistant brands repository for official icon