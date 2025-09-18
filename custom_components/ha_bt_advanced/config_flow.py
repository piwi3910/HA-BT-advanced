"""Config flow for BLE Triangulation integration."""
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.const import (
    CONF_NAME,
    CONF_LATITUDE,
    CONF_LONGITUDE,
)

from .const import (
    DOMAIN,
    DEFAULT_MQTT_TOPIC_PREFIX,
    DEFAULT_MAX_READING_AGE,
    DEFAULT_MIN_PROXIES,
    DEFAULT_RSSI_SMOOTHING,
    DEFAULT_POSITION_SMOOTHING,
    DEFAULT_TX_POWER,
    DEFAULT_PATH_LOSS_EXPONENT,
    CONF_MQTT_TOPIC,
    CONF_SIGNAL_PARAMETERS,
    CONF_TX_POWER,
    CONF_PATH_LOSS_EXPONENT,
    CONF_RSSI_SMOOTHING,
    CONF_POSITION_SMOOTHING,
    CONF_MAX_READING_AGE,
    CONF_MIN_PROXIES,
    CONF_BEACONS,
    CONF_PROXIES,
    CONF_BEACON_CATEGORY,
    CONF_BEACON_ICON,
    BEACON_CATEGORY_PERSON,
    BEACON_CATEGORY_PET,
    BEACON_CATEGORY_ITEM,
    BEACON_CATEGORY_VEHICLE,
    DATA_MANAGER,
    CATEGORY_ICONS,
)

_LOGGER = logging.getLogger(__name__)

async def validate_input(hass: HomeAssistant, data: dict) -> Dict[str, Any]:
    """Validate the user input."""
    # TODO: Add validation if needed
    return {"title": "BLE Triangulation"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BLE Triangulation."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Optional(
                        CONF_MQTT_TOPIC,
                        default=DEFAULT_MQTT_TOPIC_PREFIX
                    ): str,
                    vol.Optional(
                        CONF_TX_POWER,
                        default=DEFAULT_TX_POWER
                    ): vol.All(int, vol.Range(min=-100, max=0)),
                    vol.Optional(
                        CONF_PATH_LOSS_EXPONENT,
                        default=DEFAULT_PATH_LOSS_EXPONENT
                    ): vol.All(float, vol.Range(min=1.5, max=4.0)),
                    vol.Optional(
                        CONF_RSSI_SMOOTHING,
                        default=DEFAULT_RSSI_SMOOTHING
                    ): vol.All(float, vol.Range(min=0.0, max=1.0)),
                    vol.Optional(
                        CONF_POSITION_SMOOTHING,
                        default=DEFAULT_POSITION_SMOOTHING
                    ): vol.All(float, vol.Range(min=0.0, max=1.0)),
                    vol.Optional(
                        CONF_MAX_READING_AGE,
                        default=DEFAULT_MAX_READING_AGE
                    ): vol.All(int, vol.Range(min=5, max=300)),
                    vol.Optional(
                        CONF_MIN_PROXIES,
                        default=DEFAULT_MIN_PROXIES
                    ): vol.All(int, vol.Range(min=1, max=10)),
                }),
                description_placeholders={
                    "mqtt_topic": "MQTT topic prefix for BLE data",
                    "tx_power": "Beacon TX power at 1m (dBm)",
                    "path_loss": "Path loss exponent for distance calculation",
                }
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            # Store signal parameters in a nested structure
            data = {
                CONF_MQTT_TOPIC: user_input.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC_PREFIX),
                CONF_SIGNAL_PARAMETERS: {
                    CONF_TX_POWER: user_input.get(CONF_TX_POWER, DEFAULT_TX_POWER),
                    CONF_PATH_LOSS_EXPONENT: user_input.get(CONF_PATH_LOSS_EXPONENT, DEFAULT_PATH_LOSS_EXPONENT),
                    CONF_RSSI_SMOOTHING: user_input.get(CONF_RSSI_SMOOTHING, DEFAULT_RSSI_SMOOTHING),
                    CONF_POSITION_SMOOTHING: user_input.get(CONF_POSITION_SMOOTHING, DEFAULT_POSITION_SMOOTHING),
                    CONF_MAX_READING_AGE: user_input.get(CONF_MAX_READING_AGE, DEFAULT_MAX_READING_AGE),
                    CONF_MIN_PROXIES: user_input.get(CONF_MIN_PROXIES, DEFAULT_MIN_PROXIES),
                },
            }
            return self.async_create_entry(title=info["title"], data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_MQTT_TOPIC,
                    default=user_input.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC_PREFIX)
                ): str,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for BLE Triangulation."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._entry_id = config_entry.entry_id
        self._selected_beacon = None
        self._selected_beacons = []
        self._discovery_start_time = None

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_menu()

    async def async_step_menu(self, user_input=None):
        """Show the main menu."""
        menu_options = [
            "beacons",
            "proxies",
            "signal",
            "calibration",
        ]

        return self.async_show_menu(
            step_id="menu",
            menu_options=menu_options
        )

    async def async_step_beacons(self, user_input=None):
        """Manage beacon configuration."""
        errors = {}

        # Get the manager instance
        manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get("manager")
        if not manager:
            manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get(DATA_MANAGER)

        if user_input is not None:
            if user_input.get("add_beacon"):
                return await self.async_step_discovery()
            elif user_input.get("remove_beacon"):
                # Remove selected beacon
                beacon_mac = user_input.get("beacon_to_remove")
                if beacon_mac and manager:
                    success = await manager.remove_beacon(beacon_mac)
                    if success:
                        # Reload to show updated list
                        return await self.async_step_beacons()
                    else:
                        errors["base"] = "remove_failed"
            elif user_input.get("back_to_menu"):
                return await self.async_step_menu()

        # Get current beacons
        beacons = {}
        if manager:
            for mac, info in manager.beacons.items():
                name = info.get(CONF_NAME, f"Beacon {mac}")
                category = info.get(CONF_BEACON_CATEGORY, BEACON_CATEGORY_ITEM)
                beacons[mac] = f"{name} ({mac}) - {category}"

        # Create form schema
        schema = {}
        if beacons:
            schema[vol.Optional("beacon_to_remove")] = vol.In(beacons)
            schema[vol.Optional("remove_beacon", default=False)] = cv.boolean

        schema[vol.Optional("add_beacon", default=False)] = cv.boolean
        schema[vol.Optional("back_to_menu", default=False)] = cv.boolean

        return self.async_show_form(
            step_id="beacons",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={
                "info": f"Currently tracking {len(beacons)} beacon(s)" if beacons else "No beacons configured yet"
            }
        )

    async def async_step_proxies(self, user_input=None):
        """Manage proxy configuration."""
        errors = {}

        # Get the manager instance
        manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get("manager")
        if not manager:
            manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get(DATA_MANAGER)

        if user_input is not None:
            if user_input.get("add_proxy"):
                # Add new proxy
                proxy_id = user_input.get("new_proxy_id")
                lat = user_input.get("new_proxy_lat")
                lng = user_input.get("new_proxy_lng")

                if proxy_id and lat is not None and lng is not None:
                    if manager:
                        success = await manager.add_proxy(proxy_id, lat, lng)
                        if success:
                            # Reload to show updated list
                            return await self.async_step_proxies()
                        else:
                            errors["base"] = "add_failed"
                else:
                    errors["base"] = "missing_data"

            elif user_input.get("remove_proxy"):
                # Remove selected proxy
                proxy_id = user_input.get("proxy_to_remove")
                if proxy_id and manager:
                    success = await manager.remove_proxy(proxy_id)
                    if success:
                        # Reload to show updated list
                        return await self.async_step_proxies()
                    else:
                        errors["base"] = "remove_failed"
            elif user_input.get("back_to_menu"):
                return await self.async_step_menu()

        # Get current proxies
        proxies = {}
        if manager:
            for proxy_id, info in manager.proxies.items():
                lat = info.get(CONF_LATITUDE)
                lng = info.get(CONF_LONGITUDE)
                proxies[proxy_id] = f"{proxy_id} ({lat:.6f}, {lng:.6f})"

        # Create form schema
        schema = {}

        # Add new proxy fields
        schema[vol.Optional("new_proxy_id")] = str
        schema[vol.Optional("new_proxy_lat", default=self.hass.config.latitude)] = vol.Coerce(float)
        schema[vol.Optional("new_proxy_lng", default=self.hass.config.longitude)] = vol.Coerce(float)
        schema[vol.Optional("add_proxy", default=False)] = cv.boolean

        # Remove proxy field
        if proxies:
            schema[vol.Optional("proxy_to_remove")] = vol.In(proxies)
            schema[vol.Optional("remove_proxy", default=False)] = cv.boolean

        schema[vol.Optional("back_to_menu", default=False)] = cv.boolean

        return self.async_show_form(
            step_id="proxies",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={
                "info": f"Currently have {len(proxies)} proxy/proxies configured" if proxies else "No proxies configured yet. They will be auto-detected from MQTT."
            }
        )

    async def async_step_signal(self, user_input=None):
        """Configure signal parameters."""
        # Get current config
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        signal_params = entry.data.get(CONF_SIGNAL_PARAMETERS, {})

        if user_input is not None:
            # Update config with new values
            new_signal_params = {
                CONF_TX_POWER: user_input.get(CONF_TX_POWER),
                CONF_PATH_LOSS_EXPONENT: user_input.get(CONF_PATH_LOSS_EXPONENT),
                CONF_RSSI_SMOOTHING: user_input.get(CONF_RSSI_SMOOTHING),
                CONF_POSITION_SMOOTHING: user_input.get(CONF_POSITION_SMOOTHING),
                CONF_MAX_READING_AGE: user_input.get(CONF_MAX_READING_AGE),
                CONF_MIN_PROXIES: user_input.get(CONF_MIN_PROXIES),
            }

            # Update the config entry
            new_data = {**entry.data}
            new_data[CONF_SIGNAL_PARAMETERS] = new_signal_params

            self.hass.config_entries.async_update_entry(
                entry,
                data=new_data
            )

            # Update the manager with new parameters
            manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get("manager")
            if not manager:
                manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get(DATA_MANAGER)
            if manager:
                manager.tx_power = new_signal_params[CONF_TX_POWER]
                manager.path_loss_exponent = new_signal_params[CONF_PATH_LOSS_EXPONENT]
                manager.rssi_smoothing = new_signal_params[CONF_RSSI_SMOOTHING]
                manager.position_smoothing = new_signal_params[CONF_POSITION_SMOOTHING]
                manager.max_reading_age = new_signal_params[CONF_MAX_READING_AGE]
                manager.min_proxies = new_signal_params[CONF_MIN_PROXIES]

            return await self.async_step_menu()

        return self.async_show_form(
            step_id="signal",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_TX_POWER,
                    default=signal_params.get(CONF_TX_POWER, DEFAULT_TX_POWER)
                ): vol.All(int, vol.Range(min=-100, max=0)),
                vol.Required(
                    CONF_PATH_LOSS_EXPONENT,
                    default=signal_params.get(CONF_PATH_LOSS_EXPONENT, DEFAULT_PATH_LOSS_EXPONENT)
                ): vol.All(float, vol.Range(min=1.5, max=4.0)),
                vol.Required(
                    CONF_RSSI_SMOOTHING,
                    default=signal_params.get(CONF_RSSI_SMOOTHING, DEFAULT_RSSI_SMOOTHING)
                ): vol.All(float, vol.Range(min=0.0, max=1.0)),
                vol.Required(
                    CONF_POSITION_SMOOTHING,
                    default=signal_params.get(CONF_POSITION_SMOOTHING, DEFAULT_POSITION_SMOOTHING)
                ): vol.All(float, vol.Range(min=0.0, max=1.0)),
                vol.Required(
                    CONF_MAX_READING_AGE,
                    default=signal_params.get(CONF_MAX_READING_AGE, DEFAULT_MAX_READING_AGE)
                ): vol.All(int, vol.Range(min=5, max=300)),
                vol.Required(
                    CONF_MIN_PROXIES,
                    default=signal_params.get(CONF_MIN_PROXIES, DEFAULT_MIN_PROXIES)
                ): vol.All(int, vol.Range(min=1, max=10)),
            }),
            description_placeholders={
                "info": (
                    "Signal parameters affect distance calculation and position accuracy.\n\n"
                    "• **TX Power**: Beacon transmission power at 1 meter (dBm)\n"
                    "• **Path Loss Exponent**: Environmental factor (2.0=free space, 3.0-4.0=indoors)\n"
                    "• **RSSI Smoothing**: Filter factor for signal strength (0=no smoothing, 1=maximum)\n"
                    "• **Position Smoothing**: Filter factor for position (0=no smoothing, 1=maximum)\n"
                    "• **Max Reading Age**: Discard readings older than this (seconds)\n"
                    "• **Min Proxies**: Minimum proxies needed for triangulation"
                )
            }
        )

    async def async_step_calibration(self, user_input=None):
        """Calibration step for determining TX power."""
        errors = {}

        # Get the manager instance
        manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get("manager")
        if not manager:
            manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get(DATA_MANAGER)

        # Get list of proxies for calibration
        proxy_options = {}
        if manager:
            for proxy_id in manager.proxies.keys():
                proxy_options[proxy_id] = proxy_id

        if not proxy_options:
            return self.async_show_form(
                step_id="calibration",
                data_schema=vol.Schema({
                    vol.Optional("back_to_menu", default=True): cv.boolean,
                }),
                errors={"base": "no_proxies"},
                description_placeholders={
                    "info": "No proxies available. Please configure proxies first."
                }
            )

        if user_input is not None:
            if user_input.get("start_calibration"):
                # Start calibration for selected proxy
                proxy_id = user_input.get("proxy_to_calibrate")
                reference_distance = user_input.get("reference_distance", 1.0)
                duration = user_input.get("duration", 30)

                if proxy_id and manager:
                    success = await manager.start_proxy_calibration(
                        proxy_id=proxy_id,
                        reference_distance=reference_distance,
                        duration=duration
                    )
                    if success:
                        return await self.async_step_calibration_started()
                    else:
                        errors["base"] = "calibration_failed"

            elif user_input.get("view_results"):
                # View calibration results for selected proxy
                proxy_id = user_input.get("proxy_to_view")
                if proxy_id and manager:
                    results = manager.get_calibration_results(proxy_id)
                    if results:
                        return await self.async_step_calibration_results({"proxy_id": proxy_id, "results": results})
                    else:
                        errors["base"] = "no_results"

            elif user_input.get("back_to_menu"):
                return await self.async_step_init()

        # Show calibration form
        return self.async_show_form(
            step_id="calibration",
            data_schema=vol.Schema({
                vol.Optional("proxy_to_calibrate"): vol.In(proxy_options),
                vol.Optional("reference_distance", default=1.0): vol.All(
                    vol.Coerce(float), vol.Range(min=0.5, max=10.0)
                ),
                vol.Optional("duration", default=30): vol.All(
                    vol.Coerce(int), vol.Range(min=10, max=120)
                ),
                vol.Optional("start_calibration", default=False): cv.boolean,
                vol.Optional("proxy_to_view"): vol.In(proxy_options),
                vol.Optional("view_results", default=False): cv.boolean,
                vol.Optional("back_to_menu", default=False): cv.boolean,
            }),
            errors=errors,
            description_placeholders={
                "info": (
                    "Calibration helps determine optimal signal parameters for your environment.\n\n"
                    "To calibrate:\n"
                    "1. Select a proxy and set the reference distance\n"
                    "2. Place a beacon at that exact distance from the proxy\n"
                    "3. Start calibration and wait for completion\n"
                    "4. View results to see calculated TX power"
                )
            }
        )

    async def async_step_calibration_results(self, context):
        """Show calibration results."""
        proxy_id = context.get("proxy_id")
        results = context.get("results")

        info_text = (
            f"**Calibration Results for {proxy_id}**\n\n"
            f"• TX Power at 1m: {results['tx_power']} dBm\n"
            f"• Average RSSI: {results['avg_rssi']} dBm\n"
            f"• Standard Deviation: {results['std_dev']} dBm\n"
            f"• Samples Collected: {results['sample_count']}\n"
            f"• Reference Distance: {results['reference_distance']} m\n\n"
            f"**Recommendation:**\n"
            f"Update Signal Parameters with TX Power = {results['tx_power']} dBm"
        )

        return self.async_show_form(
            step_id="calibration_results",
            data_schema=vol.Schema({
                vol.Optional("back_to_calibration", default=True): cv.boolean,
            }),
            description_placeholders={
                "info": info_text
            }
        )

    async def async_step_calibration_started(self, user_input=None):
        """Calibration started notification."""
        return self.async_show_form(
            step_id="calibration_started",
            data_schema=vol.Schema({
                vol.Optional("back_to_calibration", default=True): cv.boolean,
            }),
            description_placeholders={
                "info": "Calibration has started! Check notifications for progress and results."
            }
        )

    async def async_step_discovery(self, user_input=None):
        """Start beacon discovery mode."""
        errors = {}

        if user_input is not None:
            if user_input.get("start_discovery"):
                # Start discovery mode
                manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get("manager")
                if not manager:
                    manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get(DATA_MANAGER)
                if manager:
                    success = await manager.start_discovery(60)
                    if success:
                        self._discovery_start_time = time.time()
                        return await self.async_step_discovery_progress()
                    else:
                        errors["base"] = "discovery_failed"
            elif user_input.get("back_to_menu"):
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

    async def async_step_discovery_progress(self, user_input=None):
        """Show discovery progress with auto-refresh."""
        if user_input is not None:
            if user_input.get("stop_discovery"):
                # Stop discovery
                manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get("manager")
                if not manager:
                    manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get(DATA_MANAGER)
                if manager and manager.discovery_manager:
                    manager.discovery_manager.stop_discovery()
                return await self.async_step_discovered_beacons()

        # Calculate remaining time
        elapsed = time.time() - getattr(self, '_discovery_start_time', time.time())
        remaining = max(0, 60 - int(elapsed))

        # Get current discovered beacon info
        manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get("manager")
        if not manager:
            manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get(DATA_MANAGER)

        discovered_beacons_info = []
        discovered_count = 0

        if manager and manager.discovery_manager:
            # Get beacons that meet the minimum detection count
            discovered = manager.discovery_manager.get_discovered_beacons(min_count=1)  # Show all, even with 1 detection
            discovered_count = len(discovered)

            for beacon in discovered[:5]:  # Show top 5 beacons
                beacon_line = f"• {beacon['mac']} - {beacon['beacon_type']} (RSSI: {beacon['avg_rssi']} dBm, Count: {beacon['count']})"
                discovered_beacons_info.append(beacon_line)

        if remaining <= 0:
            # Auto-redirect to results when time is up
            return await self.async_step_discovered_beacons()

        # Build beacon list display
        beacon_list = "\n".join(discovered_beacons_info) if discovered_beacons_info else "No beacons detected yet..."

        # Create schema with a refresh button
        schema = {
            vol.Optional("refresh", default=False): cv.boolean,
            vol.Optional("stop_discovery", default=False): cv.boolean,
        }

        # Check if refresh was requested (auto-refresh every update)
        if user_input and user_input.get("refresh"):
            # Re-show the same form with updated data
            return await self.async_step_discovery_progress()

        return self.async_show_form(
            step_id="discovery_progress",
            data_schema=vol.Schema(schema),
            description_placeholders={
                "info": (
                    f"**🔍 Discovery in Progress**\n\n"
                    f"⏱️ **Time Remaining:** {remaining} seconds\n"
                    f"📡 **Beacons Found:** {discovered_count}\n\n"
                    f"**Discovered Beacons:**\n{beacon_list}\n\n"
                    f"_Place your beacon within 5 meters of a proxy._\n"
                    f"_Click 'Refresh' to update the list._"
                ),
            }
        )

    async def async_step_discovered_beacons(self, user_input=None):
        """Show discovered beacons for multi-select onboarding."""
        errors = {}

        manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get("manager")
        if not manager:
            manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get(DATA_MANAGER)

        if user_input is not None:
            if user_input.get("beacons_to_onboard"):
                # Store selected beacons for onboarding
                self._selected_beacons = user_input["beacons_to_onboard"]
                if len(self._selected_beacons) == 1:
                    # Single beacon - go to detailed config
                    self._selected_beacon = self._selected_beacons[0]
                    return await self.async_step_onboard_beacon()
                else:
                    # Multiple beacons - use quick onboarding
                    return await self.async_step_onboard_multiple()
            else:
                return await self.async_step_beacons()

        # Get discovered beacons
        discovered_options = {}

        if manager and manager.discovery_manager:
            discovered = manager.discovery_manager.get_discovered_beacons()
            for beacon in discovered:
                if beacon["mac"] not in manager.discovery_manager.onboarded_beacons:
                    label = (
                        f"{beacon['mac']} - {beacon['beacon_type']} "
                        f"(RSSI: {beacon['avg_rssi']:.0f} dBm, "
                        f"Seen: {beacon['count']} times)"
                    )
                    discovered_options[beacon["mac"]] = label

        if not discovered_options:
            return self.async_show_form(
                step_id="discovered_beacons",
                data_schema=vol.Schema({
                    vol.Optional("back_to_discovery", default=True): cv.boolean,
                }),
                errors={"base": "no_beacons_found"},
                description_placeholders={
                    "info": (
                        "**No new beacons discovered.**\n\n"
                        "Make sure:\n"
                        "• Your beacon is powered on\n"
                        "• The beacon is within 5 meters of a proxy\n"
                        "• The beacon is not already onboarded"
                    )
                }
            )

        return self.async_show_form(
            step_id="discovered_beacons",
            data_schema=vol.Schema({
                vol.Optional("beacons_to_onboard"): cv.multi_select(discovered_options),
                vol.Optional("back_to_beacons", default=False): cv.boolean,
            }),
            errors=errors,
            description_placeholders={
                "info": (
                    f"**Found {len(discovered_options)} new beacon(s)**\n\n"
                    f"Select one or more beacons to onboard.\n"
                    f"You can select multiple beacons for quick onboarding."
                )
            }
        )

    async def async_step_onboard_multiple(self, user_input=None):
        """Quick onboard multiple beacons."""
        errors = {}

        manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get("manager")
        if not manager:
            manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get(DATA_MANAGER)

        if user_input is not None:
            # Onboard all selected beacons with default settings
            success_count = 0
            failed_beacons = []

            category = user_input.get("category", BEACON_CATEGORY_ITEM)
            name_prefix = user_input.get("name_prefix", "Beacon")

            for mac in self._selected_beacons:
                # Generate name based on MAC address last 4 chars
                short_mac = mac.replace(":", "")[-4:].upper()
                name = f"{name_prefix} {short_mac}"

                if manager:
                    success = await manager.onboard_beacon(
                        mac_address=mac,
                        name=name,
                        category=category,
                        icon=CATEGORY_ICONS.get(category),
                        notifications_enabled=True,
                        tracking_precision="medium",
                    )
                    if success:
                        success_count += 1
                    else:
                        failed_beacons.append(mac)

            # Show results
            if success_count > 0:
                if failed_beacons:
                    _LOGGER.warning(f"Failed to onboard beacons: {failed_beacons}")
                return await self.async_step_onboard_success({
                    "count": success_count,
                    "failed": failed_beacons
                })
            else:
                errors["base"] = "onboard_failed"

        return self.async_show_form(
            step_id="onboard_multiple",
            data_schema=vol.Schema({
                vol.Required("name_prefix", default="Beacon"): str,
                vol.Required("category", default=BEACON_CATEGORY_ITEM): vol.In({
                    BEACON_CATEGORY_PERSON: "Person",
                    BEACON_CATEGORY_PET: "Pet",
                    BEACON_CATEGORY_ITEM: "Item",
                    BEACON_CATEGORY_VEHICLE: "Vehicle",
                }),
            }),
            errors=errors,
            description_placeholders={
                "info": (
                    f"**Quick Onboarding {len(self._selected_beacons)} Beacons**\n\n"
                    f"All beacons will be onboarded with:\n"
                    f"• Same category and settings\n"
                    f"• Automatic names based on MAC address\n"
                    f"• Default tracking precision (medium)\n\n"
                    f"You can customize individual beacons later."
                )
            }
        )

    async def async_step_onboard_beacon(self, user_input=None):
        """Onboard a specific beacon with detailed configuration."""
        errors = {}

        manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get("manager")
        if not manager:
            manager = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get(DATA_MANAGER)

        if user_input is not None:
            # Onboard the beacon
            if manager:
                success = await manager.onboard_beacon(
                    mac_address=self._selected_beacon,
                    name=user_input[CONF_NAME],
                    category=user_input.get("category", BEACON_CATEGORY_ITEM),
                    icon=user_input.get("icon"),
                    notifications_enabled=user_input.get("notifications", True),
                    tracking_precision=user_input.get("precision", "medium"),
                )

                if success:
                    return await self.async_step_onboard_success({"count": 1, "failed": []})
                else:
                    errors["base"] = "onboard_failed"

        # Get beacon info if available
        beacon_info = {}
        if manager and manager.discovery_manager:
            discovered = manager.discovery_manager.discovered_beacons.get(self._selected_beacon, {})
            beacon_info = discovered.get('beacon_data', {})

        # Suggest a name based on beacon type and MAC
        short_mac = self._selected_beacon.replace(":", "")[-4:].upper()
        suggested_name = f"Beacon {short_mac}"

        return self.async_show_form(
            step_id="onboard_beacon",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=suggested_name): str,
                vol.Required("category", default=BEACON_CATEGORY_ITEM): vol.In({
                    BEACON_CATEGORY_PERSON: "Person",
                    BEACON_CATEGORY_PET: "Pet",
                    BEACON_CATEGORY_ITEM: "Item",
                    BEACON_CATEGORY_VEHICLE: "Vehicle",
                }),
                vol.Optional("icon"): str,
                vol.Required("notifications", default=True): cv.boolean,
                vol.Required("precision", default="medium"): vol.In({
                    "low": "Low (faster, less accurate)",
                    "medium": "Medium (balanced)",
                    "high": "High (slower, more accurate)",
                }),
            }),
            errors=errors,
            description_placeholders={
                "info": (
                    f"**Configure Beacon: {self._selected_beacon}**\n\n"
                    f"UUID: {beacon_info.get('uuid', 'N/A')}\n"
                    f"Major: {beacon_info.get('major', 'N/A')}\n"
                    f"Minor: {beacon_info.get('minor', 'N/A')}"
                )
            }
        )

    async def async_step_onboard_success(self, context):
        """Show onboarding success message."""
        count = context.get("count", 0)
        failed = context.get("failed", [])

        if failed:
            info_text = (
                f"✅ **Successfully onboarded {count} beacon(s)**\n\n"
                f"⚠️ Failed to onboard: {', '.join(failed)}\n\n"
                f"The beacons are now being tracked on your map."
            )
        else:
            info_text = (
                f"✅ **Successfully onboarded {count} beacon(s)**\n\n"
                f"The beacon{'s are' if count > 1 else ' is'} now being tracked on your map.\n"
                f"You can view {'them' if count > 1 else 'it'} in Settings > Devices & Services > HA-BT-Advanced."
            )

        return self.async_show_form(
            step_id="onboard_success",
            data_schema=vol.Schema({
                vol.Optional("back_to_beacons", default=True): cv.boolean,
            }),
            description_placeholders={
                "info": info_text
            }
        )