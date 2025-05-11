"""BLE Triangulation configuration panel."""
import logging
import voluptuous as vol

from homeassistant.components.config import SECTIONS
from homeassistant.components.config.custom_panel import async_register_panel
from homeassistant.const import (
    CONF_NAME,
    CONF_LATITUDE,
    CONF_LONGITUDE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    CONF_PROXIES,
    CONF_PROXY_ID,
    PROXY_CONFIG_DIR,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BLE Triangulation configuration panel."""
    # Register custom panel
    async def get_panel_html():
        """Create panel html."""
        # You would typically use template rendering here for a full app
        # This is a simple example to demonstrate the functionality
        return """
        <style>
            ble-proxy-manager {
                display: block;
                max-width: 600px;
                margin: 0 auto;
                padding: 16px;
            }
            .proxy-card {
                margin-bottom: 16px;
                padding: 16px;
                border-radius: 4px;
                background: var(--card-background-color);
                box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0, 0, 0, 0.14));
            }
            .proxy-form {
                margin-top: 24px;
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
        </style>

        <ble-proxy-manager>
            <h1>BLE Triangulation - Proxy Configuration</h1>
            
            <div class="map-wrapper">
                <ha-map id="proxyMap"></ha-map>
            </div>
            
            <div id="proxyList">
                <!-- Proxy cards will be rendered here -->
                <div class="empty-state" id="emptyState">
                    <p>No proxies configured yet. Add your first proxy below.</p>
                </div>
            </div>
            
            <div class="proxy-form">
                <h2>Add New Proxy</h2>
                <div class="form-row">
                    <div class="form-group">
                        <label for="proxyId">Proxy ID</label>
                        <input type="text" id="proxyId" placeholder="e.g., kitchen_proxy">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="latitude">Latitude</label>
                        <input type="number" id="latitude" step="0.0000001">
                    </div>
                    <div class="form-group">
                        <label for="longitude">Longitude</label>
                        <input type="number" id="longitude" step="0.0000001">
                    </div>
                </div>
                <div class="actions">
                    <button id="addProxyBtn">Add Proxy</button>
                </div>
            </div>
        </ble-proxy-manager>

        <script>
            class BLEProxyManager extends HTMLElement {
                constructor() {
                    super();
                    this._proxies = [];
                }
                
                connectedCallback() {
                    this._initMap();
                    this._fetchProxies();
                    this._setupEventListeners();
                }
                
                async _fetchProxies() {
                    try {
                        const response = await fetch('/api/ble_triangulation/proxies');
                        if (response.ok) {
                            this._proxies = await response.json();
                            this._renderProxies();
                            this._updateMap();
                        }
                    } catch (error) {
                        console.error('Error fetching proxies:', error);
                    }
                }
                
                _initMap() {
                    // Initialize the map
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
                    }
                }
                
                _updateMap() {
                    const mapElement = this.querySelector('#proxyMap');
                    if (!mapElement || this._proxies.length === 0) return;
                    
                    // Create proxy entities for the map
                    const entities = this._proxies.map(proxy => ({
                        entity_id: `proxy.${proxy.id}`,
                        attributes: {
                            friendly_name: proxy.id,
                            latitude: proxy.latitude,
                            longitude: proxy.longitude,
                            icon: 'mdi:wifi'
                        },
                        state: 'home'
                    }));
                    
                    mapElement.entities = entities;
                }
                
                _renderProxies() {
                    const proxyList = this.querySelector('#proxyList');
                    const emptyState = this.querySelector('#emptyState');
                    
                    if (this._proxies.length === 0) {
                        emptyState.style.display = 'block';
                        proxyList.innerHTML = '';
                        return;
                    }
                    
                    emptyState.style.display = 'none';
                    
                    // Create proxy cards
                    const proxyCards = this._proxies.map(proxy => `
                        <div class="proxy-card" data-id="${proxy.id}">
                            <h3>${proxy.id}</h3>
                            <p>Location: ${proxy.latitude.toFixed(6)}, ${proxy.longitude.toFixed(6)}</p>
                            <div class="actions">
                                <button class="delete-btn" data-id="${proxy.id}">Delete</button>
                            </div>
                        </div>
                    `).join('');
                    
                    proxyList.innerHTML = proxyCards;
                    
                    // Add event listeners to delete buttons
                    this.querySelectorAll('.delete-btn').forEach(btn => {
                        btn.addEventListener('click', this._handleDeleteProxy.bind(this));
                    });
                }
                
                _setupEventListeners() {
                    const addBtn = this.querySelector('#addProxyBtn');
                    addBtn.addEventListener('click', this._handleAddProxy.bind(this));
                }
                
                async _handleAddProxy() {
                    const proxyId = this.querySelector('#proxyId').value.trim();
                    const latitude = parseFloat(this.querySelector('#latitude').value);
                    const longitude = parseFloat(this.querySelector('#longitude').value);
                    
                    if (!proxyId || isNaN(latitude) || isNaN(longitude)) {
                        alert('Please fill in all fields with valid values.');
                        return;
                    }
                    
                    try {
                        const response = await fetch('/api/ble_triangulation/proxies', {
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
                            // Clear form
                            this.querySelector('#proxyId').value = '';
                            this.querySelector('#latitude').value = '';
                            this.querySelector('#longitude').value = '';
                            
                            // Refresh proxies
                            await this._fetchProxies();
                        } else {
                            alert('Error adding proxy. Please try again.');
                        }
                    } catch (error) {
                        console.error('Error adding proxy:', error);
                        alert('Error adding proxy. Please try again.');
                    }
                }
                
                async _handleDeleteProxy(event) {
                    const proxyId = event.target.dataset.id;
                    
                    if (confirm(`Are you sure you want to delete the proxy '${proxyId}'?`)) {
                        try {
                            const response = await fetch(`/api/ble_triangulation/proxies/${proxyId}`, {
                                method: 'DELETE'
                            });
                            
                            if (response.ok) {
                                // Refresh proxies
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
            }
            
            customElements.define('ble-proxy-manager', BLEProxyManager);
        </script>
        """

    try:
        # Register configuration panel
        await async_register_panel(
            hass,
            "ble-triangulation",
            "BLE Triangulation",
            "mdi:bluetooth",
            get_panel_html,
        )
        
        # Register API handlers
        hass.http.register_view(ProxyListView(hass, config_entry))
        hass.http.register_view(ProxyView(hass, config_entry))
        
        return True
    except Exception as e:
        _LOGGER.error(f"Error setting up BLE Triangulation panel: {e}")
        return False


class ProxyListView:
    """API View for listing and creating proxies."""

    url = "/api/ble_triangulation/proxies"
    name = "api:ble_triangulation:proxies"

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
            
        return self.json(proxies_data)

    async def post(self, request):
        """Handle POST request."""
        data = await request.json()
        
        proxy_id = data.get("id")
        latitude = data.get(CONF_LATITUDE)
        longitude = data.get(CONF_LONGITUDE)
        
        if not proxy_id or latitude is None or longitude is None:
            return self.json_message("Invalid proxy data", status_code=400)
            
        try:
            await self.manager.add_proxy(proxy_id, latitude, longitude)
            return self.json({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error adding proxy: {e}")
            return self.json_message(f"Error adding proxy: {str(e)}", status_code=500)


class ProxyView:
    """API View for individual proxy operations."""

    url = "/api/ble_triangulation/proxies/{proxy_id}"
    name = "api:ble_triangulation:proxy"

    def __init__(self, hass, config_entry):
        """Initialize."""
        self.hass = hass
        self.config_entry = config_entry
        self.manager = hass.data[DOMAIN][config_entry.entry_id]["manager"]

    async def delete(self, request, proxy_id):
        """Handle DELETE request."""
        try:
            await self.manager.remove_proxy(proxy_id)
            return self.json({"success": True})
        except Exception as e:
            _LOGGER.error(f"Error removing proxy: {e}")
            return self.json_message(f"Error removing proxy: {str(e)}", status_code=500)