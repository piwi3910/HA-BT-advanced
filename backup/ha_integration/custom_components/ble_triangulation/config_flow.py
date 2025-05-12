"""Config flow for BLE Triangulation integration."""
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
    CONF_TX_POWER,
    CONF_PATH_LOSS_EXPONENT,
    CONF_RSSI_SMOOTHING,
    CONF_POSITION_SMOOTHING,
    CONF_MAX_READING_AGE,
    CONF_MIN_PROXIES,
    CONF_SERVICE_ENABLED,
    CONF_MQTT_TOPIC,
    CONF_SIGNAL_PARAMETERS,
    DEFAULT_TX_POWER,
    DEFAULT_PATH_LOSS_EXPONENT,
    DEFAULT_RSSI_SMOOTHING,
    DEFAULT_POSITION_SMOOTHING,
    DEFAULT_MAX_READING_AGE,
    DEFAULT_MIN_PROXIES,
    DEFAULT_MQTT_TOPIC_PREFIX,
)

_LOGGER = logging.getLogger(__name__)

class BLETriangulationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BLE Triangulation."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate user input
            return self.async_create_entry(
                title="BLE Triangulation",
                data={
                    CONF_PROXIES: {},
                    CONF_BEACONS: {},
                    CONF_SERVICE_ENABLED: True,
                    CONF_MQTT_TOPIC: user_input.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC_PREFIX),
                    CONF_SIGNAL_PARAMETERS: {
                        CONF_TX_POWER: user_input.get(CONF_TX_POWER, DEFAULT_TX_POWER),
                        CONF_PATH_LOSS_EXPONENT: user_input.get(CONF_PATH_LOSS_EXPONENT, DEFAULT_PATH_LOSS_EXPONENT),
                        CONF_RSSI_SMOOTHING: user_input.get(CONF_RSSI_SMOOTHING, DEFAULT_RSSI_SMOOTHING),
                        CONF_POSITION_SMOOTHING: user_input.get(CONF_POSITION_SMOOTHING, DEFAULT_POSITION_SMOOTHING),
                        CONF_MAX_READING_AGE: user_input.get(CONF_MAX_READING_AGE, DEFAULT_MAX_READING_AGE),
                        CONF_MIN_PROXIES: user_input.get(CONF_MIN_PROXIES, DEFAULT_MIN_PROXIES),
                    },
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TX_POWER, default=DEFAULT_TX_POWER
                    ): vol.All(vol.Coerce(int), vol.Range(min=-100, max=0)),
                    vol.Optional(
                        CONF_PATH_LOSS_EXPONENT, default=DEFAULT_PATH_LOSS_EXPONENT
                    ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=5.0)),
                    vol.Optional(
                        CONF_RSSI_SMOOTHING, default=DEFAULT_RSSI_SMOOTHING
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                    vol.Optional(
                        CONF_POSITION_SMOOTHING, default=DEFAULT_POSITION_SMOOTHING
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                    vol.Optional(
                        CONF_MAX_READING_AGE, default=DEFAULT_MAX_READING_AGE
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                    vol.Optional(
                        CONF_MIN_PROXIES, default=DEFAULT_MIN_PROXIES
                    ): vol.All(vol.Coerce(int), vol.Range(min=2, max=10)),
                    vol.Optional(
                        CONF_MQTT_TOPIC, default=DEFAULT_MQTT_TOPIC_PREFIX
                    ): cv.string,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return BLETriangulationOptionsFlow(config_entry)


class BLETriangulationOptionsFlow(config_entries.OptionsFlow):
    """Handle BLE Triangulation options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        errors = {}
        data = dict(self.config_entry.data)
        signal_params = data.get(CONF_SIGNAL_PARAMETERS, {})

        if user_input is not None:
            # Update configuration
            new_signal_params = {
                CONF_TX_POWER: user_input.get(CONF_TX_POWER, signal_params.get(CONF_TX_POWER, DEFAULT_TX_POWER)),
                CONF_PATH_LOSS_EXPONENT: user_input.get(CONF_PATH_LOSS_EXPONENT, signal_params.get(CONF_PATH_LOSS_EXPONENT, DEFAULT_PATH_LOSS_EXPONENT)),
                CONF_RSSI_SMOOTHING: user_input.get(CONF_RSSI_SMOOTHING, signal_params.get(CONF_RSSI_SMOOTHING, DEFAULT_RSSI_SMOOTHING)),
                CONF_POSITION_SMOOTHING: user_input.get(CONF_POSITION_SMOOTHING, signal_params.get(CONF_POSITION_SMOOTHING, DEFAULT_POSITION_SMOOTHING)),
                CONF_MAX_READING_AGE: user_input.get(CONF_MAX_READING_AGE, signal_params.get(CONF_MAX_READING_AGE, DEFAULT_MAX_READING_AGE)),
                CONF_MIN_PROXIES: user_input.get(CONF_MIN_PROXIES, signal_params.get(CONF_MIN_PROXIES, DEFAULT_MIN_PROXIES)),
            }
            
            updated_data = {
                **data,
                CONF_SERVICE_ENABLED: user_input.get(CONF_SERVICE_ENABLED, data.get(CONF_SERVICE_ENABLED, True)),
                CONF_MQTT_TOPIC: user_input.get(CONF_MQTT_TOPIC, data.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC_PREFIX)),
                CONF_SIGNAL_PARAMETERS: new_signal_params,
            }

            self.hass.config_entries.async_update_entry(
                self.config_entry, data=updated_data
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SERVICE_ENABLED, 
                        default=data.get(CONF_SERVICE_ENABLED, True)
                    ): cv.boolean,
                    vol.Optional(
                        CONF_MQTT_TOPIC, 
                        default=data.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC_PREFIX)
                    ): cv.string,
                    vol.Optional(
                        CONF_TX_POWER, 
                        default=signal_params.get(CONF_TX_POWER, DEFAULT_TX_POWER)
                    ): vol.All(vol.Coerce(int), vol.Range(min=-100, max=0)),
                    vol.Optional(
                        CONF_PATH_LOSS_EXPONENT, 
                        default=signal_params.get(CONF_PATH_LOSS_EXPONENT, DEFAULT_PATH_LOSS_EXPONENT)
                    ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=5.0)),
                    vol.Optional(
                        CONF_RSSI_SMOOTHING, 
                        default=signal_params.get(CONF_RSSI_SMOOTHING, DEFAULT_RSSI_SMOOTHING)
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                    vol.Optional(
                        CONF_POSITION_SMOOTHING, 
                        default=signal_params.get(CONF_POSITION_SMOOTHING, DEFAULT_POSITION_SMOOTHING)
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                    vol.Optional(
                        CONF_MAX_READING_AGE, 
                        default=signal_params.get(CONF_MAX_READING_AGE, DEFAULT_MAX_READING_AGE)
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                    vol.Optional(
                        CONF_MIN_PROXIES, 
                        default=signal_params.get(CONF_MIN_PROXIES, DEFAULT_MIN_PROXIES)
                    ): vol.All(vol.Coerce(int), vol.Range(min=2, max=10)),
                }
            ),
            errors=errors,
        )