"""Constants for the HA-BT-Advanced integration."""

DOMAIN = "ha_bt_advanced"

# Configuration constants
CONF_PROXIES = "proxies"
CONF_BEACONS = "beacons"
CONF_PROXY_ID = "proxy_id"
CONF_MAC_ADDRESS = "mac_address"
CONF_TX_POWER = "tx_power"
CONF_PATH_LOSS_EXPONENT = "path_loss_exponent"
CONF_RSSI_SMOOTHING = "rssi_smoothing"
CONF_POSITION_SMOOTHING = "position_smoothing"
CONF_MAX_READING_AGE = "max_reading_age"
CONF_MIN_PROXIES = "min_proxies"
CONF_SERVICE_ENABLED = "service_enabled"
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_SIGNAL_PARAMETERS = "signal_parameters"
CONF_ENVIRONMENT_PRESET = "environment_preset"
CONF_BEACON_CATEGORY = "category"
CONF_BEACON_ICON = "icon"
CONF_ZONE_ID = "zone_id"
CONF_ZONE_NAME = "zone_name"
CONF_ZONE_TYPE = "zone_type"
CONF_ZONE_COORDINATES = "coordinates"
CONF_WIFI_SSID = "wifi_ssid"
CONF_WIFI_PASSWORD = "wifi_password"
CONF_MQTT_HOST = "mqtt_host"
CONF_MQTT_USERNAME = "mqtt_username"
CONF_MQTT_PASSWORD = "mqtt_password"
CONF_FALLBACK_PASSWORD = "fallback_password"

# Beacon categories
BEACON_CATEGORY_PERSON = "person"
BEACON_CATEGORY_ITEM = "item"
BEACON_CATEGORY_PET = "pet"
BEACON_CATEGORY_VEHICLE = "vehicle"
BEACON_CATEGORY_OTHER = "other"

# Zone types
ZONE_TYPE_HOME = "home"
ZONE_TYPE_WORK = "work"
ZONE_TYPE_ROOM = "room"
ZONE_TYPE_CUSTOM = "custom"

# Default values
DEFAULT_TX_POWER = -59
DEFAULT_PATH_LOSS_EXPONENT = 2.0
DEFAULT_RSSI_SMOOTHING = 0.3
DEFAULT_POSITION_SMOOTHING = 0.2
DEFAULT_MAX_READING_AGE = 30
DEFAULT_MIN_PROXIES = 2
DEFAULT_MQTT_TOPIC_PREFIX = "ble-triangulation"
DEFAULT_MQTT_STATE_PREFIX = "ble-location"
DEFAULT_BEACON_ICON = "mdi:bluetooth"
DEFAULT_PERSON_ICON = "mdi:account"
DEFAULT_ITEM_ICON = "mdi:package-variant-closed"
DEFAULT_PET_ICON = "mdi:paw"
DEFAULT_VEHICLE_ICON = "mdi:car"

# Map of beacon categories to default icons
CATEGORY_ICONS = {
    BEACON_CATEGORY_PERSON: DEFAULT_PERSON_ICON,
    BEACON_CATEGORY_ITEM: DEFAULT_ITEM_ICON,
    BEACON_CATEGORY_PET: DEFAULT_PET_ICON,
    BEACON_CATEGORY_VEHICLE: DEFAULT_VEHICLE_ICON,
    BEACON_CATEGORY_OTHER: DEFAULT_BEACON_ICON,
}

# Data storage keys
DATA_CONFIG = "config"
DATA_MANAGER = "manager"

# Configuration directories
PROXY_CONFIG_DIR = "ha_bt_advanced/proxies"
BEACON_CONFIG_DIR = "ha_bt_advanced/beacons"
ZONE_CONFIG_DIR = "ha_bt_advanced/zones"

# Service names
SERVICE_RESTART = "restart"
SERVICE_ADD_BEACON = "add_beacon"
SERVICE_REMOVE_BEACON = "remove_beacon"
SERVICE_ADD_PROXY = "add_proxy"
SERVICE_REMOVE_PROXY = "remove_proxy"
SERVICE_ADD_ZONE = "add_zone"
SERVICE_REMOVE_ZONE = "remove_zone"
SERVICE_CALIBRATE = "calibrate"
SERVICE_GENERATE_ESPHOME = "generate_esphome_config"

# Signal attributes
ATTR_RSSI = "rssi"
ATTR_BEACON_MAC = "beacon_mac"
ATTR_PROXY_ID = "proxy_id"
ATTR_TIMESTAMP = "timestamp"
ATTR_DISTANCE = "distance"
ATTR_ICON = "icon"
ATTR_CATEGORY = "category"

# Device tracker attributes
ATTR_GPS_ACCURACY = "gps_accuracy"
ATTR_LAST_SEEN = "last_seen"
ATTR_SOURCE_PROXIES = "source_proxies"
ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"
ATTR_ZONE = "zone"

# Notification IDs
NOTIFICATION_NEW_BEACON = "new_beacon_{}"
NOTIFICATION_BEACON_MISSING = "beacon_missing_{}"
NOTIFICATION_PROXY_OFFLINE = "proxy_offline_{}"

# Event types
EVENT_BEACON_DISCOVERED = f"{DOMAIN}_beacon_discovered"
EVENT_BEACON_SEEN = f"{DOMAIN}_beacon_seen"
EVENT_BEACON_ZONE_CHANGE = f"{DOMAIN}_zone_change"
EVENT_PROXY_STATUS_CHANGE = f"{DOMAIN}_proxy_status_change"