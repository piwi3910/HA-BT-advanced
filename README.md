# HA-BT-Advanced: BLE iBeacon Triangulation for Home Assistant

This integration provides Bluetooth Low Energy (BLE) beacon triangulation using multiple ESP32 devices as proxies. It calculates beacon positions using RSSI-based triangulation and creates device tracker entities in Home Assistant.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

## Features

### ✅ What's Included
- 🗺️ **Visual Configuration Panel** - Interactive map-based interface for managing proxies, beacons, and zones
- 📍 **Map-Based Proxy Placement** - Click on the map to place proxies or drag markers to adjust positions
- 🔷 **Graphical Zone Drawing** - Draw custom zones directly on the map by clicking to define polygon boundaries
- 📡 **MQTT Integration** - Receives BLE advertisement data from ESP32 proxies via MQTT
- 📐 **Triangulation** - Calculates beacon positions using 2+ proxies (bilateration/multilateration)
- 🎯 **Device Tracking** - Creates device_tracker entities that appear on the Home Assistant map
- 📊 **Sensors** - RSSI signal strength, distance estimates, and accuracy metrics
- 🏠 **Zone Detection** - Detects when beacons enter/leave defined zones
- 🔔 **Notifications** - Alerts for new beacons, missing beacons, and offline proxies
- 🛠️ **Service Calls** - Full API for automation and advanced configuration

## Installation

### Via HACS (Recommended)

1. Add this repository as a custom repository in HACS:
   - URL: `https://github.com/piwi3910/HA-BT-advanced`
   - Category: Integration
2. Install "HA-BT-Advanced" from HACS
3. Restart Home Assistant
4. Add the integration via Settings → Devices & Services → Add Integration → "HA-BT-Advanced"

### Manual Installation

1. Copy `custom_components/ha_bt_advanced` to your `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration via Settings → Devices & Services

## Initial Setup

### Step 1: Configure the Integration

When adding the integration, you'll be prompted to configure:
- **Service Mode**: Choose "Built-in triangulation service"
- **Signal Parameters**:
  - TX Power: -59 (typical for most beacons)
  - Path Loss Exponent: 2.0 (adjust based on environment)
  - RSSI Smoothing: 0.3
  - Position Smoothing: 0.2
  - Max Reading Age: 30 seconds
  - Min Proxies: 2

### Step 2: Access the Configuration Panel

After installation, a new sidebar item "BT Advanced" will appear in your Home Assistant interface. Click it to open the visual configuration panel with:
- Interactive map for proxy and zone management
- Lists of configured proxies, beacons, and zones
- Tools for adding and removing devices

### Step 3: Set Up ESP32 Proxies

1. **Flash ESP32 devices** with the provided ESPHome configuration:
```yaml
# esphome_ble_proxy.yaml
esphome:
  name: ble-proxy-1
  platform: ESP32
  board: esp32dev

wifi:
  ssid: "YOUR_WIFI_SSID"
  password: "YOUR_WIFI_PASSWORD"

mqtt:
  broker: YOUR_MQTT_BROKER_IP
  username: mqtt_user
  password: mqtt_password

esp32_ble_tracker:
  scan_parameters:
    interval: 320ms
    window: 48ms
    active: false

bluetooth_proxy:
  active: false

ble_tracker:
  on_ble_advertise:
    - then:
        - mqtt.publish:
            topic: ble_triangulation/advertisements/ble-proxy-1
            payload: !lambda |-
              char buffer[256];
              sprintf(buffer, "{\"mac\":\"%s\",\"rssi\":%d,\"timestamp\":\"%s\"}",
                      x.address_str().c_str(), x.get_rssi(),
                      id(homeassistant_time).now().timestamp);
              return std::string(buffer);
```

2. **Add proxies** using the visual interface:
   - Open the "BT Advanced" panel from the sidebar
   - Click the "Add Proxy" button or select the proxy tool on the map
   - Click on the map to place the proxy at the desired location
   - Enter a unique proxy ID (e.g., "living_room_proxy")
   - Save the proxy configuration

   Alternatively, you can use the service call:
   ```yaml
   service: ha_bt_advanced.add_proxy
   data:
     proxy_id: "ble-proxy-1"
     latitude: 37.7749
     longitude: -122.4194
   ```

### Step 4: Add Beacons

Beacons can be added through the visual interface:
- Click "Add Beacon" in the BT Advanced panel
- Enter the beacon's MAC address and friendly name
- Select a category (person, item, pet, vehicle, other)
- Choose an icon for visual identification

Or use the service call:
```yaml
service: ha_bt_advanced.add_beacon
data:
  mac_address: "AA:BB:CC:DD:EE:FF"
  name: "My Keys"
  category: "item"  # person, item, pet, vehicle, other
  icon: "mdi:key"
  tx_power: -59
  path_loss_exponent: 2.0
```

### Step 5: Configure Zones (Optional)

Draw zones directly on the map:
1. Click the "Draw Zone" button or select the zone tool
2. Click multiple points on the map to define the zone boundary
3. Complete the zone by clicking near the first point
4. Enter zone name and type (room, home, work, custom)
5. Save the zone

Or define zones via service call:

```yaml
service: ha_bt_advanced.add_zone
data:
  zone_id: "living_room"
  name: "Living Room"
  type: "room"  # room, home, work, custom
  coordinates: |
    [[37.7749, -122.4194],
     [37.7750, -122.4194],
     [37.7750, -122.4193],
     [37.7749, -122.4193]]
  icon: "mdi:sofa"
```

## Using the Visual Configuration Panel

The BT Advanced panel provides an intuitive interface for managing your BLE tracking system:

### Map Interface
- **View Mode**: Pan and zoom the map to explore your setup
- **Add Proxy Tool**: Click on the map to place new proxies
- **Draw Zone Tool**: Click multiple points to create zone boundaries

### Sidebar Controls
- **Proxies Section**: View all proxies with online/offline status
- **Beacons Section**: List of tracked beacons with current location
- **Zones Section**: Configured zones with edit/delete options

### Real-Time Updates
- Beacon positions update automatically on the map
- Proxy status indicators show connectivity
- Zone presence is highlighted when beacons enter/leave

## Managing Devices via Service Calls

### Managing Beacons

#### View All Beacons
Beacons appear as device_tracker entities with the naming pattern:
- `device_tracker.beacon_aa_bb_cc_dd_ee_ff`

Each beacon also creates:
- `sensor.beacon_aa_bb_cc_dd_ee_ff_rssi` - Signal strength
- `sensor.beacon_aa_bb_cc_dd_ee_ff_distance` - Estimated distance
- `sensor.beacon_aa_bb_cc_dd_ee_ff_accuracy` - Position accuracy
- `binary_sensor.beacon_aa_bb_cc_dd_ee_ff_presence` - Presence detection

#### Remove a Beacon
```yaml
service: ha_bt_advanced.remove_beacon
data:
  mac_address: "AA:BB:CC:DD:EE:FF"
```

#### Calibrate a Beacon
```yaml
service: ha_bt_advanced.calibrate
data:
  mac_address: "AA:BB:CC:DD:EE:FF"
  tx_power: -65
  path_loss_exponent: 2.5
```

### Managing Proxies

#### List Proxies
Check the integration's device page or look for binary sensors:
- `binary_sensor.proxy_ble_proxy_1_connectivity`

#### Remove a Proxy
```yaml
service: ha_bt_advanced.remove_proxy
data:
  proxy_id: "ble-proxy-1"
```

### Restart the Service
```yaml
service: ha_bt_advanced.restart
```

## Configuration Files

The integration stores configuration in your Home Assistant config directory:

- **Beacons**: `config/ha_bt_beacons/*.yaml`
- **Proxies**: `config/ha_bt_proxies/*.yaml`
- **Zones**: `config/ha_bt_zones/*.yaml`

You can manually edit these YAML files and restart the integration to apply changes.

## Troubleshooting

### No Beacons Detected
1. Verify ESP32 proxies are online: Check `binary_sensor.proxy_*_connectivity`
2. Ensure MQTT is working: Check MQTT logs for messages on `ble_triangulation/advertisements/+`
3. Confirm beacons are transmitting: Use a BLE scanner app to verify
4. Check you have at least 2 proxies with known coordinates

### Poor Position Accuracy
1. Add more proxies (3-4 recommended for good accuracy)
2. Adjust signal parameters:
   - Indoor environments: path_loss_exponent = 2.5-3.5
   - Open spaces: path_loss_exponent = 2.0-2.5
3. Increase smoothing factors if positions jump around
4. Ensure proxy coordinates are accurate

### Proxies Show Offline
1. Check ESP32 WiFi connection
2. Verify MQTT broker is accessible
3. Confirm MQTT credentials are correct
4. Check firewall rules allow MQTT traffic

### Integration Won't Start
1. Check Home Assistant logs for errors
2. Verify all required fields in configuration
3. Ensure no duplicate MAC addresses or proxy IDs
4. Try removing and re-adding the integration

## Service Reference

| Service | Description | Required Fields |
|---------|-------------|-----------------|
| `ha_bt_advanced.restart` | Restart the triangulation service | None |
| `ha_bt_advanced.add_beacon` | Add a new beacon | `mac_address`, `name` |
| `ha_bt_advanced.remove_beacon` | Remove a beacon | `mac_address` |
| `ha_bt_advanced.add_proxy` | Add a new proxy | `proxy_id`, `latitude`, `longitude` |
| `ha_bt_advanced.remove_proxy` | Remove a proxy | `proxy_id` |
| `ha_bt_advanced.add_zone` | Add a zone | `zone_id`, `name`, `type`, `coordinates` |
| `ha_bt_advanced.remove_zone` | Remove a zone | `zone_id` |
| `ha_bt_advanced.calibrate` | Calibrate beacon signal | `mac_address` |

## Example Automations

### Notify When Keys Leave Home
```yaml
automation:
  - alias: "Keys Left Home"
    trigger:
      - platform: state
        entity_id: device_tracker.beacon_aa_bb_cc_dd_ee_ff
        from: "home"
        to: "not_home"
    action:
      - service: notify.mobile_app
        data:
          message: "Your keys have left home!"
```

### Track Pet in Backyard
```yaml
automation:
  - alias: "Dog in Backyard"
    trigger:
      - platform: state
        entity_id: binary_sensor.beacon_pet_collar_zone_backyard
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Dog is in the backyard"
```

## Technical Details

### Triangulation Method
- **2 Proxies**: Uses bilateration (intersection of two circles)
- **3+ Proxies**: Uses multilateration with weighted least squares
- **Accuracy**: Calculated from triangulation residuals

### Signal Processing
- RSSI to distance: `distance = 10^((tx_power - rssi) / (10 * path_loss_exponent))`
- Exponential moving average for RSSI smoothing
- Position smoothing to reduce jitter

### MQTT Topics
- Advertisements: `ble_triangulation/advertisements/{proxy_id}`
- Expected payload format:
```json
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "rssi": -70,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Development

### Validation
Run the validation script to check HACS compatibility:
```bash
./tools/validate.sh
```

### File Structure
```
custom_components/ha_bt_advanced/
├── __init__.py          # Integration setup and services
├── config_flow.py       # Configuration flow
├── manager.py           # Core triangulation manager
├── triangulation.py     # Triangulation algorithms
├── device_tracker.py    # Device tracker entities
├── sensor.py            # Sensor entities
├── binary_sensor.py     # Binary sensor entities
├── zones.py             # Zone management
├── const.py             # Constants
├── manifest.json        # Integration manifest
├── services.yaml        # Service definitions
└── translations/        # UI translations
```

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/piwi3910/HA-BT-advanced/issues) page.

## Author

Pascal Watteel (pascal@watteel.com)

## License

This project is licensed under the MIT License - see the LICENSE file for details.