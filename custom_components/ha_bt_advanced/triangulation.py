"""Triangulation algorithm for BLE beacon positioning."""
import math
import time
from typing import Dict, List, Optional, Tuple, Any

class RSSIBuffer:
    """Maintains a rolling buffer of RSSI readings with timestamps."""

    def __init__(self, max_age: float = 30.0, smoothing_factor: float = 0.3):
        """Initialize RSSI buffer."""
        self.readings = []
        self.max_age = max_age
        self.smoothing_factor = smoothing_factor
        self.smoothed_rssi = None

    def add_reading(self, rssi: int, timestamp: float):
        """Add a new RSSI reading with timestamp."""
        self.readings.append((rssi, timestamp))
        
        # Update smoothed RSSI using exponential moving average
        if self.smoothed_rssi is None:
            self.smoothed_rssi = rssi
        else:
            self.smoothed_rssi = (
                self.smoothing_factor * rssi + 
                (1 - self.smoothing_factor) * self.smoothed_rssi
            )

    def clean_old_readings(self, current_time: float):
        """Remove readings older than max_age."""
        self.readings = [
            (rssi, ts) for rssi, ts in self.readings 
            if current_time - ts <= self.max_age
        ]

    def get_average_rssi(self) -> Optional[float]:
        """Get the average RSSI from recent readings."""
        if not self.readings:
            return None
        
        # Return the smoothed value instead of simple average
        return self.smoothed_rssi


class BeaconTracker:
    """Tracks RSSI readings from multiple proxies for a single beacon."""

    def __init__(
        self, 
        mac: str, 
        name: str, 
        tx_power: float, 
        path_loss_exponent: float,
        rssi_smoothing: float,
        position_smoothing: float,
        max_reading_age: float,
        icon: str = None,
        category: str = None,
    ):
        """Initialize the beacon tracker."""
        self.mac = mac
        self.name = name
        self.tx_power = tx_power
        self.path_loss_exponent = path_loss_exponent
        self.rssi_smoothing = rssi_smoothing
        self.max_reading_age = max_reading_age
        self.position_smoothing = position_smoothing
        self.icon = icon
        self.category = category
        
        # Dictionary of proxy_id -> RSSIBuffer
        self.proxy_readings: Dict[str, RSSIBuffer] = {}
        
        # Last calculated position
        self.latitude = None
        self.longitude = None
        self.accuracy = None
        self.last_update = None
        
        # Current zone
        self.zone = None
        self.prev_zone = None

    def update_reading(self, proxy_id: str, rssi: int, timestamp: float):
        """Update RSSI reading for a specific proxy."""
        if proxy_id not in self.proxy_readings:
            self.proxy_readings[proxy_id] = RSSIBuffer(
                max_age=self.max_reading_age,
                smoothing_factor=self.rssi_smoothing,
            )
        
        self.proxy_readings[proxy_id].add_reading(rssi, timestamp)

    def clean_old_readings(self):
        """Remove old readings from all proxy buffers."""
        current_time = time.time()
        for buffer in self.proxy_readings.values():
            buffer.clean_old_readings(current_time)

    def rssi_to_distance(self, rssi: float) -> float:
        """Convert RSSI to distance in meters using path loss model."""
        if rssi == 0:
            return 100.0  # Arbitrary large distance for zero RSSI
            
        ratio = (self.tx_power - rssi) / (10 * self.path_loss_exponent)
        return 10 ** ratio

    def get_proxy_distances(self, proxy_positions: Dict[str, Dict[str, float]]) -> List[Tuple]:
        """Get list of (lat, lng, distance) tuples for trilateration."""
        result = []
        current_time = time.time()
        
        for proxy_id, buffer in self.proxy_readings.items():
            buffer.clean_old_readings(current_time)
            avg_rssi = buffer.get_average_rssi()
            
            if avg_rssi is not None and proxy_id in proxy_positions:
                distance = self.rssi_to_distance(avg_rssi)
                lat = proxy_positions[proxy_id].get('latitude')
                lng = proxy_positions[proxy_id].get('longitude')
                if lat is not None and lng is not None:
                    result.append((lat, lng, distance))
                
        return result

    def update_position(
        self, 
        lat: float, 
        lng: float, 
        accuracy: float, 
        timestamp: float
    ):
        """Update beacon position with smoothing."""
        if self.latitude is None or self.longitude is None:
            # First position update
            self.latitude = lat
            self.longitude = lng
            self.accuracy = accuracy
        else:
            # Apply exponential moving average smoothing
            self.latitude = (
                self.position_smoothing * lat + 
                (1 - self.position_smoothing) * self.latitude
            )
            self.longitude = (
                self.position_smoothing * lng + 
                (1 - self.position_smoothing) * self.longitude
            )
            self.accuracy = (
                self.position_smoothing * accuracy + 
                (1 - self.position_smoothing) * self.accuracy
            )
            
        self.last_update = timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert beacon tracker state to dictionary."""
        return {
            "mac": self.mac,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
            "last_update": self.last_update,
            "zone": self.zone,
            "icon": self.icon,
            "category": self.category,
        }
    
    def __str__(self) -> str:
        """Return string representation."""
        return f"Beacon({self.name}, mac={self.mac}, pos=({self.latitude}, {self.longitude}))"


class Triangulator:
    """Performs triangulation based on distances from known points."""

    @staticmethod
    def trilaterate_2d(points: List[Tuple]) -> Tuple[float, float, float]:
        """
        Perform 2D trilateration to find the most likely position.
        points: List of (lat, lng, distance) tuples
        returns: (latitude, longitude, accuracy)
        """
        if len(points) < 2:
            return None, None, None
            
        # If only 2 points, use simpler method
        if len(points) == 2:
            return Triangulator.bilaterate_2d(points)
            
        # Convert lat/lng to x/y using simple approximation
        # (this works for small areas, for larger areas use proper projection)
        earth_radius = 6371000  # meters
        
        # Use first point as origin
        origin_lat, origin_lng, _ = points[0]
        
        # Convert to radians
        origin_lat_rad = origin_lat * (math.pi / 180)
        
        # Scale factors
        lat_scale = earth_radius  # meters per radian
        lng_scale = earth_radius * math.cos(origin_lat_rad)  # meters per radian
        
        # Convert all points to local x/y coordinates
        xy_points = []
        for lat, lng, distance in points:
            x = (lng - origin_lng) * (math.pi / 180) * lng_scale
            y = (lat - origin_lat) * (math.pi / 180) * lat_scale
            xy_points.append((x, y, distance))
        
        # Perform trilateration in x/y space (simplified least squares)
        # This is a simplification of the full least squares solution
        weights = [1/(d*d) if d > 0 else 1.0 for _, _, d in xy_points]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return None, None, None
            
        # Weighted average of circle intersections
        x_sum = 0
        y_sum = 0
        
        for i, (x1, y1, r1) in enumerate(xy_points):
            for j in range(i+1, len(xy_points)):
                x2, y2, r2 = xy_points[j]
                
                # Distance between centers
                d = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                
                # No solution if circles are too far apart or one contains the other
                if d > r1 + r2 or d < abs(r1 - r2):
                    continue
                
                # Math for circle intersection
                a = (r1*r1 - r2*r2 + d*d) / (2*d)
                h = math.sqrt(max(0, r1*r1 - a*a))  # Use max to avoid negative sqrt
                
                x3 = x1 + a * (x2 - x1) / d
                y3 = y1 + a * (y2 - y1) / d
                
                # Two intersection points
                x4_1 = x3 + h * (y2 - y1) / d
                y4_1 = y3 - h * (x2 - x1) / d
                
                x4_2 = x3 - h * (y2 - y1) / d
                y4_2 = y3 + h * (x2 - x1) / d
                
                # Calculate the weight for this pair based on distance measurement confidence
                pair_weight = weights[i] * weights[j]
                
                # Add both intersection points with weight
                x_sum += (x4_1 + x4_2) * pair_weight / 2
                y_sum += (y4_1 + y4_2) * pair_weight / 2
        
        # Check if we have any valid intersections
        if x_sum == 0 and y_sum == 0:
            # Fallback to weighted centroid of circles
            for i, ((x, y, r), w) in enumerate(zip(xy_points, weights)):
                x_sum += x * w
                y_sum += y * w
                
            x_result = x_sum / total_weight
            y_result = y_sum / total_weight
        else:
            # Normalize by weight sum
            x_result = x_sum / total_weight
            y_result = y_sum / total_weight
            
        # Calculate accuracy from residuals
        residuals = []
        for x, y, r in xy_points:
            actual_dist = math.sqrt((x_result - x)**2 + (y_result - y)**2)
            residuals.append(abs(actual_dist - r))
            
        # Use the average residual as our accuracy estimate
        if residuals:
            accuracy = sum(residuals) / len(residuals)
            # Ensure minimum accuracy of 1m
            accuracy = max(1.0, accuracy)
        else:
            accuracy = 10.0  # default when we can't estimate
            
        # Convert back to lat/lng
        result_lng = origin_lng + (x_result / lng_scale) * (180 / math.pi)
        result_lat = origin_lat + (y_result / lat_scale) * (180 / math.pi)
        
        return result_lat, result_lng, accuracy

    @staticmethod
    def bilaterate_2d(points: List[Tuple]) -> Tuple[float, float, float]:
        """
        Calculate position based on two distance measurements.
        This is a special case of trilateration with just 2 points.
        """
        (lat1, lng1, r1), (lat2, lng2, r2) = points
        
        # Convert to a local x-y coordinate system
        # (simple approximation assuming small distances)
        earth_radius = 6371000  # meters
        
        # Convert to radians
        lat1_rad = lat1 * (math.pi / 180)
        lat2_rad = lat2 * (math.pi / 180)
        lng1_rad = lng1 * (math.pi / 180)
        lng2_rad = lng2 * (math.pi / 180)
        
        # Calculate x-y coordinates
        x1, y1 = 0, 0  # First point is origin
        
        # Distance between points
        d_lat = (lat2_rad - lat1_rad) * earth_radius
        d_lng = (lng2_rad - lng1_rad) * earth_radius * math.cos(lat1_rad)
        
        x2 = d_lng
        y2 = d_lat
        
        d = math.sqrt(x2*x2 + y2*y2)
        
        # Handle edge cases
        if d == 0:
            # Points are in the same location, can't determine position
            return lat1, lng1, max(r1, r2)
            
        if d > r1 + r2:
            # Circles don't intersect, find point between them
            ratio = r1 / (r1 + r2)
            x = x1 + (x2 - x1) * ratio
            y = y1 + (y2 - y1) * ratio
            accuracy = d - (r1 + r2)
        elif d < abs(r1 - r2):
            # One circle contains the other
            if r1 > r2:
                ratio = r2 / r1
                x = x1 + (x2 - x1) * ratio
                y = y1 + (y2 - y1) * ratio
            else:
                ratio = r1 / r2
                x = x2 + (x1 - x2) * ratio
                y = y2 + (y1 - y2) * ratio
            accuracy = abs(r1 - r2) - d
        else:
            # Standard case - circles intersect
            a = (r1*r1 - r2*r2 + d*d) / (2*d)
            h = math.sqrt(r1*r1 - a*a)
            
            x3 = x1 + a * (x2 - x1) / d
            y3 = y1 + a * (y2 - y1) / d
            
            # We have two intersection points, choose the one that makes most sense
            # For now, just take average of the two points
            x4_1 = x3 + h * (y2 - y1) / d
            y4_1 = y3 - h * (x2 - x1) / d
            
            x4_2 = x3 - h * (y2 - y1) / d
            y4_2 = y3 + h * (x2 - x1) / d
            
            x = (x4_1 + x4_2) / 2
            y = (y4_1 + y4_2) / 2
            
            # Calculate accuracy based on how well circles fit
            accuracy = max(1.0, h)
            
        # Convert back to lat/lng
        result_lat = lat1 + (y / earth_radius) * (180 / math.pi)
        result_lng = lng1 + (x / (earth_radius * math.cos(lat1_rad))) * (180 / math.pi)
        
        return result_lat, result_lng, accuracy
        
    @staticmethod
    def check_point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
        """
        Check if a point is inside a polygon using ray casting algorithm.
        
        Args:
            point: A tuple of (latitude, longitude)
            polygon: A list of (latitude, longitude) tuples defining the polygon
            
        Returns:
            True if the point is inside the polygon, False otherwise
        """
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
            
        return inside