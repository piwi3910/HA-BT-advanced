"""Discovery manager for beacon onboarding."""
import logging
import time
from typing import Dict, Any, Set, Optional, List
from datetime import datetime, timedelta
import re

_LOGGER = logging.getLogger(__name__)

# Beacon type patterns
BEACON_PATTERNS = {
    'ibeacon': {
        'uuid_pattern': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE),
        'has_major_minor': True,
    },
    'eddystone': {
        'frame_types': ['UID', 'URL', 'TLM', 'EID'],
    },
    'altbeacon': {
        'manufacturer_id': 0x0118,
    },
    'ruuvi': {
        'manufacturer_id': 0x0499,
    },
    'xiaomi': {
        'service_uuids': ['0000fe95-0000-1000-8000-00805f9b34fb'],
    },
    'tile': {
        'manufacturer_id': 0x0099,
    },
    'airtag': {
        'manufacturer_id': 0x004C,  # Apple
        'type_hint': 'FindMy',
    },
}

class DiscoveryManager:
    """Manages beacon discovery and onboarding."""

    def __init__(self, hass):
        """Initialize the discovery manager."""
        self.hass = hass
        self.discovery_mode = False
        self.discovery_end_time = None
        self.discovered_beacons: Dict[str, Dict[str, Any]] = {}
        self.onboarded_beacons: Set[str] = set()
        self.beacon_filters = {
            'include_uuids': [],
            'exclude_uuids': [],
            'min_rssi': -70,  # Proximity requirement
            'min_proxy_count': 1,
            'min_detection_count': 3,
        }
        self.virtual_users: Dict[str, Dict[str, Any]] = {}

    async def start_discovery(self, duration: int = 60) -> bool:
        """Start discovery mode with proximity filter."""
        self.discovery_mode = True
        self.discovery_end_time = time.time() + duration
        self.discovered_beacons.clear()
        _LOGGER.info(f"Discovery mode started for {duration} seconds")

        # Schedule auto-stop
        self.hass.loop.call_later(duration, self._stop_discovery)

        return True

    def _stop_discovery(self) -> None:
        """Stop discovery mode."""
        self.discovery_mode = False
        self.discovery_end_time = None
        _LOGGER.info(f"Discovery mode ended. Found {len(self.discovered_beacons)} beacons")

    def stop_discovery(self) -> None:
        """Manually stop discovery mode."""
        self._stop_discovery()

    def extend_discovery(self, additional_seconds: int = 30) -> None:
        """Extend discovery mode if user is actively using it."""
        if self.discovery_mode and self.discovery_end_time:
            self.discovery_end_time += additional_seconds
            _LOGGER.info(f"Discovery mode extended by {additional_seconds} seconds")

    def is_beacon_onboarded(self, mac: str) -> bool:
        """Check if a beacon is onboarded."""
        return mac.upper() in self.onboarded_beacons

    def add_onboarded_beacon(self, mac: str) -> None:
        """Add a beacon to the onboarded list."""
        self.onboarded_beacons.add(mac.upper())

    def remove_onboarded_beacon(self, mac: str) -> None:
        """Remove a beacon from the onboarded list."""
        self.onboarded_beacons.discard(mac.upper())

    def detect_beacon_type(self, beacon_data: Dict[str, Any]) -> str:
        """Detect the type of beacon from its data."""
        # Check for iBeacon
        if 'uuid' in beacon_data and 'major' in beacon_data and 'minor' in beacon_data:
            uuid = beacon_data.get('uuid', '')
            if BEACON_PATTERNS['ibeacon']['uuid_pattern'].match(uuid):
                return 'ibeacon'

        # Check for Eddystone
        if 'eddystone' in beacon_data or 'namespace' in beacon_data:
            return 'eddystone'

        # Check manufacturer IDs
        manufacturer_id = beacon_data.get('manufacturer_id')
        if manufacturer_id:
            if manufacturer_id == BEACON_PATTERNS['ruuvi']['manufacturer_id']:
                return 'ruuvi'
            elif manufacturer_id == BEACON_PATTERNS['tile']['manufacturer_id']:
                return 'tile'
            elif manufacturer_id == BEACON_PATTERNS['altbeacon']['manufacturer_id']:
                return 'altbeacon'
            elif manufacturer_id == BEACON_PATTERNS['airtag']['manufacturer_id']:
                # Additional check for AirTag
                if 'FindMy' in str(beacon_data):
                    return 'airtag'

        # Check service UUIDs for Xiaomi
        service_uuids = beacon_data.get('service_uuids', [])
        for uuid in BEACON_PATTERNS['xiaomi']['service_uuids']:
            if uuid in service_uuids:
                return 'xiaomi'

        return 'unknown'

    def should_process_beacon(self, mac: str, rssi: int, beacon_data: Dict[str, Any]) -> bool:
        """Determine if a beacon should be processed."""
        mac_upper = mac.upper()

        # Always process onboarded beacons
        if self.is_beacon_onboarded(mac):
            _LOGGER.debug(f"Beacon {mac_upper} is onboarded, will process normally")
            return True

        # In discovery mode, apply filters
        if not self.discovery_mode:
            _LOGGER.debug(f"Beacon {mac_upper} not onboarded and not in discovery mode, ignoring")
            return False

        _LOGGER.debug(f"In discovery mode, checking filters for {mac_upper}")

        # Check if discovery has expired
        if self.discovery_end_time and time.time() > self.discovery_end_time:
            self._stop_discovery()
            return False

        # Apply proximity filter (more negative = weaker signal)
        # We want to KEEP beacons with RSSI greater than threshold (closer)
        if rssi < self.beacon_filters['min_rssi']:
            _LOGGER.debug(f"Beacon {mac_upper} filtered out: RSSI {rssi} is weaker than threshold {self.beacon_filters['min_rssi']}")
            return False

        # Apply UUID filters
        uuid = beacon_data.get('uuid', '')
        if uuid:
            if self.beacon_filters['include_uuids'] and uuid not in self.beacon_filters['include_uuids']:
                return False
            if uuid in self.beacon_filters['exclude_uuids']:
                return False

        return True

    def process_discovery_beacon(self, mac: str, rssi: int, beacon_data: Dict[str, Any], proxy_id: str) -> None:
        """Process a beacon in discovery mode."""
        if not self.discovery_mode:
            _LOGGER.debug(f"Not in discovery mode, ignoring beacon {mac}")
            return

        mac_upper = mac.upper()
        current_time = time.time()

        _LOGGER.info(f"Processing discovery beacon: {mac_upper}, RSSI: {rssi}, Proxy: {proxy_id}")

        if mac_upper not in self.discovered_beacons:
            self.discovered_beacons[mac_upper] = {
                'first_seen': current_time,
                'last_seen': current_time,
                'count': 0,
                'rssi_values': [],
                'proxies': set(),
                'beacon_type': self.detect_beacon_type(beacon_data),
                'beacon_data': beacon_data,
            }

        beacon_info = self.discovered_beacons[mac_upper]
        beacon_info['last_seen'] = current_time
        beacon_info['count'] += 1
        beacon_info['rssi_values'].append(rssi)
        beacon_info['proxies'].add(proxy_id)

        _LOGGER.info(
            f"Discovery beacon {mac_upper}: count={beacon_info['count']}, "
            f"RSSI={rssi}, proxies={len(beacon_info['proxies'])}"
        )

        # Keep only last 10 RSSI values for averaging
        if len(beacon_info['rssi_values']) > 10:
            beacon_info['rssi_values'] = beacon_info['rssi_values'][-10:]

        # Update beacon data if newer
        beacon_info['beacon_data'].update(beacon_data)

    def get_discovered_beacons(self, min_count: int = 3) -> List[Dict[str, Any]]:
        """Get list of discovered beacons that meet criteria."""
        current_time = time.time()
        eligible_beacons = []

        _LOGGER.info(f"Getting discovered beacons: total={len(self.discovered_beacons)}, min_count={min_count}")

        for mac, info in self.discovered_beacons.items():
            # Skip if not enough detections
            if info['count'] < min_count:
                _LOGGER.debug(f"Beacon {mac} has count={info['count']} < {min_count}, skipping")
                continue

            # Skip if not seen recently (within last 10 seconds)
            time_since_seen = current_time - info['last_seen']
            if time_since_seen > 10:
                _LOGGER.debug(f"Beacon {mac} last seen {time_since_seen:.1f}s ago, skipping")
                continue

            # Calculate average RSSI
            avg_rssi = sum(info['rssi_values']) / len(info['rssi_values']) if info['rssi_values'] else -100

            eligible_beacons.append({
                'mac': mac,
                'beacon_type': info['beacon_type'],
                'avg_rssi': avg_rssi,
                'count': info['count'],
                'proxy_count': len(info['proxies']),
                'proxies': list(info['proxies']),
                'first_seen': datetime.fromtimestamp(info['first_seen']).isoformat(),
                'last_seen': datetime.fromtimestamp(info['last_seen']).isoformat(),
                'beacon_data': info['beacon_data'],
            })

        # Sort by signal strength (strongest first)
        eligible_beacons.sort(key=lambda x: x['avg_rssi'], reverse=True)

        return eligible_beacons

    async def create_virtual_user(self, name: str) -> str:
        """Create a virtual user for guests."""
        # Generate unique ID
        user_id = f"guest_{name.lower().replace(' ', '_')}_{int(time.time())}"

        self.virtual_users[user_id] = {
            'name': name,
            'type': 'virtual',
            'created_at': datetime.now().isoformat(),
            'beacons': [],
        }

        # Save to file
        await self._save_virtual_user(user_id)

        return user_id

    async def _save_virtual_user(self, user_id: str) -> None:
        """Save virtual user to file."""
        from pathlib import Path
        import yaml

        users_dir = Path(self.hass.config.path("ha_bt_advanced/users"))
        if not users_dir.exists():
            await self.hass.async_add_executor_job(lambda: users_dir.mkdir(parents=True, exist_ok=True))

        user_file = users_dir / f"{user_id}.yaml"
        user_data = self.virtual_users[user_id]

        content = yaml.dump(user_data)
        await self.hass.async_add_executor_job(user_file.write_text, content)

    async def load_virtual_users(self) -> None:
        """Load virtual users from files."""
        from pathlib import Path
        import yaml

        users_dir = Path(self.hass.config.path("ha_bt_advanced/users"))
        if not users_dir.exists():
            return

        file_paths = await self.hass.async_add_executor_job(
            lambda: list(users_dir.glob("guest_*.yaml"))
        )

        for file_path in file_paths:
            try:
                content = await self.hass.async_add_executor_job(file_path.read_text)
                user_data = yaml.safe_load(content)
                if user_data:
                    user_id = file_path.stem
                    self.virtual_users[user_id] = user_data
            except Exception as e:
                _LOGGER.error(f"Error loading virtual user from {file_path}: {e}")

    def get_all_users(self) -> List[Dict[str, str]]:
        """Get all users (HA users + virtual users)."""
        users = []

        # Add HA users
        for user in self.hass.auth.users:
            users.append({
                'id': user.id,
                'name': user.name,
                'type': 'ha_user',
            })

        # Add virtual users
        for user_id, user_data in self.virtual_users.items():
            users.append({
                'id': user_id,
                'name': user_data['name'],
                'type': 'virtual',
            })

        return users

    def set_beacon_filters(self, filters: Dict[str, Any]) -> None:
        """Update beacon discovery filters."""
        self.beacon_filters.update(filters)
        _LOGGER.info(f"Beacon filters updated: {self.beacon_filters}")