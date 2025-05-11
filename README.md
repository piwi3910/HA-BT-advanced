# HA-BT-Advanced: BLE iBeacon Triangulation with ESPHome

This project implements a system for tracking Bluetooth Low Energy (BLE) beacons using multiple ESPHome-based ESP32 devices as proxies. It performs triangulation to estimate beacon positions and displays them on your Home Assistant map - all through an easy-to-use graphical interface with automatic discovery.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

## Key Features

- 🧙‍♂️ **Complete GUI Setup** - No YAML editing required! Everything configurable in the UI
- 🔍 **Auto-Discovery** - Automatically detects and adds new beacons as they appear
- 📡 Multiple ESP32 devices with ESPHome firmware act as BLE scanning proxies
- 🔄 MQTT messaging for BLE scan data
- 📐 Custom triangulation service with tunable path-loss model
- 🗺️ Home Assistant map integration with accuracy circles
- 📱 Track any BLE iBeacon device (tags, smartphones, wearables)

## Quick Setup Wizard

The integration features a step-by-step setup wizard that handles all configuration:

1. **Base setup** - Configure signal parameters with suggested defaults
2. **Proxy configuration** - Add proxies visually on a map
3. **Beacon auto-discovery** - Beacons are automatically detected and named

**No YAML editing required!** The integration provides a complete graphical interface for all configuration.

## System Architecture

1. **ESPHome Proxies**: ESP32 devices running custom ESPHome firmware scan for iBeacon advertisements
2. **MQTT Bridge**: BLE data is published through MQTT
3. **Triangulation Service**: Built directly into Home Assistant, performs triangulation calculations
4. **Home Assistant Integration**: Visual management of proxies and beacons through a fully graphical interface

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

## The Configuration Wizard

After installation, the integration provides a step-by-step configuration wizard:

### Step 1: Basic Configuration

![Configuration Screenshot](https://github.com/piwi3910/HA-BT-advanced/raw/main/images/config_screen.png)

- Set signal parameters (with reasonable defaults)
- Configure MQTT topic prefixes
- Enable/disable the built-in triangulation service

### Step 2: Proxy Configuration

Navigate to "HA-BT-Advanced" in the Configuration panel to:

- Add proxies visually using a map interface
- Enter proxy locations by dragging pins on the map
- Generate and download ESP32 firmware files directly from the UI

### Step 3: Beacon Management

Beacons are automatically discovered when they come into range of your proxies. From the UI you can:

- Rename detected beacons with friendly names
- Monitor signal strength and estimated distance
- View all beacons on the Home Assistant map
- Add beacons manually if needed

## Home Assistant Entities

For each beacon, the integration automatically creates:

- **Device Tracker Entity**: Shows the beacon location on your map
- **Signal Strength Sensor**: Tracks RSSI values from each proxy
- **Distance Sensor**: Shows estimated distance in meters
- **Presence Binary Sensor**: Detects if the beacon is currently present

## Signal Propagation Tuning

The relationship between RSSI and distance is affected by environmental factors. The UI allows you to tune:

- **TX Power**: Measured power at 1 meter (typical values between -59 and -75)
- **Path Loss Exponent**: 2.0 for free space, 2.7-3.5 for indoor environments
- **RSSI Smoothing**: Reduces signal fluctuations 
- **Position Smoothing**: Creates smoother movement paths

## Troubleshooting

- **No beacons detected**: Ensure your iBeacons are active and within range of at least two proxies
- **Poor accuracy**: Adjust the `tx_power` and `path_loss_exponent` values in the integration settings
- **Erratic movement**: Increase smoothing factors in the configuration settings

## Advanced: Standalone Mode

For advanced users who prefer manual configuration, the repository also includes:

- `esphome_ble_proxy.yaml`: Base ESPHome configuration for proxies
- `triangulation_service/`: Standalone Python triangulation service
- `docker-compose.yml`: Docker configuration for standalone deployment

See the [Advanced Configuration](https://github.com/piwi3910/HA-BT-advanced/wiki) page in the wiki for details.

## Future Enhancements

- Mobile device BLE + GPS fusion
- Floorplan integration
- Room-level zoning
- 3D positioning with altitude

## Author

Pascal Watteel (pascal@watteel.com)