# HA-BT-Advanced: BLE iBeacon Triangulation with ESPHome

This project implements a system for tracking Bluetooth Low Energy (BLE) beacons using multiple ESPHome-based ESP32 devices as proxies. It performs triangulation to estimate beacon positions, which are then displayed on a Home Assistant map.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

## Features

- 📡 Multiple ESP32 devices with ESPHome firmware act as BLE scanning proxies
- 🔄 MQTT messaging for BLE scan data
- 📐 Custom triangulation service using Python
- 🗺️ Home Assistant integration via MQTT auto-discovery
- ⚙️ Tunable signal propagation model
- 🔄 Position smoothing and accuracy estimation
- 🧙 Complete Home Assistant integration with configuration UI

## System Architecture

1. **ESPHome Proxies**: ESP32 devices running custom ESPHome firmware scan for BLE advertisements from iBeacons
2. **MQTT Bridge**: BLE data is published to MQTT topics
3. **Triangulation Service**: Python service subscribes to MQTT, performs triangulation, and publishes location data
4. **Home Assistant**: Displays beacon locations on a map with accuracy circles

## Installation Options

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

### Option 2: Home Assistant Manual Integration 

1. Copy the `custom_components/ha_bt_advanced` directory to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings** → **Devices & Services** → **Add Integration** and search for "HA-BT-Advanced"
4. Follow the setup wizard to configure the integration

### Option 3: Standalone Installation

#### 1. ESPHome Proxy Setup

1. Flash multiple ESP32 devices with the provided ESPHome configuration
2. For each device, modify the `proxy_id` in `substitutions` and deploy

```yaml
# Example for kitchen_proxy
substitutions:
  proxy_id: kitchen_proxy  # Change for each ESP32
  name: "${proxy_id}"
  friendly_name: "${proxy_id} BLE Proxy"
```

3. Make sure to set up your Wi-Fi and MQTT credentials using ESPHome secrets

#### 2. Configure Proxy Positions

Edit `triangulation_service/proxies.yaml` to set the real-world locations of your proxies:

```yaml
proxies:
  kitchen_proxy:
    latitude: 25.1201
    longitude: 55.3089
  bedroom_proxy:
    latitude: 25.1203
    longitude: 55.3091
```

Also configure your beacons in the same file:

```yaml
beacons:
  "C7:9B:6A:32:BB:0E": "Jayden's Backpack"
```

#### 3. Run the Triangulation Service

**Using Docker (recommended):**

```bash
# Set your MQTT details
export MQTT_HOST=your-mqtt-host
export MQTT_USERNAME=your-username
export MQTT_PASSWORD=your-password

# Start the service
docker-compose up -d
```

**Manual Installation:**

```bash
cd triangulation_service
pip install -r requirements.txt
python main.py
```

## Home Assistant Integration Features

The Home Assistant integration provides a complete UI for managing the triangulation system:

### Configuration Options

- TX Power at 1 meter (calibration parameter)
- Path Loss Exponent (environmental parameter)
- RSSI and Position Smoothing factors
- Minimum proxies required for triangulation

### Proxy Management

- Visual map-based interface for adding proxy locations
- Easy management of proxy devices
- Automatic ESPHome configuration generation

### Beacon Management

- Automatic beacon discovery when detected
- Custom naming of beacons
- Beacon presence detection

### Entities Created

For each beacon, the integration creates:

- Device tracker (for map display)
- Signal strength sensor
- Distance sensor
- Presence binary sensor

## Signal Propagation Tuning

The relationship between RSSI and distance is affected by environmental factors. You can tune the model by adjusting these parameters in the integration settings:

- **TX Power**: Measured power at 1 meter (typical values between -59 and -75)
- **Path Loss Exponent**: 2.0 for free space, 2.7-3.5 for indoor environments

## Technical Details

### MQTT Topics

- BLE advertisements: `ble-triangulation/<proxy_id>`
- Beacon locations: `ble-location/beacon_<mac>`
- Discovery topics: `homeassistant/device_tracker/beacon_<mac>/config`

### Triangulation Algorithm

The service uses a weighted trilateration algorithm:

1. RSSI values are converted to estimated distances using the path loss model
2. For multiple proxies, their distance measurements create circles
3. The most likely position is calculated from circle intersections
4. Accuracy is estimated based on the residuals of the solution

## Troubleshooting

- **No beacons detected**: Ensure your iBeacons are active and within range of at least two proxies
- **Poor accuracy**: Try adjusting the `tx_power` and `path_loss_exponent` values
- **Erratic movement**: Increase smoothing factors in the configuration settings

## Future Enhancements

- Mobile device BLE + GPS fusion
- Floorplan integration
- Room-level zoning
- 3D positioning with altitude