"""Config flow for HA-BT-Advanced integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_NAME,
    CONF_LATITUDE,
    CONF_LONGITUDE,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_PROXIES,
    CONF_BEACONS,
    CONF_PROXY_ID,
    CONF_MAC_ADDRESS,
    CONF_TX_POWER,
    CONF_PATH_LOSS_EXPONENT,
    CONF_RSSI_SMOOTHING,
    CONF_POSITION_SMOOTHING,
    CONF_MAX_READING_AGE,
    CONF_MIN_PROXIES,
    CONF_SERVICE_ENABLED,
    CONF_MQTT_TOPIC,
    CONF_SIGNAL_PARAMETERS,
    CONF_ENVIRONMENT_PRESET,
    DEFAULT_TX_POWER,
    DEFAULT_PATH_LOSS_EXPONENT,
    DEFAULT_RSSI_SMOOTHING,
    DEFAULT_POSITION_SMOOTHING,
    DEFAULT_MAX_READING_AGE,
    DEFAULT_MIN_PROXIES,
    DEFAULT_MQTT_TOPIC_PREFIX,
    DATA_MANAGER,
)

_LOGGER = logging.getLogger(__name__)

# Environment presets
PRESET_HOME = "home"
PRESET_OFFICE = "office"
PRESET_OPEN_SPACE = "open_space"

ENVIRONMENT_PRESETS = {
    PRESET_HOME: {
        CONF_TX_POWER: -59,
        CONF_PATH_LOSS_EXPONENT: 2.5,
        CONF_RSSI_SMOOTHING: 0.3,
        CONF_POSITION_SMOOTHING: 0.2,
    },
    PRESET_OFFICE: {
        CONF_TX_POWER: -63,
        CONF_PATH_LOSS_EXPONENT: 3.0,
        CONF_RSSI_SMOOTHING: 0.4,
        CONF_POSITION_SMOOTHING: 0.3,
    },
    PRESET_OPEN_SPACE: {
        CONF_TX_POWER: -59,
        CONF_PATH_LOSS_EXPONENT: 2.0,
        CONF_RSSI_SMOOTHING: 0.2,
        CONF_POSITION_SMOOTHING: 0.1,
    },
}

class HABTAdvancedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA-BT-Advanced."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize the config flow."""
        self.config_data = {
            CONF_PROXIES: {},
            CONF_BEACONS: {},
        }
        self._environment_preset = PRESET_HOME
        
    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Store basic config
            self.config_data[CONF_SERVICE_ENABLED] = user_input.get(CONF_SERVICE_ENABLED, True)
            self.config_data[CONF_MQTT_TOPIC] = user_input.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC_PREFIX)
            
            # Move to environment selection step
            return await self.async_step_environment_preset()

        # Show initial form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SERVICE_ENABLED, default=True): bool,
                    vol.Required(CONF_MQTT_TOPIC, default=DEFAULT_MQTT_TOPIC_PREFIX): cv.string,
                }
            ),
            errors=errors,
            description_placeholders={
                "integration_title": "HA-BT-Advanced",
                "documentation_url": "https://github.com/piwi3910/HA-BT-advanced",
            },
        )
        
    async def async_step_environment_preset(self, user_input=None) -> FlowResult:
        """Handle environment preset selection step."""
        errors = {}

        if user_input is not None:
            # Store selected preset
            self._environment_preset = user_input.get(CONF_ENVIRONMENT_PRESET, PRESET_HOME)
            
            # Move to detailed signal parameters
            return await self.async_step_signal_parameters()

        # Show preset selection form
        return self.async_show_form(
            step_id="environment_preset",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ENVIRONMENT_PRESET, default=PRESET_HOME): vol.In(
                        {
                            PRESET_HOME: "Home (indoor residential)",
                            PRESET_OFFICE: "Office (indoor commercial)",
                            PRESET_OPEN_SPACE: "Open Space (minimal obstacles)",
                        }
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "preset_description": (
                    "Select the environment type that best matches where your beacons will be used. "
                    "This will set optimal defaults for signal propagation parameters."
                ),
            },
        )
        
    async def async_step_signal_parameters(self, user_input=None) -> FlowResult:
        """Handle signal parameters configuration step."""
        errors = {}
        preset = ENVIRONMENT_PRESETS[self._environment_preset]

        if user_input is not None:
            # Store signal parameters
            self.config_data[CONF_SIGNAL_PARAMETERS] = {
                CONF_TX_POWER: user_input.get(CONF_TX_POWER, preset[CONF_TX_POWER]),
                CONF_PATH_LOSS_EXPONENT: user_input.get(CONF_PATH_LOSS_EXPONENT, preset[CONF_PATH_LOSS_EXPONENT]),
                CONF_RSSI_SMOOTHING: user_input.get(CONF_RSSI_SMOOTHING, preset[CONF_RSSI_SMOOTHING]),
                CONF_POSITION_SMOOTHING: user_input.get(CONF_POSITION_SMOOTHING, preset[CONF_POSITION_SMOOTHING]),
                CONF_MAX_READING_AGE: user_input.get(CONF_MAX_READING_AGE, DEFAULT_MAX_READING_AGE),
                CONF_MIN_PROXIES: user_input.get(CONF_MIN_PROXIES, DEFAULT_MIN_PROXIES),
            }
            
            # Create the config entry
            return self.async_create_entry(
                title="HA-BT-Advanced",
                data=self.config_data,
            )

        # Show signal parameters form with preset defaults
        return self.async_show_form(
            step_id="signal_parameters",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TX_POWER, default=preset[CONF_TX_POWER]): 
                        vol.All(vol.Coerce(int), vol.Range(min=-100, max=0)),
                    vol.Required(CONF_PATH_LOSS_EXPONENT, default=preset[CONF_PATH_LOSS_EXPONENT]): 
                        vol.All(vol.Coerce(float), vol.Range(min=1.0, max=5.0)),
                    vol.Required(CONF_RSSI_SMOOTHING, default=preset[CONF_RSSI_SMOOTHING]): 
                        vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                    vol.Required(CONF_POSITION_SMOOTHING, default=preset[CONF_POSITION_SMOOTHING]): 
                        vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                    vol.Required(CONF_MAX_READING_AGE, default=DEFAULT_MAX_READING_AGE): 
                        vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                    vol.Required(CONF_MIN_PROXIES, default=DEFAULT_MIN_PROXIES): 
                        vol.All(vol.Coerce(int), vol.Range(min=2, max=10)),
                }
            ),
            errors=errors,
            description_placeholders={
                "preset_name": {
                    PRESET_HOME: "Home",
                    PRESET_OFFICE: "Office",
                    PRESET_OPEN_SPACE: "Open Space",
                }[self._environment_preset],
                "tx_power_description": (
                    "Measured signal strength at 1 meter distance. "
                    "Typical values range from -59dBm (stronger) to -75dBm (weaker)."
                ),
                "path_loss_description": (
                    "How quickly signal strength diminishes with distance. "
                    "Higher values (3.0-4.0) for environments with many obstacles, "
                    "lower values (2.0-2.5) for open spaces."
                ),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return HABTAdvancedOptionsFlow(config_entry)


class HABTAdvancedOptionsFlow(config_entries.OptionsFlow):
    """Handle HA-BT-Advanced options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)
        self.config_data = dict(config_entry.data)
        self._discovered_beacons = []
        self._selected_beacon = None
        self._beacon_to_delete = None

    async def async_step_init(self, user_input=None):
        """Manage the options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "beacons",
                "proxies",
                "discovery",
                "signal_parameters",
            ]
        )

    async def async_step_beacons(self, user_input=None):
        """Manage beacons."""
        errors = {}

        if user_input is not None:
            if user_input.get("add_beacon"):
                return await self.async_step_discovery()
            elif user_input.get("beacon_to_delete"):
                self._beacon_to_delete = user_input["beacon_to_delete"]
                return await self.async_step_confirm_delete_beacon()

        # Get current beacons from manager
        manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get("manager")
        if not manager:
            # Try alternate key
            manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get(DATA_MANAGER)

        beacons = []
        beacon_options = {}

        if manager and hasattr(manager, '_trackers'):
            # Get onboarded beacons
            for mac, tracker in manager._trackers.items():
                beacon_name = f"{tracker.name} ({mac})"
                beacons.append(beacon_name)
                beacon_options[mac] = beacon_name

        if not beacons:
            beacons = ["No beacons onboarded"]

        schema = vol.Schema({
            vol.Optional("add_beacon", default=False): bool,
        })

        if beacon_options:
            schema = schema.extend({
                vol.Optional("beacon_to_delete"): vol.In(beacon_options),
            })

        return self.async_show_form(
            step_id="beacons",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "beacon_list": "\n".join(f"• {b}" for b in beacons),
                "beacon_count": str(len(beacon_options)),
            }
        )

    async def async_step_confirm_delete_beacon(self, user_input=None):
        """Confirm beacon deletion."""
        if user_input is not None:
            if user_input.get("confirm"):
                # Delete the beacon
                manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get("manager")
                if not manager:
                    manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get(DATA_MANAGER)
                if manager:
                    await manager.remove_beacon(self._beacon_to_delete)

            return await self.async_step_beacons()

        return self.async_show_form(
            step_id="confirm_delete_beacon",
            data_schema=vol.Schema({
                vol.Required("confirm", default=False): bool,
            }),
            description_placeholders={
                "beacon_mac": self._beacon_to_delete,
            }
        )

    async def async_step_proxies(self, user_input=None):
        """Manage proxies."""
        errors = {}

        # Get detected proxies from manager
        manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get("manager")
        if not manager:
            manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get(DATA_MANAGER)
        proxies = []

        if manager and hasattr(manager, 'proxies'):
            # Get auto-detected proxies
            for proxy_id, proxy_data in manager.proxies.items():
                # Check if proxy is online based on last seen time
                status = "Online"  # Simplified for now
                proxies.append(f"{proxy_id} - {status}")

        if not proxies:
            proxies = ["No proxies detected"]

        return self.async_show_form(
            step_id="proxies",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "proxy_list": "\n".join(f"• {p}" for p in proxies),
                "proxy_count": str(len(proxies)),
                "info": "Proxies are automatically detected when they send data via MQTT."
            }
        )

    async def async_step_discovery(self, user_input=None):
        """Start beacon discovery mode."""
        errors = {}

        if user_input is not None:
            if user_input.get("start_discovery"):
                # Start discovery mode
                manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get("manager")
                if not manager:
                    manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get(DATA_MANAGER)
                if manager:
                    await manager.start_discovery(60)
                    return await self.async_step_discovered_beacons()
            else:
                return await self.async_step_beacons()

        return self.async_show_form(
            step_id="discovery",
            data_schema=vol.Schema({
                vol.Required("start_discovery", default=False): bool,
            }),
            errors=errors,
            description_placeholders={
                "info": (
                    "Discovery mode will scan for nearby BLE beacons for 60 seconds.\n"
                    "Only beacons within ~5 meters (RSSI > -70 dBm) will be detected.\n"
                    "Make sure your beacon is nearby and powered on."
                ),
            }
        )

    async def async_step_discovered_beacons(self, user_input=None):
        """Show discovered beacons for onboarding."""
        errors = {}

        manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get("manager")
        if not manager:
            manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get(DATA_MANAGER)

        if user_input is not None:
            if user_input.get("beacon_to_onboard"):
                self._selected_beacon = user_input["beacon_to_onboard"]
                return await self.async_step_onboard_beacon()
            else:
                return await self.async_step_beacons()

        # Get discovered beacons
        discovered_options = {}

        if manager and manager.discovery_manager:
            discovered = manager.discovery_manager.get_discovered_beacons()
            for beacon in discovered:
                if beacon["mac"] not in manager.discovery_manager.onboarded_beacons:
                    label = f"{beacon['mac']} - {beacon['beacon_type']} ({beacon['avg_rssi']} dBm)"
                    discovered_options[beacon["mac"]] = label

        if not discovered_options:
            return self.async_show_form(
                step_id="discovered_beacons",
                data_schema=vol.Schema({}),
                errors={"base": "no_beacons_found"},
                description_placeholders={
                    "info": "No new beacons discovered. Make sure your beacon is nearby and try again."
                }
            )

        return self.async_show_form(
            step_id="discovered_beacons",
            data_schema=vol.Schema({
                vol.Required("beacon_to_onboard"): vol.In(discovered_options),
            }),
            errors=errors,
            description_placeholders={
                "beacon_count": str(len(discovered_options)),
            }
        )

    async def async_step_onboard_beacon(self, user_input=None):
        """Onboard a specific beacon."""
        errors = {}

        if user_input is not None:
            # Onboard the beacon
            manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get("manager")
        if not manager:
            manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get(DATA_MANAGER)
            if manager:
                success = await manager.onboard_beacon(
                    mac_address=self._selected_beacon,
                    name=user_input[CONF_NAME],
                    category=user_input.get("category", "item"),
                    icon=user_input.get("icon"),
                    notifications_enabled=user_input.get("notifications", True),
                    tracking_precision=user_input.get("precision", "medium"),
                )

                if success:
                    return await self.async_step_beacons()
                else:
                    errors["base"] = "onboarding_failed"

        return self.async_show_form(
            step_id="onboard_beacon",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): cv.string,
                vol.Optional("category", default="item"): vol.In({
                    "item": "Item",
                    "person": "Person",
                    "pet": "Pet",
                    "vehicle": "Vehicle",
                    "other": "Other",
                }),
                vol.Optional("icon"): cv.string,
                vol.Optional("notifications", default=True): bool,
                vol.Optional("precision", default="medium"): vol.In({
                    "low": "Low",
                    "medium": "Medium",
                    "high": "High",
                }),
            }),
            errors=errors,
            description_placeholders={
                "beacon_mac": self._selected_beacon,
            }
        )

    async def async_step_signal_parameters(self, user_input=None):
        """Configure signal parameters."""
        errors = {}

        if user_input is not None:
            # Update signal parameters
            updated_data = dict(self.config_data)
            updated_signal_params = {
                CONF_TX_POWER: user_input[CONF_TX_POWER],
                CONF_PATH_LOSS_EXPONENT: user_input[CONF_PATH_LOSS_EXPONENT],
                CONF_RSSI_SMOOTHING: user_input[CONF_RSSI_SMOOTHING],
                CONF_POSITION_SMOOTHING: user_input[CONF_POSITION_SMOOTHING],
                CONF_MAX_READING_AGE: user_input[CONF_MAX_READING_AGE],
                CONF_MIN_PROXIES: user_input[CONF_MIN_PROXIES],
            }
            updated_data[CONF_SIGNAL_PARAMETERS] = updated_signal_params

            # Update the config entry
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=updated_data
            )

            return self.async_create_entry(title="", data={})

        # Get current signal parameters
        signal_params = self.config_data.get(CONF_SIGNAL_PARAMETERS, {})

        return self.async_show_form(
            step_id="signal_parameters",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_TX_POWER,
                    default=signal_params.get(CONF_TX_POWER, DEFAULT_TX_POWER)
                ): vol.All(vol.Coerce(int), vol.Range(min=-100, max=0)),
                vol.Required(
                    CONF_PATH_LOSS_EXPONENT,
                    default=signal_params.get(CONF_PATH_LOSS_EXPONENT, DEFAULT_PATH_LOSS_EXPONENT)
                ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=5.0)),
                vol.Required(
                    CONF_RSSI_SMOOTHING,
                    default=signal_params.get(CONF_RSSI_SMOOTHING, DEFAULT_RSSI_SMOOTHING)
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                vol.Required(
                    CONF_POSITION_SMOOTHING,
                    default=signal_params.get(CONF_POSITION_SMOOTHING, DEFAULT_POSITION_SMOOTHING)
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                vol.Required(
                    CONF_MAX_READING_AGE,
                    default=signal_params.get(CONF_MAX_READING_AGE, DEFAULT_MAX_READING_AGE)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                vol.Required(
                    CONF_MIN_PROXIES,
                    default=signal_params.get(CONF_MIN_PROXIES, DEFAULT_MIN_PROXIES)
                ): vol.All(vol.Coerce(int), vol.Range(min=2, max=10)),
            }),
            errors=errors,
        )