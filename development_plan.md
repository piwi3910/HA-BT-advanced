# Development Plan for HA-BT-Advanced Integration

This document outlines the work needed to deliver a fully GUI-based configuration experience with no YAML editing required.

## 1. Complete Configuration Wizard

### Tasks:
- [ ] Implement a multi-step configuration flow when adding the integration
- [ ] Create UI for mapping beacons to users/items (friendly names, icons)
- [ ] Add configuration for zones and room mapping
- [ ] Implement full signal parameter configuration with reasonable defaults
- [ ] Create a testing/calibration UI for signal propagation parameters

### Implementation:
- Extend config_flow.py to include multiple configuration steps
- Add user-friendly explanations and help text for each configuration option
- Include presets for common environments (home, office, etc.)
- Add validation for all user inputs

```python
# Example of expanded configuration flow
class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA-BT-Advanced."""
    
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH
    
    def __init__(self):
        """Initialize the flow."""
        self.config_data = {}
        
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            self.config_data.update(user_input)
            return await self.async_step_environment()
            
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_MQTT_TOPIC, default=DEFAULT_MQTT_TOPIC_PREFIX): str,
                vol.Required(CONF_SERVICE_ENABLED, default=True): bool,
            }),
        )
    
    async def async_step_environment(self, user_input=None):
        """Configure environment parameters."""
        if user_input is not None:
            self.config_data[CONF_SIGNAL_PARAMETERS] = {
                CONF_TX_POWER: user_input[CONF_TX_POWER],
                CONF_PATH_LOSS_EXPONENT: user_input[CONF_PATH_LOSS_EXPONENT],
                CONF_RSSI_SMOOTHING: user_input[CONF_RSSI_SMOOTHING],
                CONF_POSITION_SMOOTHING: user_input[CONF_POSITION_SMOOTHING],
                CONF_MAX_READING_AGE: user_input[CONF_MAX_READING_AGE],
                CONF_MIN_PROXIES: user_input[CONF_MIN_PROXIES],
            }
            return await self.async_step_finalize()
        
        # Define different presets for different environments
        PRESETS = {
            "home": {
                CONF_TX_POWER: -59,
                CONF_PATH_LOSS_EXPONENT: 2.5,
                CONF_RSSI_SMOOTHING: 0.3,
                CONF_POSITION_SMOOTHING: 0.2,
            },
            "office": {
                CONF_TX_POWER: -63,
                CONF_PATH_LOSS_EXPONENT: 3.0,
                CONF_RSSI_SMOOTHING: 0.4,
                CONF_POSITION_SMOOTHING: 0.3,
            },
            "open_space": {
                CONF_TX_POWER: -59,
                CONF_PATH_LOSS_EXPONENT: 2.0,
                CONF_RSSI_SMOOTHING: 0.2,
                CONF_POSITION_SMOOTHING: 0.1,
            },
        }
        
        # Default preset
        preset = PRESETS["home"]
        
        return self.async_show_form(
            step_id="environment",
            data_schema=vol.Schema({
                vol.Required(CONF_TX_POWER, default=preset[CONF_TX_POWER]): 
                    vol.All(vol.Coerce(int), vol.Range(min=-100, max=0)),
                vol.Required(CONF_PATH_LOSS_EXPONENT, default=preset[CONF_PATH_LOSS_EXPONENT]): 
                    vol.All(vol.Coerce(float), vol.Range(min=1.0, max=5.0)),
                vol.Required(CONF_RSSI_SMOOTHING, default=preset[CONF_RSSI_SMOOTHING]): 
                    vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                vol.Required(CONF_POSITION_SMOOTHING, default=preset[CONF_POSITION_SMOOTHING]): 
                    vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                vol.Required(CONF_MAX_READING_AGE, default=30): 
                    vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                vol.Required(CONF_MIN_PROXIES, default=2): 
                    vol.All(vol.Coerce(int), vol.Range(min=2, max=10)),
            }),
            description_placeholders={
                "preset_options": "Home, Office, Open Space"
            },
        )
    
    async def async_step_finalize(self, user_input=None):
        """Create the config entry."""
        return self.async_create_entry(
            title="HA-BT-Advanced",
            data=self.config_data,
        )
```

## 2. Complete Proxy Management UI

### Tasks:
- [ ] Create a full-fledged configuration panel for proxy management
- [ ] Implement visual map interface with drag-and-drop proxy placement
- [ ] Add one-click ESPHome configuration generation and download
- [ ] Implement a WiFi and MQTT credential form for ESPHome config
- [ ] Include status monitoring for proxies (online/offline)
- [ ] Support bulk operations and proxy grouping

### Implementation:
- Update config.py to use the correct domain (ha_bt_advanced)
- Add UI components for proxy management with full drag-and-drop support
- Create an ESPHome configuration download endpoint
- Implement a more robust map interface with marker drag support

```javascript
// Example enhanced map interface
_initMap() {
    const mapElement = this.querySelector('#proxyMap');
    if (mapElement && window.homeAssistant) {
        const hass = window.homeAssistant.hass;
        mapElement.hass = hass;
        
        // Center map on home coordinates
        if (hass.config && hass.config.latitude && hass.config.longitude) {
            mapElement.latitude = hass.config.latitude;
            mapElement.longitude = hass.config.longitude;
            mapElement.zoom = 15;
        }
        
        // Enable marker drag and drop
        mapElement.addEventListener('marker-dragged', (event) => {
            const { entity_id, latitude, longitude } = event.detail;
            const proxyId = entity_id.replace('proxy.', '');
            
            // Update form with new coordinates
            this.querySelector('#latitude').value = latitude;
            this.querySelector('#longitude').value = longitude;
            this.querySelector('#proxyId').value = proxyId;
            
            // Auto-update if this is an existing proxy
            if (this._proxies.some(p => p.id === proxyId)) {
                this._handleUpdateProxy(proxyId, latitude, longitude);
            }
        });
        
        // Add click handler for adding new proxies
        mapElement.addEventListener('click', (event) => {
            if (event.detail && event.detail.latitude && event.detail.longitude) {
                // Fill the form with the clicked location
                this.querySelector('#latitude').value = event.detail.latitude;
                this.querySelector('#longitude').value = event.detail.longitude;
            }
        });
    }
}
```

## 3. Complete Beacon Management UI

### Tasks:
- [ ] Create a dedicated UI for beacon management
- [ ] Implement UI for mapping beacons to users or items
- [ ] Add support for custom icons, colors, and categories
- [ ] Create a beacon discovery view with auto-assignment options
- [ ] Implement a "calibration mode" for tuning signal parameters
- [ ] Add visualization for historical paths and common locations

### Implementation:
- Create a new beacon_manager.js component for the UI
- Implement API endpoints for beacon management
- Add beacon configuration options in the UI
- Create data visualization components for beacon tracking

```html
<!-- Example Beacon Management UI -->
<ha-card header="Beacon Management">
    <div class="card-content">
        <h3>Discovered Beacons</h3>
        <div class="beacon-list">
            <!-- Beacons will be rendered here -->
        </div>
        
        <h3>Add/Edit Beacon</h3>
        <div class="beacon-form">
            <div class="form-row">
                <div class="form-group">
                    <label for="beaconMac">MAC Address</label>
                    <input type="text" id="beaconMac" placeholder="XX:XX:XX:XX:XX:XX">
                </div>
                <div class="form-group">
                    <label for="beaconName">Friendly Name</label>
                    <input type="text" id="beaconName" placeholder="John's Keys">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="beaconIcon">Icon</label>
                    <ha-icon-picker id="beaconIcon"></ha-icon-picker>
                </div>
                <div class="form-group">
                    <label for="beaconCategory">Category</label>
                    <select id="beaconCategory">
                        <option value="person">Person</option>
                        <option value="item">Item</option>
                        <option value="pet">Pet</option>
                    </select>
                </div>
            </div>
            <div class="actions">
                <button id="saveBeaconBtn">Save Beacon</button>
            </div>
        </div>
    </div>
</ha-card>
```

## 4. Complete Triangulation Implementation 

### Tasks:
- [ ] Port the full triangulation algorithm from the Python service
- [ ] Implement proper distance calculation from RSSI values
- [ ] Create position calculation from multiple proxies
- [ ] Add position smoothing and filtering
- [ ] Add accuracy calculation based on signal quality

### Implementation:
- Port the RSSIBuffer, BeaconTracker, and Triangulator classes
- Implement proper position calculations with all smoothing options
- Add accuracy estimation based on signal quality

## 5. Zone and Room Mapping

### Tasks:
- [ ] Create a UI for defining zones and rooms
- [ ] Implement polygon drawing on the map for zone definition
- [ ] Add room-level detection based on signal strength
- [ ] Create configurable zone events and automations
- [ ] Add UI for zone assignment and properties

### Implementation:
- Create a zone_manager.js component
- Add API endpoints for zone management
- Implement zone detection logic in the manager

## 6. Complete Auto-Discovery Flow

### Tasks:
- [ ] Implement automatic beacon discovery and registration
- [ ] Create a UI for assigning discovered beacons
- [ ] Add notification system for new beacon discovery
- [ ] Implement batch operations for discovered beacons

### Implementation:
- Add discovery logic in the MQTT handler
- Create a discovery queue with UI for assignment
- Add notification system for new beacons

## 7. ESPHome Integration

### Tasks:
- [ ] Complete the ESPHome configuration generator
- [ ] Add WiFi setup UI for ESPHome devices
- [ ] Create a QR code option for ESPHome Flash
- [ ] Implement proxy health monitoring

### Implementation:
- Complete the esphome_wizard.py implementation
- Add UI components for WiFi setup
- Create a download API endpoint

## 8. Documentation and User Experience

### Tasks:
- [ ] Create comprehensive documentation with screenshots
- [ ] Implement first-run tutorial and tips
- [ ] Add interactive help in the UI
- [ ] Create troubleshooting guides
- [ ] Add example configurations and templates

## 9. Testing and Deployment

### Tasks:
- [ ] Conduct thorough testing with real hardware
- [ ] Create automated tests for triangulation algorithm
- [ ] Test UI on various screen sizes and devices
- [ ] Create a demonstration video
- [ ] Prepare for HACS publication