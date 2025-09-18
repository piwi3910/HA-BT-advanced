class HABTAdvancedPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._hass = null;
    this.proxies = [];
    this.beacons = [];
    this.zones = [];
    this.selectedTool = 'view';
    this.drawingZone = false;
    this.zonePoints = [];
    this.map = null;
    this.markers = {};
    this.zonePolygons = {};
    this.discoveryMode = false;
    this.discoveryEndTime = null;
    this.discoveredBeacons = [];
    this.selectedBeaconsToOnboard = new Set();
    this.users = [];
    this.virtualUsers = [];
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.shadowRoot.innerHTML) {
      this.render();
      // Wait for Leaflet to load before setting up the map
      this.waitForLeaflet().then(() => {
        this.setupMap();
        this.loadData();
      });
    }
  }

  async waitForLeaflet() {
    // If Leaflet is already loaded, return immediately
    if (window.L) {
      // Also inject Leaflet CSS into shadow DOM
      this.injectLeafletStyles();
      return;
    }

    // Wait for Leaflet to be loaded
    return new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (window.L) {
          clearInterval(checkInterval);
          // Inject Leaflet CSS into shadow DOM
          this.injectLeafletStyles();
          resolve();
        }
      }, 100);

      // Timeout after 10 seconds
      setTimeout(() => {
        clearInterval(checkInterval);
        console.error('Leaflet failed to load');
        resolve(); // Resolve anyway to prevent hanging
      }, 10000);
    });
  }

  injectLeafletStyles() {
    // Inject Leaflet CSS directly into shadow DOM
    const leafletCSS = document.createElement('link');
    leafletCSS.rel = 'stylesheet';
    leafletCSS.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
    this.shadowRoot.appendChild(leafletCSS);
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          height: 100vh;
          font-family: var(--paper-font-body1_-_font-family);
        }
        .container {
          display: flex;
          height: 100%;
        }
        .sidebar {
          width: 350px;
          background: var(--card-background-color, #fff);
          border-right: 1px solid var(--divider-color, #e0e0e0);
          overflow-y: auto;
          padding: 16px;
        }
        .map-container {
          flex: 1;
          position: relative;
        }
        #map {
          width: 100%;
          height: 100%;
        }
        .toolbar {
          position: absolute;
          top: 10px;
          right: 10px;
          z-index: 1000;
          background: white;
          border-radius: 8px;
          padding: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .tool-button {
          padding: 8px 16px;
          margin: 4px;
          border: 1px solid #ccc;
          border-radius: 4px;
          background: white;
          cursor: pointer;
          transition: all 0.3s;
        }
        .tool-button:hover {
          background: #f0f0f0;
        }
        .tool-button.active {
          background: #2196F3;
          color: white;
        }
        .section {
          margin-bottom: 24px;
        }
        .section-title {
          font-size: 18px;
          font-weight: 500;
          margin-bottom: 12px;
          color: var(--primary-text-color);
        }
        .item-card {
          background: var(--ha-card-background);
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 8px;
          border: 1px solid var(--divider-color);
        }
        .item-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        .item-name {
          font-weight: 500;
          color: var(--primary-text-color);
        }
        .item-status {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
        }
        .status-online {
          background: #4CAF50;
          color: white;
        }
        .status-offline {
          background: #f44336;
          color: white;
        }
        .item-details {
          font-size: 14px;
          color: var(--secondary-text-color);
        }
        .add-button {
          width: 100%;
          padding: 12px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
          margin-top: 8px;
        }
        .add-button:hover {
          opacity: 0.9;
        }
        .delete-button {
          padding: 4px 8px;
          background: #f44336;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
        }
        .modal {
          display: none;
          position: fixed;
          z-index: 2000;
          left: 0;
          top: 0;
          width: 100%;
          height: 100%;
          background-color: rgba(0,0,0,0.4);
        }
        .modal-content {
          background-color: var(--card-background-color);
          margin: 15% auto;
          padding: 20px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          width: 400px;
        }
        .modal-title {
          font-size: 20px;
          font-weight: 500;
          margin-bottom: 16px;
          color: var(--primary-text-color);
        }
        .form-group {
          margin-bottom: 16px;
        }
        .form-label {
          display: block;
          margin-bottom: 4px;
          font-size: 14px;
          color: var(--primary-text-color);
        }
        .form-input, .form-select {
          width: 100%;
          padding: 8px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          font-size: 14px;
        }
        .modal-buttons {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
          margin-top: 20px;
        }
        .modal-button {
          padding: 8px 16px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
        }
        .modal-cancel {
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
        }
        .modal-save {
          background: var(--primary-color);
          color: white;
        }
        .instructions {
          background: #FFF3E0;
          border: 1px solid #FFB74D;
          border-radius: 4px;
          padding: 12px;
          margin-bottom: 16px;
        }
        .instructions-title {
          font-weight: 500;
          margin-bottom: 4px;
        }
        .discovery-section {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 16px;
          border-radius: 8px;
          margin-bottom: 24px;
        }
        .discovery-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .discovery-title {
          font-size: 20px;
          font-weight: 600;
        }
        .discovery-button {
          padding: 10px 20px;
          border: none;
          border-radius: 6px;
          background: white;
          color: #667eea;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
        }
        .discovery-button:hover {
          transform: scale(1.05);
          box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .discovery-button.active {
          background: #ff6b6b;
          color: white;
        }
        .discovery-countdown {
          font-size: 24px;
          font-weight: bold;
          text-align: center;
          margin: 16px 0;
        }
        .discovered-list {
          max-height: 300px;
          overflow-y: auto;
          background: white;
          border-radius: 8px;
          padding: 8px;
          color: #333;
        }
        .discovered-beacon {
          display: flex;
          align-items: center;
          padding: 12px;
          margin: 4px 0;
          background: #f8f9fa;
          border-radius: 6px;
          border: 2px solid transparent;
          transition: all 0.3s;
        }
        .discovered-beacon:hover {
          border-color: #667eea;
          background: #f0f4ff;
        }
        .discovered-beacon.selected {
          background: #e8f4ff;
          border-color: #2196F3;
        }
        .beacon-checkbox {
          margin-right: 12px;
          width: 20px;
          height: 20px;
        }
        .beacon-info {
          flex: 1;
        }
        .beacon-mac {
          font-family: monospace;
          font-weight: 600;
        }
        .beacon-type {
          display: inline-block;
          padding: 2px 8px;
          background: #667eea;
          color: white;
          border-radius: 4px;
          font-size: 12px;
          margin-left: 8px;
        }
        .signal-strength {
          display: flex;
          align-items: center;
          margin-top: 4px;
        }
        .signal-bars {
          display: flex;
          gap: 2px;
          margin-right: 8px;
        }
        .signal-bar {
          width: 4px;
          height: 16px;
          background: #ddd;
          border-radius: 2px;
        }
        .signal-bar.active {
          background: #4CAF50;
        }
        .beacon-stats {
          display: flex;
          gap: 16px;
          margin-top: 4px;
          font-size: 12px;
          color: #666;
        }
        .onboard-buttons {
          display: flex;
          gap: 8px;
          margin-top: 16px;
        }
        .onboard-button {
          flex: 1;
          padding: 10px;
          border: none;
          border-radius: 6px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
        }
        .onboard-single {
          background: #2196F3;
          color: white;
        }
        .onboard-selected {
          background: #4CAF50;
          color: white;
        }
        .onboard-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .onboard-button:disabled {
          background: #ccc;
          cursor: not-allowed;
          transform: none;
        }
        .user-select {
          margin-bottom: 12px;
        }
        .user-select label {
          display: block;
          margin-bottom: 4px;
          font-weight: 500;
        }
        .user-select select {
          width: 100%;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
        }
        .create-virtual-user {
          display: flex;
          gap: 8px;
          margin-top: 8px;
        }
        .create-virtual-user input {
          flex: 1;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
        }
        .create-virtual-user button {
          padding: 8px 16px;
          background: #667eea;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }
      </style>

      <div class="container">
        <div class="sidebar">
          <!-- Discovery Section -->
          <div class="discovery-section">
            <div class="discovery-header">
              <div class="discovery-title">🔍 Beacon Discovery</div>
              <button class="discovery-button" id="discovery-toggle">Start Discovery</button>
            </div>
            <div id="discovery-content" style="display: none;">
              <div class="discovery-countdown" id="discovery-countdown"></div>
              <div class="discovered-list" id="discovered-list"></div>
              <div class="onboard-buttons" id="onboard-buttons" style="display: none;">
                <button class="onboard-button onboard-selected" id="onboard-selected-btn" disabled>
                  Onboard Selected (0)
                </button>
              </div>
            </div>
          </div>

          <div class="section">
            <div class="section-title">Proxies</div>
            <div id="proxy-list"></div>
            <button class="add-button" id="add-proxy-btn">Add Proxy</button>
          </div>

          <div class="section">
            <div class="section-title">Onboarded Beacons</div>
            <div id="beacon-list"></div>
          </div>

          <div class="section">
            <div class="section-title">Zones</div>
            <div id="zone-list"></div>
            <button class="add-button" id="add-zone-btn">Draw Zone on Map</button>
          </div>
        </div>

        <div class="map-container">
          <div class="toolbar">
            <button class="tool-button active" data-tool="view">
              <ha-icon icon="mdi:cursor-default"></ha-icon> View
            </button>
            <button class="tool-button" data-tool="add-proxy">
              <ha-icon icon="mdi:wifi"></ha-icon> Add Proxy
            </button>
            <button class="tool-button" data-tool="draw-zone">
              <ha-icon icon="mdi:vector-polygon"></ha-icon> Draw Zone
            </button>
          </div>
          <div id="map"></div>
        </div>
      </div>

      <!-- Add Proxy Modal -->
      <div id="proxy-modal" class="modal">
        <div class="modal-content">
          <div class="modal-title">Add Proxy</div>
          <div class="form-group">
            <label class="form-label">Proxy ID</label>
            <input type="text" id="proxy-id" class="form-input" placeholder="e.g., living_room_proxy">
          </div>
          <div class="form-group">
            <label class="form-label">Latitude</label>
            <input type="number" id="proxy-lat" class="form-input" step="0.000001">
          </div>
          <div class="form-group">
            <label class="form-label">Longitude</label>
            <input type="number" id="proxy-lng" class="form-input" step="0.000001">
          </div>
          <div class="modal-buttons">
            <button class="modal-button modal-cancel" id="proxy-cancel">Cancel</button>
            <button class="modal-button modal-save" id="proxy-save">Save</button>
          </div>
        </div>
      </div>

      <!-- Onboard Beacon Modal -->
      <div id="onboard-modal" class="modal">
        <div class="modal-content" style="min-width: 500px;">
          <div class="modal-title">Onboard Beacon</div>
          <div id="onboard-beacon-info" style="background: #f0f4ff; padding: 12px; border-radius: 6px; margin-bottom: 16px;">
            <!-- Beacon info will be displayed here -->
          </div>
          <div class="form-group">
            <label class="form-label">Name *</label>
            <input type="text" id="onboard-name" class="form-input" placeholder="e.g., John's Keys" required>
          </div>
          <div class="form-group">
            <label class="form-label">Owner</label>
            <select id="onboard-owner" class="form-select">
              <option value="">No Owner</option>
            </select>
            <div class="create-virtual-user">
              <input type="text" id="virtual-user-name" placeholder="New guest name...">
              <button id="create-virtual-btn">Create Guest</button>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Category</label>
            <select id="onboard-category" class="form-select">
              <option value="item">Item</option>
              <option value="person">Person</option>
              <option value="pet">Pet</option>
              <option value="vehicle">Vehicle</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Icon</label>
            <input type="text" id="onboard-icon" class="form-input" placeholder="mdi:key">
          </div>
          <div class="form-group">
            <label class="form-label">
              <input type="checkbox" id="onboard-notifications" checked> Enable Notifications
            </label>
          </div>
          <div class="form-group">
            <label class="form-label">Tracking Precision</label>
            <select id="onboard-precision" class="form-select">
              <option value="low">Low - Less accurate, saves battery</option>
              <option value="medium" selected>Medium - Balanced</option>
              <option value="high">High - Most accurate</option>
            </select>
          </div>
          <div class="modal-buttons">
            <button class="modal-button modal-cancel" id="onboard-cancel">Cancel</button>
            <button class="modal-button modal-save" id="onboard-save">Onboard Beacon</button>
          </div>
        </div>
      </div>

      <!-- Bulk Onboard Modal -->
      <div id="bulk-onboard-modal" class="modal">
        <div class="modal-content" style="min-width: 600px;">
          <div class="modal-title">Onboard Multiple Beacons</div>
          <div style="background: #f0f4ff; padding: 12px; border-radius: 6px; margin-bottom: 16px;">
            <strong>Selected Beacons:</strong> <span id="bulk-count">0</span>
          </div>
          <div id="bulk-beacon-list" style="max-height: 200px; overflow-y: auto; margin-bottom: 16px;">
            <!-- Selected beacons will be listed here -->
          </div>
          <div class="form-group">
            <label class="form-label">Default Owner</label>
            <select id="bulk-owner" class="form-select">
              <option value="">No Owner</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Default Category</label>
            <select id="bulk-category" class="form-select">
              <option value="item">Item</option>
              <option value="person">Person</option>
              <option value="pet">Pet</option>
              <option value="vehicle">Vehicle</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">
              <input type="checkbox" id="bulk-notifications" checked> Enable Notifications for All
            </label>
          </div>
          <div class="form-group">
            <label class="form-label">Names for Each Beacon:</label>
            <div id="bulk-names">
              <!-- Individual name inputs will be generated here -->
            </div>
          </div>
          <div class="modal-buttons">
            <button class="modal-button modal-cancel" id="bulk-cancel">Cancel</button>
            <button class="modal-button modal-save" id="bulk-save">Onboard All</button>
          </div>
        </div>
      </div>

      <!-- Zone Name Modal -->
      <div id="zone-modal" class="modal">
        <div class="modal-content">
          <div class="modal-title">Name Your Zone</div>
          <div class="form-group">
            <label class="form-label">Zone ID</label>
            <input type="text" id="zone-id" class="form-input" placeholder="e.g., living_room">
          </div>
          <div class="form-group">
            <label class="form-label">Name</label>
            <input type="text" id="zone-name" class="form-input" placeholder="e.g., Living Room">
          </div>
          <div class="form-group">
            <label class="form-label">Type</label>
            <select id="zone-type" class="form-select">
              <option value="room">Room</option>
              <option value="home">Home</option>
              <option value="work">Work</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Icon</label>
            <input type="text" id="zone-icon" class="form-input" placeholder="mdi:sofa">
          </div>
          <div class="modal-buttons">
            <button class="modal-button modal-cancel" id="zone-cancel">Cancel</button>
            <button class="modal-button modal-save" id="zone-save">Save</button>
          </div>
        </div>
      </div>
    `;

    this.setupEventListeners();
  }

  setupMap() {
    // Initialize Leaflet map
    const mapElement = this.shadowRoot.getElementById('map');

    // Check if map element exists
    if (!mapElement) {
      console.error('Map element not found');
      return;
    }

    // Get Home Assistant's home location
    const homeLocation = [
      this._hass.config.latitude || 37.7749,
      this._hass.config.longitude || -122.4194
    ];

    try {
      // Create map
      this.map = L.map(mapElement).setView(homeLocation, 18);

      // Add OpenStreetMap tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }).addTo(this.map);

      // Force map to recalculate its size (fixes tiling issues)
      setTimeout(() => {
        this.map.invalidateSize();
      }, 100);

      // Add resize observer to handle container size changes
      const resizeObserver = new ResizeObserver(() => {
        if (this.map) {
          this.map.invalidateSize();
        }
      });
      resizeObserver.observe(mapElement);

    // Add home marker
    L.marker(homeLocation, {
      icon: L.icon({
        iconUrl: 'data:image/svg+xml;base64,' + btoa(`
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
            <path fill="#2196F3" d="M10,20V14H14V20H19V12H22L12,3L2,12H5V20H10Z"/>
          </svg>
        `),
        iconSize: [24, 24],
        iconAnchor: [12, 24]
      })
    }).addTo(this.map).bindPopup('Home');

      // Handle map clicks
      this.map.on('click', (e) => {
        if (this.selectedTool === 'add-proxy') {
          this.showProxyModal(e.latlng.lat, e.latlng.lng);
        } else if (this.selectedTool === 'draw-zone') {
          this.addZonePoint(e.latlng);
        }
      });
    } catch (error) {
      console.error('Error initializing map:', error);
    }
  }

  setupEventListeners() {
    // Tool buttons
    this.shadowRoot.querySelectorAll('.tool-button').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.selectTool(e.target.closest('.tool-button').dataset.tool);
      });
    });

    // Discovery button
    const discoveryToggle = this.shadowRoot.getElementById('discovery-toggle');
    if (discoveryToggle) {
      discoveryToggle.addEventListener('click', () => {
        if (this.discoveryMode) {
          this.stopDiscovery();
        } else {
          this.startDiscovery();
        }
      });
    }

    // Onboard selected button
    const onboardSelectedBtn = this.shadowRoot.getElementById('onboard-selected-btn');
    if (onboardSelectedBtn) {
      onboardSelectedBtn.addEventListener('click', () => {
        this.showBulkOnboardModal();
      });
    }

    // Add buttons
    this.shadowRoot.getElementById('add-proxy-btn').addEventListener('click', () => {
      this.showProxyModal();
    });

    this.shadowRoot.getElementById('add-zone-btn').addEventListener('click', () => {
      this.selectTool('draw-zone');
    });

    // Modal handlers
    this.setupModalHandlers();
  }

  setupModalHandlers() {
    // Proxy modal
    const proxyModal = this.shadowRoot.getElementById('proxy-modal');
    this.shadowRoot.getElementById('proxy-cancel').addEventListener('click', () => {
      proxyModal.style.display = 'none';
    });
    this.shadowRoot.getElementById('proxy-save').addEventListener('click', () => {
      this.saveProxy();
    });

    // Beacon modal
    const beaconModal = this.shadowRoot.getElementById('beacon-modal');
    this.shadowRoot.getElementById('beacon-cancel').addEventListener('click', () => {
      beaconModal.style.display = 'none';
    });
    this.shadowRoot.getElementById('beacon-save').addEventListener('click', () => {
      this.saveBeacon();
    });

    // Zone modal
    const zoneModal = this.shadowRoot.getElementById('zone-modal');
    this.shadowRoot.getElementById('zone-cancel').addEventListener('click', () => {
      zoneModal.style.display = 'none';
      this.clearZoneDrawing();
    });
    this.shadowRoot.getElementById('zone-save').addEventListener('click', () => {
      this.saveZone();
    });
  }

  selectTool(tool) {
    this.selectedTool = tool;

    // Update button states
    this.shadowRoot.querySelectorAll('.tool-button').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tool === tool);
    });

    // Show instructions for zone drawing
    if (tool === 'draw-zone') {
      this.startZoneDrawing();
    } else {
      this.clearZoneDrawing();
    }
  }

  startZoneDrawing() {
    this.drawingZone = true;
    this.zonePoints = [];

    // Change cursor
    this.map.getContainer().style.cursor = 'crosshair';

    // Show instructions
    const instructions = L.control({position: 'topright'});
    instructions.onAdd = () => {
      const div = L.DomUtil.create('div', 'zone-instructions');
      div.style.background = 'white';
      div.style.padding = '10px';
      div.style.borderRadius = '4px';
      div.innerHTML = '<b>Click to add zone points</b><br>Press ESC to cancel';
      return div;
    };
    instructions.addTo(this.map);
    this.zoneInstructions = instructions;
  }

  clearZoneDrawing() {
    this.drawingZone = false;
    this.zonePoints = [];

    // Reset cursor
    if (this.map) {
      this.map.getContainer().style.cursor = '';
    }

    // Remove instructions
    if (this.zoneInstructions) {
      this.zoneInstructions.remove();
      this.zoneInstructions = null;
    }

    // Remove temporary polygon
    if (this.tempZonePolygon) {
      this.tempZonePolygon.remove();
      this.tempZonePolygon = null;
    }
  }

  addZonePoint(latlng) {
    this.zonePoints.push([latlng.lat, latlng.lng]);

    // Update temporary polygon
    if (this.tempZonePolygon) {
      this.tempZonePolygon.setLatLngs(this.zonePoints);
    } else if (this.zonePoints.length >= 3) {
      this.tempZonePolygon = L.polygon(this.zonePoints, {
        color: '#2196F3',
        fillOpacity: 0.3
      }).addTo(this.map);
    }

    // If we have at least 3 points, offer to complete
    if (this.zonePoints.length >= 3) {
      // Add a marker for the first point to indicate closing
      const firstPoint = this.zonePoints[0];
      const distance = this.getDistance(latlng, {lat: firstPoint[0], lng: firstPoint[1]});

      // If click is near the first point, complete the zone
      if (distance < 20) { // 20 meters threshold
        this.completeZone();
      }
    }
  }

  completeZone() {
    if (this.zonePoints.length < 3) return;

    // Show zone naming modal
    this.shadowRoot.getElementById('zone-modal').style.display = 'block';
  }

  getDistance(latlng1, latlng2) {
    // Calculate distance in meters between two points
    const R = 6371000; // Earth's radius in meters
    const dLat = (latlng2.lat - latlng1.lat) * Math.PI / 180;
    const dLon = (latlng2.lng - latlng1.lng) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(latlng1.lat * Math.PI / 180) * Math.cos(latlng2.lat * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  }

  showProxyModal(lat = null, lng = null) {
    const modal = this.shadowRoot.getElementById('proxy-modal');
    modal.style.display = 'block';

    if (lat && lng) {
      this.shadowRoot.getElementById('proxy-lat').value = lat.toFixed(6);
      this.shadowRoot.getElementById('proxy-lng').value = lng.toFixed(6);
    }
  }

  showBeaconModal() {
    const modal = this.shadowRoot.getElementById('beacon-modal');
    modal.style.display = 'block';
  }

  async saveProxy() {
    const proxyId = this.shadowRoot.getElementById('proxy-id').value;
    const lat = parseFloat(this.shadowRoot.getElementById('proxy-lat').value);
    const lng = parseFloat(this.shadowRoot.getElementById('proxy-lng').value);

    if (!proxyId || !lat || !lng) {
      alert('Please fill in all fields');
      return;
    }

    try {
      await this._hass.callService('ha_bt_advanced', 'add_proxy', {
        proxy_id: proxyId,
        latitude: lat,
        longitude: lng
      });

      // Hide modal
      this.shadowRoot.getElementById('proxy-modal').style.display = 'none';

      // Clear form
      this.shadowRoot.getElementById('proxy-id').value = '';
      this.shadowRoot.getElementById('proxy-lat').value = '';
      this.shadowRoot.getElementById('proxy-lng').value = '';

      // Reload data
      this.loadData();
    } catch (error) {
      alert('Failed to add proxy: ' + error.message);
    }
  }

  async saveBeacon() {
    const mac = this.shadowRoot.getElementById('beacon-mac').value;
    const name = this.shadowRoot.getElementById('beacon-name').value;
    const category = this.shadowRoot.getElementById('beacon-category').value;
    const icon = this.shadowRoot.getElementById('beacon-icon').value;

    if (!mac || !name) {
      alert('MAC Address and Name are required');
      return;
    }

    try {
      await this._hass.callService('ha_bt_advanced', 'add_beacon', {
        mac_address: mac,
        name: name,
        category: category,
        icon: icon || undefined
      });

      // Hide modal
      this.shadowRoot.getElementById('beacon-modal').style.display = 'none';

      // Clear form
      this.shadowRoot.getElementById('beacon-mac').value = '';
      this.shadowRoot.getElementById('beacon-name').value = '';
      this.shadowRoot.getElementById('beacon-icon').value = '';

      // Reload data
      this.loadData();
    } catch (error) {
      alert('Failed to add beacon: ' + error.message);
    }
  }

  async saveZone() {
    const zoneId = this.shadowRoot.getElementById('zone-id').value;
    const name = this.shadowRoot.getElementById('zone-name').value;
    const type = this.shadowRoot.getElementById('zone-type').value;
    const icon = this.shadowRoot.getElementById('zone-icon').value;

    if (!zoneId || !name) {
      alert('Zone ID and Name are required');
      return;
    }

    try {
      await this._hass.callService('ha_bt_advanced', 'add_zone', {
        zone_id: zoneId,
        name: name,
        type: type,
        coordinates: JSON.stringify(this.zonePoints),
        icon: icon || undefined
      });

      // Hide modal
      this.shadowRoot.getElementById('zone-modal').style.display = 'none';

      // Clear form and drawing
      this.shadowRoot.getElementById('zone-id').value = '';
      this.shadowRoot.getElementById('zone-name').value = '';
      this.shadowRoot.getElementById('zone-icon').value = '';
      this.clearZoneDrawing();

      // Reset tool
      this.selectTool('view');

      // Reload data
      this.loadData();
    } catch (error) {
      alert('Failed to add zone: ' + error.message);
    }
  }

  async loadData() {
    // Load proxies
    await this.loadProxies();

    // Load beacons
    await this.loadBeacons();

    // Load zones
    await this.loadZones();

    // Load users
    await this.loadUsers();
  }

  async loadUsers() {
    try {
      // Get all HA users and virtual users
      const result = await this._hass.callService('ha_bt_advanced', 'get_all_users', {}, true);
      if (result && result.users) {
        this.users = result.users;
        this.updateUserSelects();
      }
    } catch (error) {
      console.error('Error loading users:', error);
      // Fallback to just HA users
      this.users = Object.values(this._hass.users || {}).map(user => ({
        id: user.id,
        name: user.name,
        type: 'ha_user'
      }));
    }
  }

  updateUserSelects() {
    // Update all user select dropdowns
    const selects = ['onboard-owner', 'bulk-owner'];
    selects.forEach(selectId => {
      const select = this.shadowRoot.getElementById(selectId);
      if (select) {
        select.innerHTML = '<option value="">No Owner</option>';

        // Add HA users
        const haUsers = this.users.filter(u => u.type === 'ha_user');
        if (haUsers.length > 0) {
          const haGroup = document.createElement('optgroup');
          haGroup.label = 'Home Assistant Users';
          haUsers.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.name;
            haGroup.appendChild(option);
          });
          select.appendChild(haGroup);
        }

        // Add virtual users
        const virtualUsers = this.users.filter(u => u.type === 'virtual');
        if (virtualUsers.length > 0) {
          const vGroup = document.createElement('optgroup');
          vGroup.label = 'Guest Users';
          virtualUsers.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.name;
            vGroup.appendChild(option);
          });
          select.appendChild(vGroup);
        }
      }
    });
  }

  async startDiscovery() {
    try {
      // Start discovery mode
      await this._hass.callService('ha_bt_advanced', 'start_discovery', {
        duration: 60
      });

      this.discoveryMode = true;
      this.discoveryEndTime = Date.now() + 60000;
      this.discoveredBeacons = [];
      this.selectedBeaconsToOnboard.clear();

      // Update UI
      const btn = this.shadowRoot.getElementById('discovery-toggle');
      btn.textContent = 'Stop Discovery';
      btn.classList.add('active');

      const content = this.shadowRoot.getElementById('discovery-content');
      content.style.display = 'block';

      // Start polling for discovered beacons
      this.startDiscoveryPolling();

      // Start countdown
      this.startCountdown();
    } catch (error) {
      console.error('Error starting discovery:', error);
      alert('Failed to start discovery mode');
    }
  }

  async stopDiscovery() {
    try {
      await this._hass.callService('ha_bt_advanced', 'stop_discovery', {});
    } catch (error) {
      console.error('Error stopping discovery:', error);
    }

    this.discoveryMode = false;
    this.discoveryEndTime = null;

    // Update UI
    const btn = this.shadowRoot.getElementById('discovery-toggle');
    btn.textContent = 'Start Discovery';
    btn.classList.remove('active');

    // Stop polling
    if (this.discoveryInterval) {
      clearInterval(this.discoveryInterval);
      this.discoveryInterval = null;
    }

    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
      this.countdownInterval = null;
    }
  }

  startCountdown() {
    const countdownEl = this.shadowRoot.getElementById('discovery-countdown');

    this.countdownInterval = setInterval(() => {
      const remaining = Math.max(0, this.discoveryEndTime - Date.now());
      const seconds = Math.ceil(remaining / 1000);

      if (seconds === 0) {
        this.stopDiscovery();
        countdownEl.textContent = 'Discovery ended';
      } else {
        countdownEl.textContent = `⏱️ ${seconds}s remaining`;
      }
    }, 100);
  }

  startDiscoveryPolling() {
    // Poll for discovered beacons every 2 seconds
    this.discoveryInterval = setInterval(async () => {
      try {
        const result = await this._hass.callService('ha_bt_advanced', 'get_discovered_beacons', {}, true);
        if (result && result.beacons) {
          this.discoveredBeacons = result.beacons;
          this.updateDiscoveredList();
        }
      } catch (error) {
        console.error('Error polling discovered beacons:', error);
      }
    }, 2000);

    // Initial poll
    this.pollDiscoveredBeacons();
  }

  async pollDiscoveredBeacons() {
    try {
      const result = await this._hass.callService('ha_bt_advanced', 'get_discovered_beacons', {}, true);
      if (result && result.beacons) {
        this.discoveredBeacons = result.beacons;
        this.updateDiscoveredList();
      }
    } catch (error) {
      console.error('Error getting discovered beacons:', error);
    }
  }

  updateDiscoveredList() {
    const listEl = this.shadowRoot.getElementById('discovered-list');
    const btnEl = this.shadowRoot.getElementById('onboard-buttons');

    if (this.discoveredBeacons.length === 0) {
      listEl.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">Searching for nearby beacons...</div>';
      btnEl.style.display = 'none';
      return;
    }

    btnEl.style.display = 'block';

    listEl.innerHTML = this.discoveredBeacons.map(beacon => {
      const signalBars = this.getSignalBars(beacon.avg_rssi);
      const isSelected = this.selectedBeaconsToOnboard.has(beacon.mac);

      return `
        <div class="discovered-beacon ${isSelected ? 'selected' : ''}" data-mac="${beacon.mac}">
          <input type="checkbox" class="beacon-checkbox" ${isSelected ? 'checked' : ''}>
          <div class="beacon-info">
            <div>
              <span class="beacon-mac">${beacon.mac}</span>
              <span class="beacon-type">${beacon.beacon_type}</span>
            </div>
            <div class="signal-strength">
              <div class="signal-bars">
                ${signalBars}
              </div>
              <span>${beacon.avg_rssi} dBm</span>
            </div>
            <div class="beacon-stats">
              <span>Seen ${beacon.count} times</span>
              <span>${beacon.proxy_count} proxy${beacon.proxy_count !== 1 ? 'es' : ''}</span>
              <span>First: ${this.formatTime(beacon.first_seen)}</span>
            </div>
          </div>
          <button class="onboard-button onboard-single" onclick="this.getRootNode().host.onboardSingleBeacon('${beacon.mac}')">
            Onboard
          </button>
        </div>
      `;
    }).join('');

    // Add checkbox listeners
    listEl.querySelectorAll('.beacon-checkbox').forEach(checkbox => {
      checkbox.addEventListener('change', (e) => {
        const beaconEl = e.target.closest('.discovered-beacon');
        const mac = beaconEl.dataset.mac;

        if (e.target.checked) {
          this.selectedBeaconsToOnboard.add(mac);
          beaconEl.classList.add('selected');
        } else {
          this.selectedBeaconsToOnboard.delete(mac);
          beaconEl.classList.remove('selected');
        }

        this.updateOnboardButton();
      });
    });
  }

  getSignalBars(rssi) {
    const bars = 5;
    let active = 0;

    if (rssi >= -50) active = 5;
    else if (rssi >= -60) active = 4;
    else if (rssi >= -70) active = 3;
    else if (rssi >= -80) active = 2;
    else if (rssi >= -90) active = 1;

    let html = '';
    for (let i = 0; i < bars; i++) {
      html += `<div class="signal-bar ${i < active ? 'active' : ''}"></div>`;
    }
    return html;
  }

  formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    return date.toLocaleTimeString();
  }

  updateOnboardButton() {
    const btn = this.shadowRoot.getElementById('onboard-selected-btn');
    const count = this.selectedBeaconsToOnboard.size;

    btn.textContent = `Onboard Selected (${count})`;
    btn.disabled = count === 0;
  }

  async onboardSingleBeacon(mac) {
    const beacon = this.discoveredBeacons.find(b => b.mac === mac);
    if (!beacon) return;

    this.currentBeaconToOnboard = beacon;
    this.showOnboardModal(beacon);
  }

  showOnboardModal(beacon) {
    const modal = this.shadowRoot.getElementById('onboard-modal');
    const infoEl = this.shadowRoot.getElementById('onboard-beacon-info');

    infoEl.innerHTML = `
      <div><strong>MAC:</strong> ${beacon.mac}</div>
      <div><strong>Type:</strong> ${beacon.beacon_type}</div>
      <div><strong>Signal:</strong> ${beacon.avg_rssi} dBm</div>
      <div><strong>Detected by:</strong> ${beacon.proxies.join(', ')}</div>
    `;

    // Reset form
    this.shadowRoot.getElementById('onboard-name').value = '';
    this.shadowRoot.getElementById('onboard-owner').value = '';
    this.shadowRoot.getElementById('onboard-category').value = 'item';
    this.shadowRoot.getElementById('onboard-icon').value = '';
    this.shadowRoot.getElementById('onboard-notifications').checked = true;
    this.shadowRoot.getElementById('onboard-precision').value = 'medium';

    modal.style.display = 'flex';

    // Setup modal handlers
    const cancelBtn = this.shadowRoot.getElementById('onboard-cancel');
    const saveBtn = this.shadowRoot.getElementById('onboard-save');
    const createVirtualBtn = this.shadowRoot.getElementById('create-virtual-btn');

    cancelBtn.onclick = () => modal.style.display = 'none';

    saveBtn.onclick = async () => {
      const name = this.shadowRoot.getElementById('onboard-name').value.trim();
      if (!name) {
        alert('Please enter a name for the beacon');
        return;
      }

      try {
        await this._hass.callService('ha_bt_advanced', 'onboard_beacon', {
          mac_address: beacon.mac,
          name: name,
          owner: this.shadowRoot.getElementById('onboard-owner').value || undefined,
          beacon_category: this.shadowRoot.getElementById('onboard-category').value,
          beacon_icon: this.shadowRoot.getElementById('onboard-icon').value || undefined,
          notifications_enabled: this.shadowRoot.getElementById('onboard-notifications').checked,
          tracking_precision: this.shadowRoot.getElementById('onboard-precision').value
        });

        modal.style.display = 'none';
        alert(`Successfully onboarded ${name}`);

        // Refresh beacon list
        await this.loadBeacons();

        // Remove from discovered list
        this.discoveredBeacons = this.discoveredBeacons.filter(b => b.mac !== beacon.mac);
        this.updateDiscoveredList();
      } catch (error) {
        console.error('Error onboarding beacon:', error);
        alert('Failed to onboard beacon: ' + error.message);
      }
    };

    createVirtualBtn.onclick = async () => {
      const name = this.shadowRoot.getElementById('virtual-user-name').value.trim();
      if (!name) {
        alert('Please enter a name for the virtual user');
        return;
      }

      try {
        const result = await this._hass.callService('ha_bt_advanced', 'create_virtual_user', {
          name: name
        }, true);

        if (result && result.user_id) {
          // Reload users and select the new one
          await this.loadUsers();
          this.shadowRoot.getElementById('onboard-owner').value = result.user_id;
          this.shadowRoot.getElementById('virtual-user-name').value = '';
          alert(`Created virtual user: ${name}`);
        }
      } catch (error) {
        console.error('Error creating virtual user:', error);
        alert('Failed to create virtual user');
      }
    };
  }

  showBulkOnboardModal() {
    // Implementation for bulk onboarding modal
    const modal = this.shadowRoot.getElementById('bulk-onboard-modal');
    const countEl = this.shadowRoot.getElementById('bulk-count');
    const listEl = this.shadowRoot.getElementById('bulk-beacon-list');
    const namesEl = this.shadowRoot.getElementById('bulk-names');

    const selectedBeacons = this.discoveredBeacons.filter(b =>
      this.selectedBeaconsToOnboard.has(b.mac)
    );

    countEl.textContent = selectedBeacons.length;

    // Show selected beacons
    listEl.innerHTML = selectedBeacons.map(b => `
      <div style="padding: 8px; background: #f5f5f5; margin: 4px 0; border-radius: 4px;">
        <strong>${b.mac}</strong> - ${b.beacon_type} - ${b.avg_rssi} dBm
      </div>
    `).join('');

    // Create name inputs for each beacon
    namesEl.innerHTML = selectedBeacons.map(b => `
      <div style="margin: 8px 0;">
        <label style="display: block; font-size: 12px; color: #666;">${b.mac}</label>
        <input type="text" class="form-input beacon-name-input" data-mac="${b.mac}"
               placeholder="Enter name for this beacon">
      </div>
    `).join('');

    modal.style.display = 'flex';

    // Setup handlers
    const cancelBtn = this.shadowRoot.getElementById('bulk-cancel');
    const saveBtn = this.shadowRoot.getElementById('bulk-save');

    cancelBtn.onclick = () => modal.style.display = 'none';

    saveBtn.onclick = async () => {
      const beacons = [];
      let allNamesProvided = true;

      namesEl.querySelectorAll('.beacon-name-input').forEach(input => {
        const name = input.value.trim();
        if (!name) {
          allNamesProvided = false;
        } else {
          beacons.push({
            mac: input.dataset.mac,
            name: name
          });
        }
      });

      if (!allNamesProvided) {
        alert('Please provide names for all beacons');
        return;
      }

      const owner = this.shadowRoot.getElementById('bulk-owner').value;
      const category = this.shadowRoot.getElementById('bulk-category').value;
      const notifications = this.shadowRoot.getElementById('bulk-notifications').checked;

      try {
        // Onboard each beacon
        for (const beacon of beacons) {
          await this._hass.callService('ha_bt_advanced', 'onboard_beacon', {
            mac_address: beacon.mac,
            name: beacon.name,
            owner: owner || undefined,
            beacon_category: category,
            notifications_enabled: notifications,
            tracking_precision: 'medium'
          });
        }

        modal.style.display = 'none';
        alert(`Successfully onboarded ${beacons.length} beacons`);

        // Clear selection
        this.selectedBeaconsToOnboard.clear();

        // Refresh
        await this.loadBeacons();
        await this.pollDiscoveredBeacons();
      } catch (error) {
        console.error('Error onboarding beacons:', error);
        alert('Failed to onboard some beacons');
      }
    };
  }

  async loadProxies() {
    // Get proxy entities
    const entities = Object.keys(this._hass.states).filter(
      entityId => entityId.startsWith('binary_sensor.proxy_') && entityId.endsWith('_connectivity')
    );

    const proxyList = this.shadowRoot.getElementById('proxy-list');
    proxyList.innerHTML = '';

    entities.forEach(entityId => {
      const state = this._hass.states[entityId];
      const proxyId = entityId.replace('binary_sensor.proxy_', '').replace('_connectivity', '');

      const card = document.createElement('div');
      card.className = 'item-card';
      card.innerHTML = `
        <div class="item-header">
          <span class="item-name">${proxyId}</span>
          <span class="item-status ${state.state === 'on' ? 'status-online' : 'status-offline'}">
            ${state.state === 'on' ? 'Online' : 'Offline'}
          </span>
        </div>
        <div class="item-details">
          Last seen: ${state.last_changed ? new Date(state.last_changed).toLocaleString() : 'Never'}
        </div>
        <button class="delete-button" data-proxy-id="${proxyId}">Delete</button>
      `;

      card.querySelector('.delete-button').addEventListener('click', async (e) => {
        if (confirm(`Delete proxy ${proxyId}?`)) {
          await this._hass.callService('ha_bt_advanced', 'remove_proxy', {
            proxy_id: proxyId
          });
          this.loadData();
        }
      });

      proxyList.appendChild(card);
    });
  }

  async loadBeacons() {
    // Get beacon entities
    const entities = Object.keys(this._hass.states).filter(
      entityId => entityId.startsWith('device_tracker.beacon_')
    );

    const beaconList = this.shadowRoot.getElementById('beacon-list');
    beaconList.innerHTML = '';

    entities.forEach(entityId => {
      const state = this._hass.states[entityId];
      const mac = entityId.replace('device_tracker.beacon_', '').replace(/_/g, ':').toUpperCase();

      const card = document.createElement('div');
      card.className = 'item-card';
      card.innerHTML = `
        <div class="item-header">
          <span class="item-name">${state.attributes.friendly_name || mac}</span>
          <span class="item-status ${state.state === 'home' ? 'status-online' : 'status-offline'}">
            ${state.state}
          </span>
        </div>
        <div class="item-details">
          MAC: ${mac}<br>
          ${state.attributes.latitude ? `Location: ${state.attributes.latitude.toFixed(6)}, ${state.attributes.longitude.toFixed(6)}` : 'Location: Unknown'}
        </div>
        <button class="delete-button" data-mac="${mac}">Delete</button>
      `;

      card.querySelector('.delete-button').addEventListener('click', async (e) => {
        if (confirm(`Delete beacon ${mac}?`)) {
          await this._hass.callService('ha_bt_advanced', 'remove_beacon', {
            mac_address: mac
          });
          this.loadData();
        }
      });

      beaconList.appendChild(card);

      // Add to map if location available
      if (state.attributes.latitude && state.attributes.longitude) {
        this.addBeaconToMap(mac, state.attributes);
      }
    });
  }

  async loadZones() {
    // For now, just show an empty list since we need API endpoints to fetch zones
    const zoneList = this.shadowRoot.getElementById('zone-list');
    zoneList.innerHTML = '<div class="item-details">Zones will appear here after creation</div>';
  }

  addBeaconToMap(mac, attributes) {
    const latLng = [attributes.latitude, attributes.longitude];

    // Remove existing marker if any
    if (this.markers[mac]) {
      this.markers[mac].remove();
    }

    // Create new marker
    this.markers[mac] = L.marker(latLng, {
      icon: L.icon({
        iconUrl: 'data:image/svg+xml;base64,' + btoa(`
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
            <path fill="#4CAF50" d="M12,2C15.31,2 18,4.66 18,7.95C18,12.41 12,19 12,19C12,19 6,12.41 6,7.95C6,4.66 8.69,2 12,2M12,6A2,2 0 0,0 10,8A2,2 0 0,0 12,10A2,2 0 0,0 14,8A2,2 0 0,0 12,6M20,19C20,21.21 16.42,23 12,23C7.58,23 4,21.21 4,19C4,17.71 5.22,16.56 7.11,15.83L7.75,16.74C6.67,17.19 6,17.81 6,18.5C6,19.88 8.69,21 12,21C15.31,21 18,19.88 18,18.5C18,17.81 17.33,17.19 16.25,16.74L16.89,15.83C18.78,16.56 20,17.71 20,19Z"/>
          </svg>
        `),
        iconSize: [24, 24],
        iconAnchor: [12, 24]
      })
    }).addTo(this.map).bindPopup(attributes.friendly_name || mac);
  }
}

customElements.define('ha-bt-advanced-panel', HABTAdvancedPanel);

// Load Leaflet CSS and JS
if (!window.L) {
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
  document.head.appendChild(link);

  const script = document.createElement('script');
  script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
  document.head.appendChild(script);
}