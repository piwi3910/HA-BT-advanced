"""Constants for the BLE Triangulation integration."""

DOMAIN = "ble_triangulation"

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

# Default values
DEFAULT_TX_POWER = -59
DEFAULT_PATH_LOSS_EXPONENT = 2.0
DEFAULT_RSSI_SMOOTHING = 0.3
DEFAULT_POSITION_SMOOTHING = 0.2
DEFAULT_MAX_READING_AGE = 30
DEFAULT_MIN_PROXIES = 2
DEFAULT_MQTT_TOPIC_PREFIX = "ble-triangulation"
DEFAULT_MQTT_STATE_PREFIX = "ble-location"

# Data storage keys
DATA_CONFIG = "config"
DATA_MANAGER = "manager"

# Configuration directories
PROXY_CONFIG_DIR = "ble_triangulation/proxies"
BEACON_CONFIG_DIR = "ble_triangulation/beacons"

# Service names
SERVICE_RESTART = "restart"
SERVICE_ADD_BEACON = "add_beacon"
SERVICE_REMOVE_BEACON = "remove_beacon"

# Signal attributes
ATTR_RSSI = "rssi"
ATTR_BEACON_MAC = "beacon_mac"
ATTR_PROXY_ID = "proxy_id"
ATTR_TIMESTAMP = "timestamp"

# Device tracker attributes
ATTR_GPS_ACCURACY = "gps_accuracy"
ATTR_LAST_SEEN = "last_seen"
ATTR_SOURCE_PROXIES = "source_proxies"