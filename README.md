# HA-BT-Advanced: BLE iBeacon Triangulation with ESPHome

This project implements a system for tracking Bluetooth Low Energy (BLE) beacons using multiple ESPHome-based ESP32 devices as proxies. It performs triangulation to estimate beacon positions and displays them on your Home Assistant map - all through an easy-to-use graphical interface with automatic discovery.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

## Key Features

- 🧙‍♂️ **Complete GUI Setup** - No YAML editing required! Everything configurable in the UI
- 🗺️ **Visual Configuration Panel** - Set up proxies, beacons, and zones with a map interface
- 🔍 **Auto-Discovery** - Automatically detects and adds new beacons as they appear
- 📡 **ESP32 Proxy Integration** - Multiple ESP32 devices with auto-generated ESPHome firmware
- 📐 **Advanced Triangulation** - Custom algorithms with signal and position smoothing
- 🏠 **Zone Management** - Define custom zones and track beacon presence in zones
- 📱 **Multi-Category Tracking** - Specialized tracking for people, pets, items, and vehicles
- 🔔 **Notifications** - Get alerts when proxies go offline or beacons go missing

## Quick Setup Wizard

The integration features a step-by-step setup wizard that handles all configuration:

1. **Base setup** - Configure signal parameters with suggested defaults
2. **Environment Selection** - Choose presets for home, office, or open spaces
3. **Proxy configuration** - Add proxies visually on a map
4. **Zone configuration** - Define areas on the map for presence detection
5. **Beacon management** - Categorize and customize auto-discovered beacons

**No YAML editing required!** The integration provides a complete graphical interface for all configuration.

## System Architecture

1. **ESPHome Proxies**: ESP32 devices running custom ESPHome firmware scan for iBeacon advertisements
2. **MQTT Bridge**: BLE data is published through MQTT
3. **Triangulation Service**: Built directly into Home Assistant, performs triangulation calculations
4. **Zone Management**: Custom polygonal zones for presence detection
5. **Home Assistant Integration**: Visual management of proxies and beacons through a fully graphical interface

## Installation

### Option 1: HACS Installation (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add this repository URL: `https://github.com/piwi3910/HA-BT-advanced`
5. Select "Integration" as the category
6. Click "Add"
7. Find "HA-BT-Advanced" in the list of integrations and click "Download"
8. Restart Home Assistant
9. Go to **Settings** → **Devices & Services** → **Add Integration** and search for "HA-BT-Advanced"
10. Follow the setup wizard to configure the integration

### Option 2: Manual Installation 

1. Copy the `custom_components/ha_bt_advanced` directory to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings** → **Devices & Services** → **Add Integration** and search for "HA-BT-Advanced"
4. Follow the setup wizard to configure the integration

## The Configuration Panel

After installation, access the configuration panel from the sidebar:

### Proxy Configuration

- Add proxies visually using a map interface
- Enter proxy locations by dragging pins on the map
- Manage proxy configuration with a user-friendly UI
- Monitor proxy status with connectivity sensors

### Beacon Management

Beacons are automatically discovered when they come into range of your proxies. From the UI you can:

- Rename detected beacons with friendly names
- Categorize beacons as people, pets, items, or vehicles
- Choose custom icons based on beacon category
- Monitor signal strength and estimated distance
- View all beacons on the Home Assistant map
- Calibrate beacons for more accurate positioning

### Zone Configuration

Define custom zones on the map to track beacon presence:

- Create zones by drawing polygons on a map
- Name and categorize zones (home, work, room, custom)
- Track when beacons enter or leave zones
- Get notifications for zone changes
- Use zone presence in automations

### ESPHome Configuration

Generate and download ESPHome configuration for your ESP32 proxies:

- Automatically generate YAML configuration
- Pre-configured MQTT settings for instant connection
- Easy setup with WiFi and broker credentials
- Download and flash directly to your ESP32 devices

## Home Assistant Entities

For each beacon, the integration automatically creates:

- **Device Tracker Entity**: Shows the beacon location on your map
- **Signal Strength Sensor**: Tracks RSSI values from each proxy
- **Distance Sensor**: Shows estimated distance in meters
- **Accuracy Sensor**: Indicates positioning accuracy in meters
- **Zone Sensor**: Shows which zone the beacon is currently in
- **Presence Binary Sensor**: Detects if the beacon is currently present
- **Zone Presence Binary Sensors**: One for each zone to track presence

For each proxy, the integration creates:

- **Connectivity Binary Sensor**: Shows if the proxy is online

## Signal Propagation Tuning

The relationship between RSSI and distance is affected by environmental factors. The UI allows you to tune:

- **TX Power**: Measured power at 1 meter (typical values between -59 and -75)
- **Path Loss Exponent**: 2.0 for free space, 2.7-3.5 for indoor environments
- **RSSI Smoothing**: Reduces signal fluctuations 
- **Position Smoothing**: Creates smoother movement paths

### Environment Presets

Choose from presets for common environments:

- **Home**: Optimized for residential settings
- **Office**: Tuned for office environments with partitions
- **Open Space**: For large open areas
- **Custom**: Manually tune all parameters

## Services

The integration provides several services for automation:

- **restart**: Restart the BLE Triangulation service
- **add_beacon**: Add a new beacon manually
- **remove_beacon**: Remove a beacon from the system
- **add_proxy**: Add a new ESP32 proxy
- **remove_proxy**: Remove a proxy from the system
- **add_zone**: Add a new zone for location tracking
- **remove_zone**: Remove a zone from the system
- **calibrate**: Calibrate a beacon with new signal parameters
- **generate_esphome_config**: Generate an ESPHome configuration for a proxy

## Troubleshooting

- **No beacons detected**: Ensure your iBeacons are active and within range of at least two proxies
- **Poor accuracy**: Adjust the `tx_power` and `path_loss_exponent` values in the integration settings
- **Erratic movement**: Increase smoothing factors in the configuration settings
- **Proxy offline**: Check your ESP32 device's connection to WiFi and MQTT
- **Zone detection issues**: Ensure your zones have properly defined coordinates

## Advanced: Standalone Mode

For advanced users who prefer manual configuration, the repository also includes:

- `esphome_ble_proxy.yaml`: Base ESPHome configuration for proxies
- `triangulation_service/`: Standalone Python triangulation service
- `docker-compose.yml`: Docker configuration for standalone deployment

See the [Advanced Configuration](https://github.com/piwi3910/HA-BT-advanced/wiki) page in the wiki for details.

## Future Enhancements

- Mobile device BLE + GPS fusion
- Floorplan integration
- 3D positioning with altitude
- Relative distance between beacons
- Tag-to-tag proximity detection

## Development

### Local Validation

This integration includes a local validation script to check for HACS and Home Assistant compatibility:

```bash
./tools/validate.sh
```

This script checks:
- manifest.json requirements
- HACS.json requirements
- services.yaml formatting
- translations structure

For more details, see [VALIDATION.md](VALIDATION.md).

## Author

Pascal Watteel (pascal@watteel.com)

## Repository Notes

For developers and maintainers:

1. Please ensure this repository has:
   - A descriptive GitHub repository description
   - Appropriate topics (home-assistant, homeassistant, hacs, bluetooth, etc.)
   - Proper validation setup (see VALIDATION.md)

2. Run local validation before pushing changes:
   ```bash
   ./tools/validate.sh
   ```