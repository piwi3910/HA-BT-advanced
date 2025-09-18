# HA-BT-Advanced: BLE iBeacon Triangulation

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

Track Bluetooth iBeacons using multiple ESPHome proxies and display their estimated positions on the Home Assistant map - all through an easy-to-use graphical interface with automatic discovery.

![Map Example](https://github.com/piwi3910/HA-BT-advanced/raw/main/images/map_example.png)

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

## Installation

### HACS Installation

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add this repository URL: `https://github.com/piwi3910/HA-BT-advanced`
5. Select "Integration" as the category
6. Click "Add"
7. Find "HA-BT-Advanced" in the list of integrations and click "Download"
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/ha_bt_advanced` directory to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration** and search for "HA-BT-Advanced"
2. Configure the basic options for the triangulation service
3. Add your ESPHome proxies through the visual configuration panel
4. As beacons are detected, they will automatically appear on your map

## Documentation

Full documentation is available in the [GitHub repository](https://github.com/piwi3910/HA-BT-advanced).

[releases-shield]: https://img.shields.io/github/release/piwi3910/HA-BT-advanced.svg?style=for-the-badge
[releases]: https://github.com/piwi3910/HA-BT-advanced/releases
[license-shield]: https://img.shields.io/github/license/piwi3910/HA-BT-advanced.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge