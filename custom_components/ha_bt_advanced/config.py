"""HA-BT-Advanced configuration panel."""
import logging
import voluptuous as vol
import json
from aiohttp import web

from homeassistant.components.config import SECTIONS
from homeassistant.components.config.custom_panel import async_register_panel
from homeassistant.const import (
    CONF_NAME,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_ICON,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.http import HomeAssistantView

from .const import (
    DOMAIN,
    CONF_PROXIES,
    CONF_PROXY_ID,
    CONF_BEACONS,
    CONF_MAC_ADDRESS,
    CONF_BEACON_ICON,
    CONF_BEACON_CATEGORY,
    CONF_ZONE_ID,
    CONF_ZONE_NAME,
    CONF_ZONE_TYPE,
    CONF_ZONE_COORDINATES,
    CONF_WIFI_SSID,
    CONF_WIFI_PASSWORD,
    CONF_MQTT_HOST,
    CONF_MQTT_USERNAME,
    CONF_MQTT_PASSWORD,
    CONF_FALLBACK_PASSWORD,
)
from . import esphome_wizard

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HA-BT-Advanced configuration panel."""
    # Register custom panel
    async def get_panel_html():
        """Create panel html."""
        return """
        <style>
            ha-bt-advanced-panel {
                display: block;
                max-width: 1200px;
                margin: 0 auto;
                padding: 16px;
            }
            .tab-container {
                margin-top: 8px;
            }
            .card {
                margin-bottom: 16px;
                padding: 16px;
                border-radius: 4px;
                background: var(--card-background-color);
                box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0, 0, 0, 0.14));
            }
            .form-row {
                display: flex;
                gap: 16px;
                margin-bottom: 16px;
            }
            .form-group {
                flex: 1;
            }
            label {
                display: block;
                margin-bottom: 4px;
                color: var(--primary-text-color);
            }
            input {
                width: 100%;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid var(--divider-color);
                background: var(--card-background-color);
                color: var(--primary-text-color);
            }
            select {
                width: 100%;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid var(--divider-color);
                background: var(--card-background-color);
                color: var(--primary-text-color);
            }
            button {
                background: var(--primary-color);
                color: var(--text-primary-color);
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                cursor: pointer;
                font-weight: 500;
            }
            .actions {
                display: flex;
                justify-content: flex-end;
                gap: 8px;
            }
            .delete-btn {
                background: var(--error-color);
            }
            .property-btn {
                background: var(--secondary-text-color);
            }
            h2 {
                font-size: 1.5rem;
                margin-bottom: 16px;
            }
            .empty-state {
                text-align: center;
                padding: 32px;
                color: var(--secondary-text-color);
            }
            .map-wrapper {
                height: 400px;
                margin-bottom: 24px;
                border-radius: 4px;
                overflow: hidden;
            }
            .zone-polygon {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 16px;
            }
            .zone-point {
                display: flex;
                gap: 8px;
                margin-bottom: 8px;
            }
            .beacon-list, .proxy-list, .zone-list {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 16px;
                margin-bottom: 16px;
            }
            .beacon-card, .proxy-card, .zone-card {
                padding: 16px;
                border-radius: 4px;
                background: var(--card-background-color);
                box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0, 0, 0, 0.14));
            }
            .tab-button {
                background: none;
                border: none;
                padding: 8px 16px;
                margin-right: 8px;
                border-radius: 4px 4px 0 0;
                cursor: pointer;
                color: var(--primary-text-color);
            }
            .tab-button.active {
                background: var(--primary-color);
                color: var(--text-primary-color);
            }
            .tab-content {
                display: none;
                padding: 16px;
                border-radius: 0 4px 4px 4px;
                background: var(--card-background-color);
                box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0, 0, 0, 0.14));
            }
            .tab-content.active {
                display: block;
            }
            .esphome-form {
                margin-top: 20px;
                padding: 16px;
                background: var(--card-background-color);
                border-radius: 4px;
                box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0, 0, 0, 0.14));
            }
        </style>

        <ha-bt-advanced-panel>
            <h1>HA-BT-Advanced Configuration</h1>
            
            <div class="tabs">
                <button class="tab-button active" data-tab="proxies">Proxies</button>
                <button class="tab-button" data-tab="beacons">Beacons</button>
                <button class="tab-button" data-tab="zones">Zones</button>
                <button class="tab-button" data-tab="esphome">ESPHome Config</button>
            </div>
            
            <div class="tab-container">
                <!-- Proxies Tab -->
                <div class="tab-content active" id="proxies-tab">
                    <div class="map-wrapper">
                        <ha-map id="proxyMap"></ha-map>
                    </div>
                    
                    <h2>Proxies</h2>
                    <div id="proxyList" class="proxy-list">
                        <!-- Proxy cards will be rendered here -->
                        <div class="empty-state" id="proxyEmptyState">
                            <p>No proxies configured yet. Add your first proxy below or click on the map.</p>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Add/Edit Proxy</h2>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="proxyId">Proxy ID</label>
                                <input type="text" id="proxyId" placeholder="e.g., kitchen_proxy">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="proxyLatitude">Latitude</label>
                                <input type="number" id="proxyLatitude" step="0.0000001">
                            </div>
                            <div class="form-group">
                                <label for="proxyLongitude">Longitude</label>
                                <input type="number" id="proxyLongitude" step="0.0000001">
                            </div>
                        </div>
                        <div class="actions">
                            <button id="clearProxyFormBtn">Clear</button>
                            <button id="addProxyBtn">Add Proxy</button>
                        </div>
                    </div>
                </div>
                
                <!-- Beacons Tab -->
                <div class="tab-content" id="beacons-tab">
                    <h2>Beacons</h2>
                    <div id="beaconList" class="beacon-list">
                        <!-- Beacon cards will be rendered here -->
                        <div class="empty-state" id="beaconEmptyState">
                            <p>No beacons configured yet. Add your first beacon below or wait for automatic discovery.</p>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Add/Edit Beacon</h2>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="beaconMac">MAC Address</label>
                                <input type="text" id="beaconMac" placeholder="e.g., C7:9B:6A:32:BB:0E">
                            </div>
                            <div class="form-group">
                                <label for="beaconName">Friendly Name</label>
                                <input type="text" id="beaconName" placeholder="e.g., John's Keys">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="beaconCategory">Category</label>
                                <select id="beaconCategory">
                                    <option value="person">Person</option>
                                    <option value="item">Item</option>
                                    <option value="pet">Pet</option>
                                    <option value="vehicle">Vehicle</option>
                                    <option value="other">Other</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="beaconIcon">Icon</label>
                                <input type="text" id="beaconIcon" placeholder="e.g., mdi:key">
                            </div>
                        </div>
                        <div class="actions">
                            <button id="clearBeaconFormBtn">Clear</button>
                            <button id="addBeaconBtn">Add Beacon</button>
                        </div>
                    </div>
                </div>
                
                <!-- Zones Tab -->
                <div class="tab-content" id="zones-tab">
                    <div class="map-wrapper">
                        <ha-map id="zoneMap"></ha-map>
                    </div>
                    
                    <h2>Zones</h2>
                    <div id="zoneList" class="zone-list">
                        <!-- Zone cards will be rendered here -->
                        <div class="empty-state" id="zoneEmptyState">
                            <p>No zones configured yet. Add your first zone below.</p>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Add/Edit Zone</h2>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="zoneId">Zone ID</label>
                                <input type="text" id="zoneId" placeholder="e.g., living_room">
                            </div>
                            <div class="form-group">
                                <label for="zoneName">Zone Name</label>
                                <input type="text" id="zoneName" placeholder="e.g., Living Room">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="zoneType">Zone Type</label>
                                <select id="zoneType">
                                    <option value="room">Room</option>
                                    <option value="home">Home</option>
                                    <option value="work">Work</option>
                                    <option value="custom">Custom</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="zoneIcon">Icon</label>
                                <input type="text" id="zoneIcon" placeholder="e.g., mdi:sofa">
                            </div>
                        </div>
                        <h3>Zone Polygon</h3>
                        <p>Click on the map to add points to the zone polygon. At least 3 points are required.</p>
                        <div id="zoneCoordinates" class="zone-polygon">
                            <!-- Zone points will be rendered here -->
                        </div>
                        <div class="actions">
                            <button id="clearZoneFormBtn">Clear</button>
                            <button id="addZoneBtn">Add Zone</button>
                        </div>
                    </div>
                </div>
                
                <!-- ESPHome Config Tab -->
                <div class="tab-content" id="esphome-tab">
                    <h2>Generate ESPHome Configuration</h2>
                    <p>
                        Generate ESPHome configuration files for your ESP32 devices to use as BLE proxies.
                        Select a proxy and enter your WiFi and MQTT credentials to generate a configuration.
                    </p>
                    
                    <div class="card">
                        <h3>Select Proxy</h3>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="configProxyId">Proxy</label>
                                <select id="configProxyId">
                                    <option value="">Select a proxy...</option>
                                    <!-- Proxy options will be rendered here -->
                                </select>
                            </div>
                        </div>
                        
                        <h3>WiFi Configuration</h3>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="wifiSsid">WiFi SSID</label>
                                <input type="text" id="wifiSsid" placeholder="Your WiFi network name">
                            </div>
                            <div class="form-group">
                                <label for="wifiPassword">WiFi Password</label>
                                <input type="password" id="wifiPassword" placeholder="Your WiFi password">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="fallbackPassword">Fallback AP Password</label>
                                <input type="password" id="fallbackPassword" placeholder="Password for fallback hotspot">
                            </div>
                        </div>
                        
                        <h3>MQTT Configuration</h3>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="mqttHost">MQTT Broker</label>
                                <input type="text" id="mqttHost" placeholder="IP address or hostname">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="mqttUsername">MQTT Username</label>
                                <input type="text" id="mqttUsername" placeholder="MQTT username">
                            </div>
                            <div class="form-group">
                                <label for="mqttPassword">MQTT Password</label>
                                <input type="password" id="mqttPassword" placeholder="MQTT password">
                            </div>
                        </div>
                        
                        <div class="actions">
                            <button id="generateConfigBtn">Generate & Download Config</button>
                        </div>
                    </div>
                </div>
            </div>
        </ha-bt-advanced-panel>

        <script>
            class HABTAdvancedPanel extends HTMLElement {
                constructor() {
                    super();
                    this._proxies = [];
                    this._beacons = [];
                    this._zones = [];
                    this._zonePoints = [];
                    this._editMode = {
                        proxy: false,
                        beacon: false,
                        zone: false
                    };
                    this._editId = {
                        proxy: null,
                        beacon: null,
                        zone: null
                    };
                }
                
                connectedCallback() {
                    this._setupTabs();
                    this._initProxyMap();
                    this._initZoneMap();
                    this._fetchProxies();
                    this._fetchBeacons();
                    this._fetchZones();
                    this._setupEventListeners();
                }
                
                _setupTabs() {
                    const tabButtons = this.querySelectorAll('.tab-button');
                    const tabContents = this.querySelectorAll('.tab-content');
                    
                    tabButtons.forEach(button => {
                        button.addEventListener('click', () => {
                            // Remove active class from all buttons and contents
                            tabButtons.forEach(btn => btn.classList.remove('active'));
                            tabContents.forEach(content => content.classList.remove('active'));
                            
                            // Add active class to clicked button and corresponding content
                            button.classList.add('active');
                            const tabId = button.dataset.tab + '-tab';
                            this.querySelector(`#${tabId}`).classList.add('active');
                            
                            // Refresh maps when tab is activated
                            if (tabId === 'proxies-tab') {
                                this._updateProxyMap();
                            } else if (tabId === 'zones-tab') {
                                this._updateZoneMap();
                            } else if (tabId === 'esphome-tab') {
                                this._updateProxyOptions();
                            }
                        });
                    });
                }
                
                async _fetchProxies() {
                    try {
                        const response = await fetch('/api/ha_bt_advanced/proxies');
                        if (response.ok) {
                            this._proxies = await response.json();
                            this._renderProxies();
                            this._updateProxyMap();
                            this._updateProxyOptions();
                        }
                    } catch (error) {
                        console.error('Error fetching proxies:', error);
                    }
                }
                
                async _fetchBeacons() {
                    try {
                        const response = await fetch('/api/ha_bt_advanced/beacons');
                        if (response.ok) {
                            this._beacons = await response.json();
                            this._renderBeacons();
                        }
                    } catch (error) {
                        console.error('Error fetching beacons:', error);
                    }
                }
                
                async _fetchZones() {
                    try {
                        const response = await fetch('/api/ha_bt_advanced/zones');
                        if (response.ok) {
                            this._zones = await response.json();
                            this._renderZones();
                            this._updateZoneMap();
                        }
                    } catch (error) {
                        console.error('Error fetching zones:', error);
                    }
                }
                
                _initProxyMap() {
                    const mapElement = this.querySelector('#proxyMap');
                    if (mapElement && window.hass) {
                        mapElement.hass = window.hass;
                        
                        // Center map on home coordinates
                        if (window.hass.config && window.hass.config.latitude && window.hass.config.longitude) {
                            mapElement.latitude = window.hass.config.latitude;
                            mapElement.longitude = window.hass.config.longitude;
                            mapElement.zoom = 15;
                        }
                        
                        // Add click handler to add new proxies
                        mapElement.addEventListener('click', (event) => {
                            if (event.detail && event.detail.latitude && event.detail.longitude) {
                                this.querySelector('#proxyLatitude').value = event.detail.latitude.toFixed(7);
                                this.querySelector('#proxyLongitude').value = event.detail.longitude.toFixed(7);
                            }
                        });
                    }
                }
                
                _initZoneMap() {
                    const mapElement = this.querySelector('#zoneMap');
                    if (mapElement && window.hass) {
                        mapElement.hass = window.hass;
                        
                        // Center map on home coordinates
                        if (window.hass.config && window.hass.config.latitude && window.hass.config.longitude) {
                            mapElement.latitude = window.hass.config.latitude;
                            mapElement.longitude = window.hass.config.longitude;
                            mapElement.zoom = 15;
                        }
                        
                        // Add click handler to add points to zone polygon
                        mapElement.addEventListener('click', (event) => {
                            if (event.detail && event.detail.latitude && event.detail.longitude) {
                                this._addZonePoint(event.detail.latitude, event.detail.longitude);
                            }
                        });
                    }
                }
                
                _updateProxyMap() {
                    const mapElement = this.querySelector('#proxyMap');
                    if (!mapElement || this._proxies.length === 0) return;
                    
                    // Create proxy entities for the map
                    const entities = this._proxies.map(proxy => ({
                        entity_id: `proxy.${proxy.id}`,
                        attributes: {
                            friendly_name: proxy.id,
                            latitude: proxy.latitude,
                            longitude: proxy.longitude,
                            icon: 'mdi:wifi',
                        },
                        state: 'home'
                    }));
                    
                    mapElement.entities = entities;
                }
                
                _updateZoneMap() {
                    const mapElement = this.querySelector('#zoneMap');
                    if (!mapElement) return;
                    
                    // Create entities for the map
                    const entities = [];
                    
                    // Add zones as polygons
                    this._zones.forEach(zone => {
                        if (zone.coordinates && zone.coordinates.length >= 3) {
                            entities.push({
                                entity_id: `zone.${zone.id}`,
                                attributes: {
                                    friendly_name: zone.name,
                                    latitude: zone.coordinates[0][0],
                                    longitude: zone.coordinates[0][1],
                                    icon: zone.icon || 'mdi:map-marker',
                                    polygon: zone.coordinates.map(coord => [coord[0], coord[1]]),
                                },
                                state: 'on'
                            });
                        }
                    });
                    
                    // Add current zone points if in edit mode
                    if (this._zonePoints.length > 0) {
                        entities.push({
                            entity_id: 'zone.new',
                            attributes: {
                                friendly_name: 'New Zone',
                                latitude: this._zonePoints[0][0],
                                longitude: this._zonePoints[0][1],
                                icon: 'mdi:map-marker-plus',
                                polygon: this._zonePoints.map(coord => [coord[0], coord[1]]),
                            },
                            state: 'on'
                        });
                        
                        // Add points as markers
                        this._zonePoints.forEach((point, index) => {
                            entities.push({
                                entity_id: `point.${index}`,
                                attributes: {
                                    friendly_name: `Point ${index + 1}`,
                                    latitude: point[0],
                                    longitude: point[1],
                                    icon: 'mdi:map-marker',
                                },
                                state: 'on'
                            });
                        });
                    }
                    
                    mapElement.entities = entities;
                }
                
                _addZonePoint(lat, lng) {
                    this._zonePoints.push([lat, lng]);
                    this._renderZonePoints();
                    this._updateZoneMap();
                }
                
                _renderZonePoints() {
                    const container = this.querySelector('#zoneCoordinates');
                    container.innerHTML = '';
                    
                    if (this._zonePoints.length === 0) {
                        container.innerHTML = '<p>No points added yet. Click on the map to add points.</p>';
                        return;
                    }
                    
                    this._zonePoints.forEach((point, index) => {
                        const pointEl = document.createElement('div');
                        pointEl.className = 'zone-point';
                        pointEl.innerHTML = `
                            <span>Point ${index + 1}: ${point[0].toFixed(6)}, ${point[1].toFixed(6)}</span>
                            <button class="delete-btn" data-index="${index}">Remove</button>
                        `;
                        container.appendChild(pointEl);
                        
                        // Add event listener to delete button
                        pointEl.querySelector('.delete-btn').addEventListener('click', (event) => {
                            const index = parseInt(event.target.dataset.index);
                            this._zonePoints.splice(index, 1);
                            this._renderZonePoints();
                            this._updateZoneMap();
                        });
                    });
                }
                
                _renderProxies() {
                    const proxyList = this.querySelector('#proxyList');
                    const emptyState = this.querySelector('#proxyEmptyState');
                    
                    if (this._proxies.length === 0) {
                        emptyState.style.display = 'block';
                        proxyList.innerHTML = '';
                        return;
                    }
                    
                    emptyState.style.display = 'none';
                    proxyList.innerHTML = '';
                    
                    // Create proxy cards
                    this._proxies.forEach(proxy => {
                        const card = document.createElement('div');
                        card.className = 'proxy-card';
                        card.dataset.id = proxy.id;
                        card.innerHTML = `
                            <h3>${proxy.id}</h3>
                            <p>Location: ${proxy.latitude.toFixed(6)}, ${proxy.longitude.toFixed(6)}</p>
                            <div class="actions">
                                <button class="property-btn edit-proxy-btn" data-id="${proxy.id}">Edit</button>
                                <button class="property-btn generate-config-btn" data-id="${proxy.id}">Config</button>
                                <button class="delete-btn delete-proxy-btn" data-id="${proxy.id}">Delete</button>
                            </div>
                        `;
                        proxyList.appendChild(card);
                    });
                    
                    // Add event listeners
                    this.querySelectorAll('.edit-proxy-btn').forEach(btn => {
                        btn.addEventListener('click', (event) => {
                            this._handleEditProxy(event.target.dataset.id);
                        });
                    });
                    
                    this.querySelectorAll('.generate-config-btn').forEach(btn => {
                        btn.addEventListener('click', (event) => {
                            // Switch to ESPHome tab and select this proxy
                            this.querySelector('.tab-button[data-tab="esphome"]').click();
                            this.querySelector('#configProxyId').value = event.target.dataset.id;
                        });
                    });
                    
                    this.querySelectorAll('.delete-proxy-btn').forEach(btn => {
                        btn.addEventListener('click', (event) => {
                            this._handleDeleteProxy(event.target.dataset.id);
                        });
                    });
                }
                
                _renderBeacons() {
                    const beaconList = this.querySelector('#beaconList');
                    const emptyState = this.querySelector('#beaconEmptyState');
                    
                    if (this._beacons.length === 0) {
                        emptyState.style.display = 'block';
                        beaconList.innerHTML = '';
                        return;
                    }
                    
                    emptyState.style.display = 'none';
                    beaconList.innerHTML = '';
                    
                    // Create beacon cards
                    this._beacons.forEach(beacon => {
                        const card = document.createElement('div');
                        card.className = 'beacon-card';
                        card.dataset.mac = beacon.mac;
                        card.innerHTML = `
                            <h3>${beacon.name}</h3>
                            <p>MAC: ${beacon.mac}</p>
                            <p>Category: ${beacon.category || 'Unknown'}</p>
                            <p>Icon: ${beacon.icon || 'Default'}</p>
                            <div class="actions">
                                <button class="property-btn edit-beacon-btn" data-mac="${beacon.mac}">Edit</button>
                                <button class="delete-btn delete-beacon-btn" data-mac="${beacon.mac}">Delete</button>
                            </div>
                        `;
                        beaconList.appendChild(card);
                    });
                    
                    // Add event listeners
                    this.querySelectorAll('.edit-beacon-btn').forEach(btn => {
                        btn.addEventListener('click', (event) => {
                            this._handleEditBeacon(event.target.dataset.mac);
                        });
                    });
                    
                    this.querySelectorAll('.delete-beacon-btn').forEach(btn => {
                        btn.addEventListener('click', (event) => {
                            this._handleDeleteBeacon(event.target.dataset.mac);
                        });
                    });
                }
                
                _renderZones() {
                    const zoneList = this.querySelector('#zoneList');
                    const emptyState = this.querySelector('#zoneEmptyState');
                    
                    if (this._zones.length === 0) {
                        emptyState.style.display = 'block';
                        zoneList.innerHTML = '';
                        return;
                    }
                    
                    emptyState.style.display = 'none';
                    zoneList.innerHTML = '';
                    
                    // Create zone cards
                    this._zones.forEach(zone => {
                        const card = document.createElement('div');
                        card.className = 'zone-card';
                        card.dataset.id = zone.id;
                        card.innerHTML = `
                            <h3>${zone.name}</h3>
                            <p>Type: ${zone.type}</p>
                            <p>Points: ${zone.coordinates ? zone.coordinates.length : 0}</p>
                            <div class="actions">
                                <button class="property-btn edit-zone-btn" data-id="${zone.id}">Edit</button>
                                <button class="delete-btn delete-zone-btn" data-id="${zone.id}">Delete</button>
                            </div>
                        `;
                        zoneList.appendChild(card);
                    });
                    
                    // Add event listeners
                    this.querySelectorAll('.edit-zone-btn').forEach(btn => {
                        btn.addEventListener('click', (event) => {
                            this._handleEditZone(event.target.dataset.id);
                        });
                    });
                    
                    this.querySelectorAll('.delete-zone-btn').forEach(btn => {
                        btn.addEventListener('click', (event) => {
                            this._handleDeleteZone(event.target.dataset.id);
                        });
                    });
                }
                
                _updateProxyOptions() {
                    const select = this.querySelector('#configProxyId');
                    if (!select) return;
                    
                    // Clear existing options except the first one
                    while (select.options.length > 1) {
                        select.remove(1);
                    }
                    
                    // Add proxy options
                    this._proxies.forEach(proxy => {
                        const option = document.createElement('option');
                        option.value = proxy.id;
                        option.textContent = proxy.id;
                        select.appendChild(option);
                    });
                }
                
                _setupEventListeners() {
                    // Proxy events
                    this.querySelector('#addProxyBtn').addEventListener('click', this._handleAddProxy.bind(this));
                    this.querySelector('#clearProxyFormBtn').addEventListener('click', this._clearProxyForm.bind(this));
                    
                    // Beacon events
                    this.querySelector('#addBeaconBtn').addEventListener('click', this._handleAddBeacon.bind(this));
                    this.querySelector('#clearBeaconFormBtn').addEventListener('click', this._clearBeaconForm.bind(this));
                    
                    // Zone events
                    this.querySelector('#addZoneBtn').addEventListener('click', this._handleAddZone.bind(this));
                    this.querySelector('#clearZoneFormBtn').addEventListener('click', this._clearZoneForm.bind(this));
                    
                    // ESPHome config events
                    this.querySelector('#generateConfigBtn').addEventListener('click', this._handleGenerateConfig.bind(this));
                }
                
                _clearProxyForm() {
                    this.querySelector('#proxyId').value = '';
                    this.querySelector('#proxyLatitude').value = '';
                    this.querySelector('#proxyLongitude').value = '';
                    this._editMode.proxy = false;
                    this._editId.proxy = null;
                    this.querySelector('#addProxyBtn').textContent = 'Add Proxy';
                }
                
                _clearBeaconForm() {
                    this.querySelector('#beaconMac').value = '';
                    this.querySelector('#beaconName').value = '';
                    this.querySelector('#beaconCategory').value = 'item';
                    this.querySelector('#beaconIcon').value = '';
                    this._editMode.beacon = false;
                    this._editId.beacon = null;
                    this.querySelector('#addBeaconBtn').textContent = 'Add Beacon';
                }
                
                _clearZoneForm() {
                    this.querySelector('#zoneId').value = '';
                    this.querySelector('#zoneName').value = '';
                    this.querySelector('#zoneType').value = 'room';
                    this.querySelector('#zoneIcon').value = '';
                    this._zonePoints = [];
                    this._renderZonePoints();
                    this._updateZoneMap();
                    this._editMode.zone = false;
                    this._editId.zone = null;
                    this.querySelector('#addZoneBtn').textContent = 'Add Zone';
                }
                
                async _handleAddProxy() {
                    const proxyId = this.querySelector('#proxyId').value.trim();
                    const latitude = parseFloat(this.querySelector('#proxyLatitude').value);
                    const longitude = parseFloat(this.querySelector('#proxyLongitude').value);
                    
                    if (!proxyId || isNaN(latitude) || isNaN(longitude)) {
                        alert('Please fill in all fields with valid values.');
                        return;
                    }
                    
                    // Check if we're editing an existing proxy
                    if (this._editMode.proxy && this._editId.proxy) {
                        try {
                            const response = await fetch(`/api/ha_bt_advanced/proxies/${this._editId.proxy}`, {
                                method: 'PUT',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                    id: proxyId,
                                    latitude,
                                    longitude
                                })
                            });
                            
                            if (response.ok) {
                                this._clearProxyForm();
                                await this._fetchProxies();
                            } else {
                                alert('Error updating proxy. Please try again.');
                            }
                        } catch (error) {
                            console.error('Error updating proxy:', error);
                            alert('Error updating proxy. Please try again.');
                        }
                    } else {
                        // Adding a new proxy
                        try {
                            const response = await fetch('/api/ha_bt_advanced/proxies', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                    id: proxyId,
                                    latitude,
                                    longitude
                                })
                            });
                            
                            if (response.ok) {
                                this._clearProxyForm();
                                await this._fetchProxies();
                            } else {
                                alert('Error adding proxy. Please try again.');
                            }
                        } catch (error) {
                            console.error('Error adding proxy:', error);
                            alert('Error adding proxy. Please try again.');
                        }
                    }
                }
                
                async _handleAddBeacon() {
                    const mac = this.querySelector('#beaconMac').value.trim();
                    const name = this.querySelector('#beaconName').value.trim();
                    const category = this.querySelector('#beaconCategory').value;
                    const icon = this.querySelector('#beaconIcon').value.trim();
                    
                    if (!mac || !name) {
                        alert('Please fill in all required fields.');
                        return;
                    }
                    
                    // Check if we're editing an existing beacon
                    if (this._editMode.beacon && this._editId.beacon) {
                        try {
                            const response = await fetch(`/api/ha_bt_advanced/beacons/${this._editId.beacon}`, {
                                method: 'PUT',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                    mac,
                                    name,
                                    category,
                                    icon: icon || undefined
                                })
                            });
                            
                            if (response.ok) {
                                this._clearBeaconForm();
                                await this._fetchBeacons();
                            } else {
                                alert('Error updating beacon. Please try again.');
                            }
                        } catch (error) {
                            console.error('Error updating beacon:', error);
                            alert('Error updating beacon. Please try again.');
                        }
                    } else {
                        // Adding a new beacon
                        try {
                            const response = await fetch('/api/ha_bt_advanced/beacons', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                    mac,
                                    name,
                                    category,
                                    icon: icon || undefined
                                })
                            });
                            
                            if (response.ok) {
                                this._clearBeaconForm();
                                await this._fetchBeacons();
                            } else {
                                alert('Error adding beacon. Please try again.');
                            }
                        } catch (error) {
                            console.error('Error adding beacon:', error);
                            alert('Error adding beacon. Please try again.');
                        }
                    }
                }
                
                async _handleAddZone() {
                    const zoneId = this.querySelector('#zoneId').value.trim();
                    const zoneName = this.querySelector('#zoneName').value.trim();
                    const zoneType = this.querySelector('#zoneType').value;
                    const zoneIcon = this.querySelector('#zoneIcon').value.trim();
                    
                    if (!zoneId || !zoneName || this._zonePoints.length < 3) {
                        alert('Please fill in all required fields and add at least 3 points to the zone.');
                        return;
                    }
                    
                    // Check if we're editing an existing zone
                    if (this._editMode.zone && this._editId.zone) {
                        try {
                            const response = await fetch(`/api/ha_bt_advanced/zones/${this._editId.zone}`, {
                                method: 'PUT',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                    id: zoneId,
                                    name: zoneName,
                                    type: zoneType,
                                    coordinates: this._zonePoints,
                                    icon: zoneIcon || undefined
                                })
                            });
                            
                            if (response.ok) {
                                this._clearZoneForm();
                                await this._fetchZones();
                            } else {
                                alert('Error updating zone. Please try again.');
                            }
                        } catch (error) {
                            console.error('Error updating zone:', error);
                            alert('Error updating zone. Please try again.');
                        }
                    } else {
                        // Adding a new zone
                        try {
                            const response = await fetch('/api/ha_bt_advanced/zones', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                    id: zoneId,
                                    name: zoneName,
                                    type: zoneType,
                                    coordinates: this._zonePoints,
                                    icon: zoneIcon || undefined
                                })
                            });
                            
                            if (response.ok) {
                                this._clearZoneForm();
                                await this._fetchZones();
                            } else {
                                alert('Error adding zone. Please try again.');
                            }
                        } catch (error) {
                            console.error('Error adding zone:', error);
                            alert('Error adding zone. Please try again.');
                        }
                    }
                }
                
                async _handleGenerateConfig() {
                    const proxyId = this.querySelector('#configProxyId').value;
                    const wifiSsid = this.querySelector('#wifiSsid').value.trim();
                    const wifiPassword = this.querySelector('#wifiPassword').value;
                    const fallbackPassword = this.querySelector('#fallbackPassword').value;
                    const mqttHost = this.querySelector('#mqttHost').value.trim();
                    const mqttUsername = this.querySelector('#mqttUsername').value.trim();
                    const mqttPassword = this.querySelector('#mqttPassword').value;
                    
                    if (!proxyId || !wifiSsid || !wifiPassword || !fallbackPassword || !mqttHost) {
                        alert('Please fill in all required fields.');
                        return;
                    }
                    
                    try {
                        // Call the API to generate the configuration
                        const response = await fetch('/api/ha_bt_advanced/esphome_config', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                proxy_id: proxyId,
                                wifi_ssid: wifiSsid,
                                wifi_password: wifiPassword,
                                fallback_password: fallbackPassword,
                                mqtt_host: mqttHost,
                                mqtt_username: mqttUsername,
                                mqtt_password: mqttPassword
                            })
                        });
                        
                        if (response.ok) {
                            // Get the configuration content
                            const config = await response.text();
                            
                            // Create a blob and download link
                            const blob = new Blob([config], { type: 'text/yaml' });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `${proxyId}.yaml`;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            URL.revokeObjectURL(url);
                        } else {
                            alert('Error generating configuration. Please try again.');
                        }
                    } catch (error) {
                        console.error('Error generating configuration:', error);
                        alert('Error generating configuration. Please try again.');
                    }
                }
                
                async _handleEditProxy(proxyId) {
                    const proxy = this._proxies.find(p => p.id === proxyId);
                    if (proxy) {
                        this.querySelector('#proxyId').value = proxy.id;
                        this.querySelector('#proxyLatitude').value = proxy.latitude;
                        this.querySelector('#proxyLongitude').value = proxy.longitude;
                        this._editMode.proxy = true;
                        this._editId.proxy = proxyId;
                        this.querySelector('#addProxyBtn').textContent = 'Update Proxy';
                    }
                }
                
                async _handleEditBeacon(mac) {
                    const beacon = this._beacons.find(b => b.mac === mac);
                    if (beacon) {
                        this.querySelector('#beaconMac').value = beacon.mac;
                        this.querySelector('#beaconName').value = beacon.name;
                        this.querySelector('#beaconCategory').value = beacon.category || 'item';
                        this.querySelector('#beaconIcon').value = beacon.icon || '';
                        this._editMode.beacon = true;
                        this._editId.beacon = mac;
                        this.querySelector('#addBeaconBtn').textContent = 'Update Beacon';
                    }
                }
                
                async _handleEditZone(zoneId) {
                    const zone = this._zones.find(z => z.id === zoneId);
                    if (zone) {
                        this.querySelector('#zoneId').value = zone.id;
                        this.querySelector('#zoneName').value = zone.name;
                        this.querySelector('#zoneType').value = zone.type;
                        this.querySelector('#zoneIcon').value = zone.icon || '';
                        this._zonePoints = [...zone.coordinates];
                        this._renderZonePoints();
                        this._editMode.zone = true;
                        this._editId.zone = zoneId;
                        this.querySelector('#addZoneBtn').textContent = 'Update Zone';
                        this._updateZoneMap();
                    }
                }
                
                async _handleDeleteProxy(proxyId) {
                    if (confirm(`Are you sure you want to delete the proxy '${proxyId}'?`)) {
                        try {
                            const response = await fetch(`/api/ha_bt_advanced/proxies/${proxyId}`, {
                                method: 'DELETE'
                            });
                            
                            if (response.ok) {
                                await this._fetchProxies();
                            } else {
                                alert('Error deleting proxy. Please try again.');
                            }
                        } catch (error) {
                            console.error('Error deleting proxy:', error);
                            alert('Error deleting proxy. Please try again.');
                        }
                    }
                }
                
                async _handleDeleteBeacon(mac) {
                    if (confirm(`Are you sure you want to delete the beacon '${mac}'?`)) {
                        try {
                            const response = await fetch(`/api/ha_bt_advanced/beacons/${mac}`, {
                                method: 'DELETE'
                            });
                            
                            if (response.ok) {
                                await this._fetchBeacons();
                            } else {
                                alert('Error deleting beacon. Please try again.');
                            }
                        } catch (error) {
                            console.error('Error deleting beacon:', error);
                            alert('Error deleting beacon. Please try again.');
                        }
                    }
                }
                
                async _handleDeleteZone(zoneId) {
                    if (confirm(`Are you sure you want to delete the zone '${zoneId}'?`)) {
                        try {
                            const response = await fetch(`/api/ha_bt_advanced/zones/${zoneId}`, {
                                method: 'DELETE'
                            });
                            
                            if (response.ok) {
                                await this._fetchZones();
                            } else {
                                alert('Error deleting zone. Please try again.');
                            }
                        } catch (error) {
                            console.error('Error deleting zone:', error);
                            alert('Error deleting zone. Please try again.');
                        }
                    }
                }
            }
            
            customElements.define('ha-bt-advanced-panel', HABTAdvancedPanel);
        </script>
        """

    try:
        # Register configuration panel
        await async_register_panel(
            hass,
            "ha_bt_advanced",
            "HA-BT-Advanced",
            "mdi:bluetooth",
            get_panel_html,
        )
        
        # Register API handlers
        hass.http.register_view(ProxyListView(hass, config_entry))
        hass.http.register_view(ProxyView(hass, config_entry))
        hass.http.register_view(BeaconListView(hass, config_entry))
        hass.http.register_view(BeaconView(hass, config_entry))
        hass.http.register_view(ZoneListView(hass, config_entry))
        hass.http.register_view(ZoneView(hass, config_entry))
        hass.http.register_view(ESPHomeConfigView(hass, config_entry))
        
        return True
    except Exception as e:
        _LOGGER.error(f"Error setting up HA-BT-Advanced panel: {e}")
        return False


class ProxyListView(HomeAssistantView):
    """API View for listing and creating proxies."""

    url = "/api/ha_bt_advanced/proxies"
    name = "api:ha_bt_advanced:proxies"

    def __init__(self, hass, config_entry):
        """Initialize."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id]["manager"]

    async def get(self, request):
        """Handle GET request."""
        proxies_data = []
        
        for proxy_id, proxy_info in self.manager.proxies.items():
            proxies_data.append({
                "id": proxy_id,
                "latitude": proxy_info.get(CONF_LATITUDE, 0),
                "longitude": proxy_info.get(CONF_LONGITUDE, 0),
            })
            
        return web.json_response(proxies_data)

    async def post(self, request):
        """Handle POST request."""
        data = await request.json()
        
        proxy_id = data.get("id")
        latitude = data.get(CONF_LATITUDE)
        longitude = data.get(CONF_LONGITUDE)
        
        if not proxy_id or latitude is None or longitude is None:
            return web.json_response({"error": "Invalid proxy data"}, status=400)
            
        try:
            await self.manager.add_proxy(proxy_id, latitude, longitude)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error adding proxy: {e}")
            return web.json_response({"error": str(e)}, status=500)


class ProxyView(HomeAssistantView):
    """API View for individual proxy operations."""

    url = "/api/ha_bt_advanced/proxies/{proxy_id}"
    name = "api:ha_bt_advanced:proxy"

    def __init__(self, hass, config_entry):
        """Initialize."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id]["manager"]

    async def get(self, request, proxy_id):
        """Handle GET request."""
        proxy_info = self.manager.proxies.get(proxy_id)
        if not proxy_info:
            return web.json_response({"error": "Proxy not found"}, status=404)
            
        return web.json_response({
            "id": proxy_id,
            "latitude": proxy_info.get(CONF_LATITUDE, 0),
            "longitude": proxy_info.get(CONF_LONGITUDE, 0),
        })

    async def put(self, request, proxy_id):
        """Handle PUT request."""
        data = await request.json()
        
        new_proxy_id = data.get("id", proxy_id)
        latitude = data.get(CONF_LATITUDE)
        longitude = data.get(CONF_LONGITUDE)
        
        if latitude is None or longitude is None:
            return web.json_response({"error": "Invalid proxy data"}, status=400)
            
        try:
            # If ID has changed, remove the old one
            if new_proxy_id != proxy_id:
                await self.manager.remove_proxy(proxy_id)
                
            # Add with new ID and data
            await self.manager.add_proxy(new_proxy_id, latitude, longitude)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error updating proxy: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def delete(self, request, proxy_id):
        """Handle DELETE request."""
        try:
            await self.manager.remove_proxy(proxy_id)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error removing proxy: {e}")
            return web.json_response({"error": str(e)}, status=500)


class BeaconListView(HomeAssistantView):
    """API View for listing and creating beacons."""

    url = "/api/ha_bt_advanced/beacons"
    name = "api:ha_bt_advanced:beacons"

    def __init__(self, hass, config_entry):
        """Initialize."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id]["manager"]

    async def get(self, request):
        """Handle GET request."""
        beacons_data = []
        
        for mac, beacon_info in self.manager.beacons.items():
            beacons_data.append({
                "mac": mac,
                "name": beacon_info.get(CONF_NAME, f"Beacon {mac}"),
                "category": beacon_info.get(CONF_BEACON_CATEGORY),
                "icon": beacon_info.get(CONF_BEACON_ICON),
            })
            
        return web.json_response(beacons_data)

    async def post(self, request):
        """Handle POST request."""
        data = await request.json()
        
        mac = data.get(CONF_MAC_ADDRESS)
        name = data.get(CONF_NAME)
        category = data.get(CONF_BEACON_CATEGORY)
        icon = data.get(CONF_BEACON_ICON)
        
        if not mac or not name:
            return web.json_response({"error": "Invalid beacon data"}, status=400)
            
        try:
            await self.manager.add_beacon(mac, name, category, icon)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error adding beacon: {e}")
            return web.json_response({"error": str(e)}, status=500)


class BeaconView(HomeAssistantView):
    """API View for individual beacon operations."""

    url = "/api/ha_bt_advanced/beacons/{mac}"
    name = "api:ha_bt_advanced:beacon"

    def __init__(self, hass, config_entry):
        """Initialize."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id]["manager"]

    async def get(self, request, mac):
        """Handle GET request."""
        beacon_info = self.manager.beacons.get(mac)
        if not beacon_info:
            return web.json_response({"error": "Beacon not found"}, status=404)
            
        return web.json_response({
            "mac": mac,
            "name": beacon_info.get(CONF_NAME, f"Beacon {mac}"),
            "category": beacon_info.get(CONF_BEACON_CATEGORY),
            "icon": beacon_info.get(CONF_BEACON_ICON),
        })

    async def put(self, request, mac):
        """Handle PUT request."""
        data = await request.json()
        
        new_mac = data.get(CONF_MAC_ADDRESS, mac)
        name = data.get(CONF_NAME)
        category = data.get(CONF_BEACON_CATEGORY)
        icon = data.get(CONF_BEACON_ICON)
        
        if not name:
            return web.json_response({"error": "Invalid beacon data"}, status=400)
            
        try:
            # If MAC has changed, remove the old one
            if new_mac != mac:
                await self.manager.remove_beacon(mac)
                
            # Add with new MAC and data
            await self.manager.add_beacon(new_mac, name, category, icon)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error updating beacon: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def delete(self, request, mac):
        """Handle DELETE request."""
        try:
            await self.manager.remove_beacon(mac)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error removing beacon: {e}")
            return web.json_response({"error": str(e)}, status=500)


class ZoneListView(HomeAssistantView):
    """API View for listing and creating zones."""

    url = "/api/ha_bt_advanced/zones"
    name = "api:ha_bt_advanced:zones"

    def __init__(self, hass, config_entry):
        """Initialize."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id]["manager"]

    async def get(self, request):
        """Handle GET request."""
        zones_data = []
        
        for zone in self.manager.zone_manager.get_all_zones():
            zones_data.append({
                "id": zone.zone_id,
                "name": zone.name,
                "type": zone.zone_type,
                "coordinates": zone.coordinates,
                "icon": zone.icon,
            })
            
        return web.json_response(zones_data)

    async def post(self, request):
        """Handle POST request."""
        data = await request.json()
        
        zone_id = data.get(CONF_ZONE_ID)
        name = data.get(CONF_ZONE_NAME)
        zone_type = data.get(CONF_ZONE_TYPE)
        coordinates = data.get(CONF_ZONE_COORDINATES)
        icon = data.get(CONF_ICON)
        
        if not zone_id or not name or not zone_type or not coordinates or len(coordinates) < 3:
            return web.json_response({"error": "Invalid zone data"}, status=400)
            
        try:
            await self.manager.zone_manager.add_zone(zone_id, name, zone_type, coordinates, icon)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error adding zone: {e}")
            return web.json_response({"error": str(e)}, status=500)


class ZoneView(HomeAssistantView):
    """API View for individual zone operations."""

    url = "/api/ha_bt_advanced/zones/{zone_id}"
    name = "api:ha_bt_advanced:zone"

    def __init__(self, hass, config_entry):
        """Initialize."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id]["manager"]

    async def get(self, request, zone_id):
        """Handle GET request."""
        zone = self.manager.zone_manager.get_zone_by_id(zone_id)
        if not zone:
            return web.json_response({"error": "Zone not found"}, status=404)
            
        return web.json_response({
            "id": zone.zone_id,
            "name": zone.name,
            "type": zone.zone_type,
            "coordinates": zone.coordinates,
            "icon": zone.icon,
        })

    async def put(self, request, zone_id):
        """Handle PUT request."""
        data = await request.json()
        
        new_zone_id = data.get(CONF_ZONE_ID, zone_id)
        name = data.get(CONF_ZONE_NAME)
        zone_type = data.get(CONF_ZONE_TYPE)
        coordinates = data.get(CONF_ZONE_COORDINATES)
        icon = data.get(CONF_ICON)
        
        if not name or not zone_type or not coordinates or len(coordinates) < 3:
            return web.json_response({"error": "Invalid zone data"}, status=400)
            
        try:
            # If ID has changed, remove the old one
            if new_zone_id != zone_id:
                await self.manager.zone_manager.remove_zone(zone_id)
                
            # Add with new ID and data
            await self.manager.zone_manager.add_zone(new_zone_id, name, zone_type, coordinates, icon)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error updating zone: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def delete(self, request, zone_id):
        """Handle DELETE request."""
        try:
            await self.manager.zone_manager.remove_zone(zone_id)
            return web.json_response({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error removing zone: {e}")
            return web.json_response({"error": str(e)}, status=500)


class ESPHomeConfigView(HomeAssistantView):
    """API View for generating ESPHome configuration."""

    url = "/api/ha_bt_advanced/esphome_config"
    name = "api:ha_bt_advanced:esphome_config"

    def __init__(self, hass, config_entry):
        """Initialize."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id]["manager"]

    async def post(self, request):
        """Handle POST request."""
        data = await request.json()
        
        proxy_id = data.get(CONF_PROXY_ID)
        wifi_ssid = data.get(CONF_WIFI_SSID)
        wifi_password = data.get(CONF_WIFI_PASSWORD)
        fallback_password = data.get(CONF_FALLBACK_PASSWORD)
        mqtt_host = data.get(CONF_MQTT_HOST)
        mqtt_username = data.get(CONF_MQTT_USERNAME, "")
        mqtt_password = data.get(CONF_MQTT_PASSWORD, "")
        
        if not proxy_id or not wifi_ssid or not wifi_password or not fallback_password or not mqtt_host:
            return web.json_response({"error": "Missing required fields"}, status=400)
            
        try:
            # Generate ESPHome configuration
            mqtt_config = {
                "broker": mqtt_host,
                "username": mqtt_username,
                "password": mqtt_password,
            }
            
            config = esphome_wizard.generate_esphome_config(
                proxy_id=proxy_id,
                mqtt_config=mqtt_config,
                mqtt_topic_prefix=self.manager.mqtt_topic_prefix
            )
            
            # Create secrets.yaml content
            secrets_content = f"""
# WiFi credentials
wifi_ssid: {wifi_ssid}
wifi_password: {wifi_password}
fallback_ap_password: {fallback_password}
"""

            # Combine the configuration with a comment about the secrets file
            complete_config = f"""# This configuration requires a secrets.yaml file with the following content:
{secrets_content}
# Save the above to a file named secrets.yaml in the same directory as this file

{config}
"""
            
            return web.Response(text=complete_config, content_type="text/yaml")
        except Exception as e:
            _LOGGER.error(f"Error generating ESPHome configuration: {e}")
            return web.json_response({"error": str(e)}, status=500)