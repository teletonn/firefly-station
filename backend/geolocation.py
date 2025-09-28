import math
import time
import datetime
import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from backend import database

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LocationPoint:
    """Represents a geographic location point."""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    timestamp: Optional[datetime.datetime] = None

@dataclass
class Zone:
    """Represents a geographic zone."""
    id: int
    name: str
    description: Optional[str]
    center_latitude: float
    center_longitude: float
    radius_meters: float
    zone_type: str = 'circular'
    coordinates: Optional[str] = None
    is_active: bool = True
    created_by: Optional[int] = None
    created_by_username: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

@dataclass
class TrackingConfig:
    """Configuration for adaptive tracking."""
    active_interval_seconds: int = 600    # 10 minutes
    stationary_interval_seconds: int = 14400  # 4 hours
    motion_threshold_mps: float = 2.0     # 2 m/s threshold for motion detection
    min_location_accuracy: float = 50.0   # Minimum GPS accuracy in meters
    max_stationary_duration: int = 3600   # 1 hour max without movement before considering stationary

class GeolocationService:
    """Service for handling geolocation tracking, zones, and motion detection."""

    def __init__(self):
        self.tracking_configs: Dict[str, TrackingConfig] = {}
        self.user_locations: Dict[str, LocationPoint] = {}
        self.user_motion_state: Dict[str, bool] = {}
        self.last_tracking_update: Dict[str, datetime.datetime] = {}

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula.
        Returns distance in meters.
        """
        R = 6371000  # Earth's radius in meters

        lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
        lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def is_point_in_zone(self, point: LocationPoint, zone: Zone) -> bool:
        """
        Check if a point is within a zone.
        Supports circular and polygon zones.
        """
        if zone.zone_type == 'circular':
            distance = self.calculate_distance(
                point.latitude, point.longitude,
                zone.center_latitude, zone.center_longitude
            )
            return distance <= zone.radius_meters
        elif zone.zone_type == 'polygon':
            return self.is_point_in_polygon(point.latitude, point.longitude, zone.coordinates)
        else:
            logger.warning(f"Unknown zone type '{zone.zone_type}' for zone {zone.id}")
            return False

    def detect_motion(self, user_id: str, new_location: LocationPoint) -> Tuple[bool, float]:
        """
        Detect if user is moving based on location changes.
        Returns (is_moving, speed_mps).
        """
        if user_id not in self.user_locations:
            self.user_locations[user_id] = new_location
            return False, 0.0

        previous_location = self.user_locations[user_id]

        # Check if enough time has passed for meaningful motion detection
        if not previous_location.timestamp or not new_location.timestamp:
            self.user_locations[user_id] = new_location
            return False, 0.0

        time_diff = (new_location.timestamp - previous_location.timestamp).total_seconds()

        if time_diff < 30:  # Minimum 30 seconds between motion checks
            return self.user_motion_state.get(user_id, False), 0.0

        distance = self.calculate_distance(
            previous_location.latitude, previous_location.longitude,
            new_location.latitude, new_location.longitude
        )

        speed_mps = distance / time_diff if time_diff > 0 else 0.0

        # Get user's tracking config
        config = self.tracking_configs.get(user_id, TrackingConfig())
        is_moving = speed_mps >= config.motion_threshold_mps

        # Update motion state
        self.user_motion_state[user_id] = is_moving
        self.user_locations[user_id] = new_location

        return is_moving, speed_mps

    def is_point_in_polygon(self, lat: float, lng: float, polygon_coords_str: Optional[str]) -> bool:
        """
        Check if a point is inside a polygon using the ray casting algorithm.
        """
        if not polygon_coords_str:
            return False

        try:
            coordinates = json.loads(polygon_coords_str)
            if not coordinates or len(coordinates) < 3:
                return False

            # Ray casting algorithm
            inside = False
            n = len(coordinates)

            p1_lat, p1_lng = coordinates[0]
            for i in range(1, n + 1):
                p2_lat, p2_lng = coordinates[i % n]

                if lat > min(p1_lat, p2_lat):
                    if lat <= max(p1_lat, p2_lat):
                        if lng <= max(p1_lng, p2_lng):
                            if p1_lat != p2_lat:
                                xinters = (lat - p1_lat) * (p2_lng - p1_lng) / (p2_lat - p1_lat) + p1_lng
                            if p1_lng == p2_lng or lng <= xinters:
                                inside = not inside

                p1_lat, p1_lng = p2_lat, p2_lng

            return inside

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Error checking point in polygon: {e}")
            return False

    def calculate_polygon_area(self, coordinates_str: str) -> float:
        """
        Calculate the area of a polygon in square meters.
        """
        try:
            coordinates = json.loads(coordinates_str)
            if not coordinates or len(coordinates) < 3:
                return 0.0

            # Convert to radians for calculation
            coords_rad = [(math.radians(lng), math.radians(lat)) for lat, lng in coordinates]

            # Use spherical excess formula for polygon area on Earth
            R = 6371000  # Earth's radius in meters

            area = 0.0
            n = len(coords_rad)

            for i in range(n):
                j = (i + 1) % n
                lng1, lat1 = coords_rad[i]
                lng2, lat2 = coords_rad[j]

                delta_lng = lng2 - lng1

                # Handle longitude wraparound
                if abs(delta_lng) > math.pi:
                    if delta_lng > 0:
                        delta_lng -= 2 * math.pi
                    else:
                        delta_lng += 2 * math.pi

                area += lng1 * lat2 - lng2 * lat1

            area = abs(area) * R * R / 2
            return area

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Error calculating polygon area: {e}")
            return 0.0

    def detect_zone_intersections(self, zones: List[Zone]) -> List[Dict[str, Any]]:
        """
        Detect intersections between zones.
        Returns list of intersecting zone pairs.
        """
        intersections = []

        for i, zone1 in enumerate(zones):
            for zone2 in zones[i+1:]:
                if self.zones_intersect(zone1, zone2):
                    intersections.append({
                        'zone1_id': zone1.id,
                        'zone1_name': zone1.name,
                        'zone2_id': zone2.id,
                        'zone2_name': zone2.name,
                        'intersection_type': self.get_intersection_type(zone1, zone2)
                    })

        return intersections

    def zones_intersect(self, zone1: Zone, zone2: Zone) -> bool:
        """
        Check if two zones intersect.
        """
        if zone1.zone_type == 'circular' and zone2.zone_type == 'circular':
            # Circle-circle intersection
            distance = self.calculate_distance(
                zone1.center_latitude, zone1.center_longitude,
                zone2.center_latitude, zone2.center_longitude
            )
            return distance < (zone1.radius_meters + zone2.radius_meters)

        elif zone1.zone_type == 'polygon' and zone2.zone_type == 'polygon':
            # Polygon-polygon intersection (simplified)
            return self.polygons_intersect(zone1.coordinates, zone2.coordinates)

        else:
            # Mixed types - check if any polygon contains the circle center
            if zone1.zone_type == 'polygon':
                return self.is_point_in_polygon(
                    zone2.center_latitude, zone2.center_longitude, zone1.coordinates
                )
            else:
                return self.is_point_in_polygon(
                    zone1.center_latitude, zone1.center_longitude, zone2.coordinates
                )

    def polygons_intersect(self, poly1_coords_str: Optional[str], poly2_coords_str: Optional[str]) -> bool:
        """
        Check if two polygons intersect (simplified implementation).
        """
        if not poly1_coords_str or not poly2_coords_str:
            return False

        try:
            poly1 = json.loads(poly1_coords_str)
            poly2 = json.loads(poly2_coords_str)

            # Simple bounding box intersection first
            if not self.bounding_boxes_intersect(poly1, poly2):
                return False

            # For more accurate detection, we'd need a full polygon clipping library
            # This is a simplified version
            return True

        except (json.JSONDecodeError, ValueError, TypeError):
            return False

    def bounding_boxes_intersect(self, poly1: List[List[float]], poly2: List[List[float]]) -> bool:
        """
        Check if bounding boxes of two polygons intersect.
        """
        def get_bounds(polygon):
            lats = [point[0] for point in polygon]
            lngs = [point[1] for point in polygon]
            return {
                'min_lat': min(lats),
                'max_lat': max(lats),
                'min_lng': min(lngs),
                'max_lng': max(lngs)
            }

        bounds1 = get_bounds(poly1)
        bounds2 = get_bounds(poly2)

        # Check for non-intersection
        return not (bounds1['max_lat'] < bounds2['min_lat'] or
                   bounds1['min_lat'] > bounds2['max_lat'] or
                   bounds1['max_lng'] < bounds2['min_lng'] or
                   bounds1['min_lng'] > bounds2['max_lng'])

    def get_intersection_type(self, zone1: Zone, zone2: Zone) -> str:
        """
        Determine the type of intersection between zones.
        """
        if zone1.zone_type == 'circular' and zone2.zone_type == 'circular':
            distance = self.calculate_distance(
                zone1.center_latitude, zone1.center_longitude,
                zone2.center_latitude, zone2.center_longitude
            )
            sum_radii = zone1.radius_meters + zone2.radius_meters

            if distance < abs(zone1.radius_meters - zone2.radius_meters):
                return 'complete_overlap'
            elif distance == sum_radii:
                return 'touching'
            else:
                return 'partial_overlap'

        return 'unknown'

    def calculate_zone_statistics(self, zone: Zone) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics for a zone.
        """
        stats = {
            'zone_id': zone.id,
            'zone_name': zone.name,
            'zone_type': zone.zone_type,
            'area_m2': 0,
            'perimeter_m': 0,
            'center_point': [zone.center_latitude, zone.center_longitude],
            'bounds': None,
            'complexity': 'simple'
        }

        if zone.zone_type == 'circular':
            # Circle statistics
            stats['area_m2'] = math.pi * (zone.radius_meters ** 2)
            stats['perimeter_m'] = 2 * math.pi * zone.radius_meters
            stats['bounds'] = {
                'min_lat': zone.center_latitude - (zone.radius_meters / 111000),
                'max_lat': zone.center_latitude + (zone.radius_meters / 111000),
                'min_lng': zone.center_longitude - (zone.radius_meters / 111000),
                'max_lng': zone.center_longitude + (zone.radius_meters / 111000)
            }

        elif zone.zone_type == 'polygon' and zone.coordinates:
            # Polygon statistics
            try:
                coordinates = json.loads(zone.coordinates)
                stats['area_m2'] = self.calculate_polygon_area(zone.coordinates)

                # Calculate perimeter
                perimeter = 0
                for i in range(len(coordinates)):
                    p1 = coordinates[i]
                    p2 = coordinates[(i + 1) % len(coordinates)]
                    distance = self.calculate_distance(p1[0], p1[1], p2[0], p2[1])
                    perimeter += distance

                stats['perimeter_m'] = perimeter
                stats['complexity'] = 'complex' if len(coordinates) > 10 else 'moderate'

                # Calculate bounds
                lats = [point[0] for point in coordinates]
                lngs = [point[1] for point in coordinates]
                stats['bounds'] = {
                    'min_lat': min(lats),
                    'max_lat': max(lats),
                    'min_lng': min(lngs),
                    'max_lng': max(lngs)
                }

            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.error(f"Error calculating polygon statistics: {e}")

        return stats

    def get_tracking_interval(self, user_id: str) -> int:
        """
        Get the appropriate tracking interval based on user's motion state.
        """
        config = self.tracking_configs.get(user_id, TrackingConfig())
        is_moving = self.user_motion_state.get(user_id, False)

        if is_moving:
            return config.active_interval_seconds
        else:
            return config.stationary_interval_seconds

    def should_update_tracking(self, user_id: str) -> bool:
        """
        Determine if it's time to update tracking for a user.
        """
        if user_id not in self.last_tracking_update:
            return True

        last_update = self.last_tracking_update[user_id]
        interval = self.get_tracking_interval(user_id)
        time_since_update = (datetime.datetime.now() - last_update).total_seconds()

        return time_since_update >= interval

    def process_location_update(self, user_id: str, latitude: float, longitude: float,
                              altitude: Optional[float] = None, accuracy: Optional[float] = None,
                              battery_level: Optional[int] = None) -> Dict:
        """
        Process a location update from a user device.
        Returns update information including alerts and zone changes.
        """
        current_time = datetime.datetime.now()
        location_point = LocationPoint(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            accuracy=accuracy,
            timestamp=current_time
        )

        # Detect motion
        is_moving, speed_mps = self.detect_motion(user_id, location_point)

        # Get current zone
        current_zone_id = self.get_user_current_zone(user_id)

        # Check zone boundaries and detect zone changes
        zone_changes = self.check_zone_boundaries(user_id, location_point)

        # Create alerts if needed
        alerts = self.check_alert_conditions(user_id, location_point, is_moving, speed_mps, zone_changes)

        # Update database
        update_data = {
            'location_updated': database.update_user_location(user_id, latitude, longitude, altitude, battery_level),
            'history_inserted': database.insert_location_history(
                user_id, latitude, longitude, altitude, accuracy, speed_mps, None, battery_level, is_moving
            ),
            'zone_updated': False,
            'alerts_created': len(alerts)
        }

        # Update user's current zone if changed
        if zone_changes.get('zone_changed', False):
            new_zone_id = zone_changes.get('new_zone_id')
            if database.update_user_location(user_id, latitude, longitude, altitude, battery_level):
                # Also update current_zone_id in users table
                conn = database.get_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET current_zone_id = ? WHERE id = ?', (new_zone_id, user_id))
                conn.commit()
                conn.close()
                update_data['zone_updated'] = True

        # Update tracking timestamp
        self.last_tracking_update[user_id] = current_time

        return {
            'success': True,
            'is_moving': is_moving,
            'speed_mps': speed_mps,
            'zone_changes': zone_changes,
            'alerts': alerts,
            'update_data': update_data
        }

    def get_user_current_zone(self, user_id: str) -> Optional[int]:
        """Get the current zone ID for a user."""
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT current_zone_id FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row['current_zone_id'] if row and row['current_zone_id'] else None

    def check_zone_boundaries(self, user_id: str, location_point: LocationPoint) -> Dict:
        """
        Check if user has entered or exited any zones.
        Returns zone change information.
        """
        # Get all active zones
        zones = [Zone(**zone_data) for zone_data in database.get_all_zones()]

        current_zone_id = self.get_user_current_zone(user_id)
        new_zone_id = None
        zone_entered = False
        zone_exited = False

        # Check each zone
        for zone in zones:
            is_in_zone = self.is_point_in_zone(location_point, zone)

            if is_in_zone:
                if current_zone_id != zone.id:
                    # User entered this zone
                    new_zone_id = zone.id
                    zone_entered = True
                    break
            else:
                if current_zone_id == zone.id:
                    # User exited this zone
                    zone_exited = True
                    new_zone_id = None

        return {
            'zone_changed': zone_entered or zone_exited,
            'zone_entered': zone_entered,
            'zone_exited': zone_exited,
            'new_zone_id': new_zone_id,
            'previous_zone_id': current_zone_id
        }

    def check_alert_conditions(self, user_id: str, location_point: LocationPoint,
                             is_moving: bool, speed_mps: float, zone_changes: Dict) -> List[Dict]:
        """
        Check various conditions and create alerts as needed.
        """
        alerts = []

        # Zone entry/exit alerts
        if zone_changes.get('zone_entered'):
            zone_id = zone_changes.get('new_zone_id')
            zone = database.get_zone(zone_id)
            if zone:
                alert_id = database.create_alert(
                    user_id=user_id,
                    zone_id=zone_id,
                    alert_type='zone_entry',
                    title=f'Zone Entry: {zone["name"]}',
                    message=f'User entered zone: {zone["name"]}',
                    location_latitude=location_point.latitude,
                    location_longitude=location_point.longitude
                )
                if alert_id:
                    alerts.append({
                        'id': alert_id,
                        'type': 'zone_entry',
                        'zone_name': zone['name']
                    })

        if zone_changes.get('zone_exited'):
            zone_id = zone_changes.get('previous_zone_id')
            zone = database.get_zone(zone_id)
            if zone:
                alert_id = database.create_alert(
                    user_id=user_id,
                    zone_id=zone_id,
                    alert_type='zone_exit',
                    title=f'Zone Exit: {zone["name"]}',
                    message=f'User exited zone: {zone["name"]}',
                    location_latitude=location_point.latitude,
                    location_longitude=location_point.longitude
                )
                if alert_id:
                    alerts.append({
                        'id': alert_id,
                        'type': 'zone_exit',
                        'zone_name': zone['name']
                    })

        # Speeding alert (if moving too fast)
        if is_moving and speed_mps > 15.0:  # 15 m/s = ~54 km/h
            alert_id = database.create_alert(
                user_id=user_id,
                zone_id=None,
                alert_type='speeding',
                title='Speed Alert',
                message=f'User speed: {speed_mps:.1f} m/s ({speed_mps*3.6:.1f} km/h)',
                location_latitude=location_point.latitude,
                location_longitude=location_point.longitude
            )
            if alert_id:
                alerts.append({
                    'id': alert_id,
                    'type': 'speeding',
                    'speed_mps': speed_mps
                })

        # Battery low alert
        if location_point.altitude and location_point.altitude < 20:  # Assuming altitude is used for battery in this context
            alert_id = database.create_alert(
                user_id=user_id,
                zone_id=None,
                alert_type='battery_low',
                title='Low Battery Alert',
                message=f'User battery level is low: {location_point.altitude}%',
                location_latitude=location_point.latitude,
                location_longitude=location_point.longitude
            )
            if alert_id:
                alerts.append({
                    'id': alert_id,
                    'type': 'battery_low',
                    'battery_level': location_point.altitude
                })

        return alerts

    def get_user_location_summary(self, user_id: str) -> Dict:
        """Get a summary of user's location and tracking status."""
        # Get user data
        user = database.get_user(user_id)
        if not user:
            return {'error': 'User not found'}

        # Get recent location history
        history = database.get_location_history(user_id, limit=10)

        # Get current zone
        current_zone_id = self.get_user_current_zone(user_id)
        current_zone = None
        if current_zone_id:
            current_zone = database.get_zone(current_zone_id)

        # Get tracking config
        config = self.tracking_configs.get(user_id, TrackingConfig())

        return {
            'user_id': user_id,
            'current_location': {
                'latitude': user.get('latitude'),
                'longitude': user.get('longitude'),
                'altitude': user.get('altitude'),
                'last_update': user.get('last_location_update')
            },
            'current_zone': current_zone,
            'tracking_enabled': user.get('tracking_enabled', True),
            'tracking_config': {
                'active_interval_seconds': config.active_interval_seconds,
                'stationary_interval_seconds': config.stationary_interval_seconds,
                'motion_threshold_mps': config.motion_threshold_mps
            },
            'motion_state': self.user_motion_state.get(user_id, False),
            'recent_history_count': len(history),
            'device_status': user.get('device_status', 'unknown')
        }

    def update_user_tracking_config(self, user_id: str, **config_updates):
        """Update tracking configuration for a user."""
        if user_id not in self.tracking_configs:
            self.tracking_configs[user_id] = TrackingConfig()

        config = self.tracking_configs[user_id]

        for key, value in config_updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # Also update database
        db_updates = {}
        if 'active_interval_seconds' in config_updates:
            db_updates['tracking_interval_active'] = config_updates['active_interval_seconds']
        if 'stationary_interval_seconds' in config_updates:
            db_updates['tracking_interval_stationary'] = config_updates['stationary_interval_seconds']

        if db_updates:
            database.update_user_tracking_settings(user_id, **db_updates)

        return True

    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old location history and cache data."""
        deleted_count = database.cleanup_old_location_history(days_to_keep)
        return {
            'location_history_deleted': deleted_count,
            'days_kept': days_to_keep
        }

    def process_offline_location_update(self, user_id: str, latitude: float, longitude: float,
                                      altitude: Optional[float] = None, accuracy: Optional[float] = None,
                                      battery_level: Optional[int] = None, timestamp: Optional[datetime.datetime] = None) -> Dict:
        """
        Process a location update for offline storage.
        This stores the location data in cache for later syncing.
        """
        try:
            # Store in cache for offline sync
            success = database.insert_location_cache(
                user_id=user_id,
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                accuracy=accuracy,
                battery_level=battery_level
            )

            if not success:
                return {
                    'success': False,
                    'error': 'Failed to store location in cache'
                }

            return {
                'success': True,
                'message': 'Location stored in cache for offline sync',
                'cached': True
            }

        except Exception as e:
            logger.error(f"Error processing offline location update for {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def sync_offline_data(self) -> Dict:
        """
        Sync offline location data to main location history.
        Returns sync statistics.
        """
        try:
            # Get unsynced cache entries
            cache_entries = database.get_unsynced_location_cache(limit=1000)

            if not cache_entries:
                return {
                    'success': True,
                    'synced_count': 0,
                    'message': 'No offline data to sync'
                }

            synced_count = 0
            failed_count = 0

            # Process each cache entry
            for entry in cache_entries:
                try:
                    # Convert cache entry to location point
                    location_point = LocationPoint(
                        latitude=entry['latitude'],
                        longitude=entry['longitude'],
                        altitude=entry['altitude'],
                        accuracy=entry['accuracy'],
                        timestamp=entry['recorded_at']
                    )

                    # Detect motion (simplified for offline sync)
                    is_moving, speed_mps = self.detect_motion(entry['user_id'], location_point)

                    # Insert into main location history
                    success = database.insert_location_history(
                        user_id=entry['user_id'],
                        latitude=entry['latitude'],
                        longitude=entry['longitude'],
                        altitude=entry['altitude'],
                        accuracy=entry['accuracy'],
                        speed=speed_mps,
                        battery_level=entry['battery_level'],
                        is_moving=is_moving
                    )

                    if success:
                        synced_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(f"Error syncing cache entry {entry['id']}: {e}")
                    failed_count += 1

            # Mark successfully synced entries as synced
            if synced_count > 0:
                synced_ids = [entry['id'] for entry in cache_entries[:synced_count]]
                database.mark_location_cache_synced(synced_ids)

            return {
                'success': True,
                'synced_count': synced_count,
                'failed_count': failed_count,
                'total_processed': len(cache_entries)
            }

        except Exception as e:
            logger.error(f"Error during offline data sync: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_offline_queue_status(self) -> Dict:
        """
        Get status of offline location data queue.
        """
        try:
            conn = database.get_connection()
            cursor = conn.cursor()

            # Get total unsynced entries
            cursor.execute('SELECT COUNT(*) as total_unsynced FROM location_cache WHERE synced = FALSE')
            total_unsynced = cursor.fetchone()['total_unsynced']

            # Get oldest entry timestamp
            cursor.execute('SELECT recorded_at FROM location_cache WHERE synced = FALSE ORDER BY recorded_at ASC LIMIT 1')
            oldest_entry = cursor.fetchone()

            # Get entries by user
            cursor.execute('''
                SELECT user_id, COUNT(*) as count
                FROM location_cache
                WHERE synced = FALSE
                GROUP BY user_id
                ORDER BY count DESC
            ''')
            user_counts = cursor.fetchall()

            conn.close()

            return {
                'total_unsynced_entries': total_unsynced,
                'oldest_entry_timestamp': oldest_entry['recorded_at'] if oldest_entry else None,
                'users_with_offline_data': len(user_counts),
                'user_breakdown': [{'user_id': row['user_id'], 'count': row['count']} for row in user_counts]
            }

        except Exception as e:
            logger.error(f"Error getting offline queue status: {e}")
            return {
                'error': str(e)
            }

    def create_zone_alert_rules(self, zone_id: int, rules: Dict[str, Any]) -> bool:
        """
        Create custom alert rules for a zone.
        """
        try:
            conn = database.get_connection()
            cursor = conn.cursor()

            # Store alert rules as JSON in a new table (would need to create this table)
            # For now, we'll store in zone's coordinates field as JSON
            zone = database.get_zone(zone_id)
            if not zone:
                return False

            # Update zone with alert rules
            cursor.execute('''
                UPDATE zones SET coordinates = ? WHERE id = ?
            ''', (json.dumps(rules), zone_id))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error creating zone alert rules: {e}")
            return False

    def check_zone_alert_rules(self, user_id: str, location_point: LocationPoint,
                              zone: Zone, context: Dict[str, Any] = None) -> List[Dict]:
        """
        Check custom alert rules for a zone.
        """
        alerts = []

        try:
            # Get zone alert rules (stored in coordinates field for now)
            if not zone.coordinates:
                return alerts

            rules = json.loads(zone.coordinates)

            # Time-based rules
            if 'time_restrictions' in rules:
                current_time = datetime.datetime.now().time()
                restrictions = rules['time_restrictions']

                if 'allowed_hours' in restrictions:
                    allowed_start = datetime.time.fromisoformat(restrictions['allowed_hours']['start'])
                    allowed_end = datetime.time.fromisoformat(restrictions['allowed_hours']['end'])

                    if not (allowed_start <= current_time <= allowed_end):
                        alerts.append({
                            'type': 'time_restriction_violation',
                            'severity': 'high',
                            'title': f'Zone Time Violation: {zone.name}',
                            'message': f'User {user_id} is in restricted zone outside allowed hours',
                            'zone_id': zone.id
                        })

            # Capacity-based rules
            if 'max_capacity' in rules:
                current_users = len(database.get_users_by_zone(zone.id))
                max_capacity = rules['max_capacity']

                if current_users >= max_capacity:
                    alerts.append({
                        'type': 'capacity_exceeded',
                        'severity': 'high',
                        'title': f'Zone Capacity Exceeded: {zone.name}',
                        'message': f'Zone has reached maximum capacity of {max_capacity} users',
                        'zone_id': zone.id
                    })

            # Speed-based rules
            if 'speed_limits' in rules and context and 'speed_mps' in context:
                speed_limit = rules['speed_limits'].get('max_speed_mps', 15.0)
                if context['speed_mps'] > speed_limit:
                    alerts.append({
                        'type': 'speed_limit_exceeded',
                        'severity': 'medium',
                        'title': f'Speed Limit Violation: {zone.name}',
                        'message': f'User exceeded speed limit of {speed_limit} m/s in zone',
                        'zone_id': zone.id
                    })

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Error checking zone alert rules: {e}")

        return alerts

    def aggregate_zone_statistics(self, zone_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Aggregate comprehensive statistics for a zone over a time period.
        """
        try:
            conn = database.get_connection()
            cursor = conn.cursor()

            stats = {
                'zone_id': zone_id,
                'period_days': days,
                'total_entries': 0,
                'total_exits': 0,
                'unique_users': 0,
                'avg_session_duration': 0,
                'peak_concurrent_users': 0,
                'alerts_by_type': {},
                'alerts_by_severity': {},
                'hourly_activity': {},
                'daily_activity': {},
                'user_activity_patterns': {}
            }

            # Get zone entry/exit alerts
            start_date = datetime.datetime.now() - datetime.timedelta(days=days)
            cursor.execute('''
                SELECT alert_type, COUNT(*) as count, DATE(created_at) as date, strftime('%H', created_at) as hour
                FROM alerts
                WHERE zone_id = ? AND created_at >= ? AND alert_type IN ('zone_entry', 'zone_exit')
                GROUP BY alert_type, date, hour
            ''', (zone_id, start_date.isoformat()))

            activity_data = cursor.fetchall()

            for row in activity_data:
                if row['alert_type'] == 'zone_entry':
                    stats['total_entries'] += row['count']
                else:
                    stats['total_exits'] += row['count']

                date = row['date']
                hour = row['hour']

                if date not in stats['daily_activity']:
                    stats['daily_activity'][date] = {'entries': 0, 'exits': 0}
                if hour not in stats['hourly_activity']:
                    stats['hourly_activity'][hour] = {'entries': 0, 'exits': 0}

                if row['alert_type'] == 'zone_entry':
                    stats['daily_activity'][date]['entries'] += row['count']
                    stats['hourly_activity'][hour]['entries'] += row['count']
                else:
                    stats['daily_activity'][date]['exits'] += row['count']
                    stats['hourly_activity'][hour]['exits'] += row['count']

            # Get unique users
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) as unique_users
                FROM alerts
                WHERE zone_id = ? AND created_at >= ? AND alert_type IN ('zone_entry', 'zone_exit')
            ''', (zone_id, start_date.isoformat()))

            stats['unique_users'] = cursor.fetchone()['unique_users']

            # Get alert statistics
            cursor.execute('''
                SELECT alert_type, severity, COUNT(*) as count
                FROM alerts
                WHERE zone_id = ? AND created_at >= ?
                GROUP BY alert_type, severity
            ''', (zone_id, start_date.isoformat()))

            alert_data = cursor.fetchall()
            for row in alert_data:
                alert_type = row['alert_type']
                severity = row['severity']

                if alert_type not in stats['alerts_by_type']:
                    stats['alerts_by_type'][alert_type] = 0
                if severity not in stats['alerts_by_severity']:
                    stats['alerts_by_severity'][severity] = 0

                stats['alerts_by_type'][alert_type] += row['count']
                stats['alerts_by_severity'][severity] += row['count']

            conn.close()

            # Calculate peak concurrent users (simplified)
            if stats['daily_activity']:
                max_daily = max(stats['daily_activity'].values(),
                              key=lambda x: x['entries'] - x['exits'])
                stats['peak_concurrent_users'] = max_daily['entries'] - max_daily['exits']

            return stats

        except Exception as e:
            logger.error(f"Error aggregating zone statistics: {e}")
            return {'error': str(e)}

    def get_zones_with_statistics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all zones with their current statistics.
        """
        try:
            zones = database.get_all_zones(limit=limit)
            zones_with_stats = []

            for zone_data in zones:
                zone = Zone(**zone_data)

                # Get current users in zone
                users_in_zone = database.get_users_by_zone(zone.id)

                # Get recent alerts
                conn = database.get_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT COUNT(*) as recent_alerts FROM alerts
                    WHERE zone_id = ? AND created_at >= datetime('now', '-24 hours')
                ''', (zone.id,))
                recent_alerts = cursor.fetchone()['recent_alerts']

                cursor.execute('''
                    SELECT COUNT(*) as total_alerts FROM alerts WHERE zone_id = ?
                ''', (zone.id,))
                total_alerts = cursor.fetchone()['total_alerts']

                conn.close()

                # Calculate zone statistics
                zone_stats = self.calculate_zone_statistics(zone)

                zones_with_stats.append({
                    **zone_data,
                    'current_users_count': len(users_in_zone),
                    'recent_alerts_24h': recent_alerts,
                    'total_alerts': total_alerts,
                    'statistics': zone_stats
                })

            return zones_with_stats

        except Exception as e:
            logger.error(f"Error getting zones with statistics: {e}")
            return []

# Alert Priority and Escalation System

class AlertPriority:
    """Alert priority levels and escalation rules."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    PRIORITY_WEIGHTS = {
        LOW: 1,
        MEDIUM: 2,
        HIGH: 3,
        CRITICAL: 4
    }

    ESCALATION_THRESHOLDS = {
        LOW: 300,      # 5 minutes
        MEDIUM: 180,   # 3 minutes
        HIGH: 60,      # 1 minute
        CRITICAL: 30   # 30 seconds
    }

@dataclass
class AlertRule:
    """Represents an alert rule configuration."""
    id: int
    name: str
    description: str
    alert_type: str
    severity: str
    conditions: Dict[str, Any]
    target_groups: List[int]
    escalation_rules: Dict[str, Any]
    is_active: bool
    created_by: int
    created_at: datetime.datetime

@dataclass
class EscalationStep:
    """Represents an escalation step in alert processing."""
    step_number: int
    delay_seconds: int
    notification_channels: List[str]
    target_users: List[str]
    target_groups: List[int]
    message_template: str
    requires_acknowledgment: bool

class AlertManager:
    """Manages alert creation, escalation, and notification."""

    def __init__(self, geolocation_service):
        self.geolocation_service = geolocation_service
        self.active_alerts: Dict[int, Dict] = {}
        self.alert_rules: Dict[int, AlertRule] = {}
        self.escalation_timers: Dict[int, Dict] = {}

    def create_zone_entry_alert(self, user_id: str, zone: Zone, location_point: LocationPoint) -> Optional[int]:
        """Create alert when user enters a zone."""
        return database.create_alert(
            user_id=user_id,
            zone_id=zone.id,
            alert_type='zone_entry',
            title=f'Zone Entry: {zone.name}',
            message=f'User {user_id} entered zone: {zone.name}',
            severity='medium',
            location_latitude=location_point.latitude,
            location_longitude=location_point.longitude
        )

    def create_zone_exit_alert(self, user_id: str, zone: Zone, location_point: LocationPoint) -> Optional[int]:
        """Create alert when user exits a zone."""
        return database.create_alert(
            user_id=user_id,
            zone_id=zone.id,
            alert_type='zone_exit',
            title=f'Zone Exit: {zone.name}',
            message=f'User {user_id} exited zone: {zone.name}',
            severity='medium',
            location_latitude=location_point.latitude,
            location_longitude=location_point.longitude
        )

    def create_speeding_alert(self, user_id: str, speed_mps: float, location_point: LocationPoint) -> Optional[int]:
        """Create alert when user is speeding."""
        speed_kmh = speed_mps * 3.6
        return database.create_alert(
            user_id=user_id,
            zone_id=None,
            alert_type='speeding',
            title='Speed Alert',
            message=f'User speed: {speed_mps:.1f} m/s ({speed_kmh:.1f} km/h)',
            severity='high' if speed_kmh > 80 else 'medium',
            location_latitude=location_point.latitude,
            location_longitude=location_point.longitude
        )

    def create_offline_alert(self, user_id: str, offline_duration_minutes: int) -> Optional[int]:
        """Create alert when user goes offline."""
        severity = 'critical' if offline_duration_minutes > 60 else 'high' if offline_duration_minutes > 30 else 'medium'

        return database.create_alert(
            user_id=user_id,
            zone_id=None,
            alert_type='offline',
            title='User Offline Alert',
            message=f'User has been offline for {offline_duration_minutes} minutes',
            severity=severity
        )

    def create_battery_low_alert(self, user_id: str, battery_level: int, location_point: LocationPoint) -> Optional[int]:
        """Create alert when user has low battery."""
        severity = 'critical' if battery_level < 10 else 'high' if battery_level < 20 else 'medium'

        return database.create_alert(
            user_id=user_id,
            zone_id=None,
            alert_type='battery_low',
            title='Low Battery Alert',
            message=f'User battery level is {battery_level}%',
            severity=severity,
            location_latitude=location_point.latitude,
            location_longitude=location_point.longitude
        )

    def create_group_targeted_alert(self, alert_type: str, title: str, message: str,
                                   target_groups: List[int], severity: str = 'medium',
                                   location_latitude: float = None, location_longitude: float = None) -> List[int]:
        """Create alerts targeted to specific user groups."""
        created_alerts = []

        for group_id in target_groups:
            # Get users in group
            users_in_group = database.get_users_in_group(group_id)

            for user in users_in_group:
                alert_id = database.create_alert(
                    user_id=user['id'],
                    zone_id=None,
                    alert_type=f"group_{alert_type}",
                    title=f"[Group Alert] {title}",
                    message=message,
                    severity=severity,
                    location_latitude=location_latitude,
                    location_longitude=location_longitude
                )
                if alert_id:
                    created_alerts.append(alert_id)

        return created_alerts

    def process_alert_escalation(self, alert_id: int):
        """Process escalation for an alert."""
        alert = database.get_alert(alert_id)
        if not alert or alert.get('is_acknowledged'):
            return

        # Get escalation rules
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT rules FROM alert_escalation_rules WHERE alert_id = ?', (alert_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return

        try:
            escalation_rules = json.loads(row['rules'])
        except json.JSONDecodeError:
            return

        # Calculate time since alert creation
        created_at = datetime.datetime.fromisoformat(alert['created_at'].replace('Z', '+00:00'))
        time_since_creation = (datetime.datetime.now() - created_at.replace(tzinfo=None)).total_seconds()

        # Check each escalation step
        for step_config in escalation_rules.get('steps', []):
            step_number = step_config.get('step_number', 1)
            delay_seconds = step_config.get('delay_seconds', 300)
            notification_channels = step_config.get('channels', ['websocket'])
            target_groups = step_config.get('target_groups', [])
            target_users = step_config.get('target_users', [])

            if time_since_creation >= delay_seconds:
                self.execute_escalation_step(alert_id, step_config)

    def execute_escalation_step(self, alert_id: int, step_config: Dict):
        """Execute a single escalation step."""
        alert = database.get_alert(alert_id)
        if not alert:
            return

        # Send notifications via specified channels
        message = step_config.get('message_template', alert['message'])
        notification_channels = step_config.get('channels', ['websocket'])

        for channel in notification_channels:
            if channel == 'websocket':
                self.send_websocket_notification(alert, message, step_config)
            elif channel == 'email':
                self.send_email_notification(alert, message, step_config)
            elif channel == 'sms':
                self.send_sms_notification(alert, message, step_config)

        # Log the escalation
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO alert_escalation_log (alert_id, step_number, executed_at, channels, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            alert_id,
            step_config.get('step_number', 1),
            datetime.datetime.now(),
            json.dumps(notification_channels),
            message
        ))

        conn.commit()
        conn.close()

    def send_websocket_notification(self, alert: Dict, message: str, step_config: Dict):
        """Send alert notification via WebSocket."""
        # This would integrate with the existing WebSocket system
        # For now, we'll just log it
        logger.info(f"WebSocket notification for alert {alert['id']}: {message}")

    def send_email_notification(self, alert: Dict, message: str, step_config: Dict):
        """Send alert notification via email."""
        # This would integrate with an email service
        # For now, we'll just log it
        logger.info(f"Email notification for alert {alert['id']}: {message}")

    def send_sms_notification(self, alert: Dict, message: str, step_config: Dict):
        """Send alert notification via SMS."""
        # This would integrate with an SMS service
        # For now, we'll just log it
        logger.info(f"SMS notification for alert {alert['id']}: {message}")

    def check_and_escalate_alerts(self):
        """Check all active alerts and process escalations."""
        conn = database.get_connection()
        cursor = conn.cursor()

        # Get unacknowledged alerts older than threshold
        threshold_time = datetime.datetime.now() - datetime.timedelta(minutes=1)

        cursor.execute('''
            SELECT id FROM alerts
            WHERE is_acknowledged = FALSE AND created_at < ?
        ''', (threshold_time,))

        unacknowledged_alerts = cursor.fetchall()
        conn.close()

        for row in unacknowledged_alerts:
            self.process_alert_escalation(row['id'])

    def get_alert_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive alert statistics."""
        conn = database.get_connection()
        cursor = conn.cursor()

        stats = {
            'period_days': days,
            'total_alerts': 0,
            'alerts_by_type': {},
            'alerts_by_severity': {},
            'alerts_by_zone': {},
            'avg_resolution_time': 0,
            'escalation_stats': {},
            'group_alert_stats': {}
        }

        # Get basic alert counts
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)

        cursor.execute('''
            SELECT COUNT(*) as total FROM alerts WHERE created_at >= ?
        ''', (start_date,))
        stats['total_alerts'] = cursor.fetchone()['total']

        # Get alerts by type
        cursor.execute('''
            SELECT alert_type, COUNT(*) as count FROM alerts
            WHERE created_at >= ? GROUP BY alert_type ORDER BY count DESC
        ''', (start_date,))
        stats['alerts_by_type'] = {row['alert_type']: row['count'] for row in cursor.fetchall()}

        # Get alerts by severity
        cursor.execute('''
            SELECT severity, COUNT(*) as count FROM alerts
            WHERE created_at >= ? GROUP BY severity ORDER BY count DESC
        ''', (start_date,))
        stats['alerts_by_severity'] = {row['severity']: row['count'] for row in cursor.fetchall()}

        # Get alerts by zone
        cursor.execute('''
            SELECT z.name, COUNT(*) as count FROM alerts a
            LEFT JOIN zones z ON a.zone_id = z.id
            WHERE a.created_at >= ? GROUP BY z.id, z.name ORDER BY count DESC
        ''', (start_date,))
        stats['alerts_by_zone'] = {row['name']: row['count'] for row in cursor.fetchall()}

        # Get average resolution time
        cursor.execute('''
            SELECT AVG(CAST((julianday(resolved_at) - julianday(created_at)) * 24 * 60 * 60 AS INTEGER)) as avg_seconds
            FROM alerts WHERE is_resolved = TRUE AND resolved_at IS NOT NULL AND created_at >= ?
        ''', (start_date,))
        avg_seconds = cursor.fetchone()['avg_seconds']
        stats['avg_resolution_time'] = avg_seconds if avg_seconds else 0

        conn.close()

        return stats

# Enhanced GeolocationService with Alert Integration

class EnhancedGeolocationService(GeolocationService):
    """Enhanced geolocation service with alert management integration."""

    def __init__(self):
        super().__init__()
        self.alert_manager = AlertManager(self)
        self.custom_alert_rules: Dict[int, Dict] = {}

    def process_location_update_enhanced(self, user_id: str, latitude: float, longitude: float,
                                       altitude: Optional[float] = None, accuracy: Optional[float] = None,
                                       battery_level: Optional[int] = None) -> Dict:
        """
        Enhanced location update processing with comprehensive alert management.
        """
        # Process basic location update
        basic_result = self.process_location_update(
            user_id, latitude, longitude, altitude, accuracy, battery_level
        )

        # Get user and location data
        user = database.get_user(user_id)
        if not user:
            return {**basic_result, 'alerts': []}

        # Create location point for enhanced processing
        current_time = datetime.datetime.now()
        location_point = LocationPoint(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            accuracy=accuracy,
            timestamp=current_time
        )

        # Check for offline status
        if user.get('last_location_update'):
            last_update = datetime.datetime.fromisoformat(user['last_location_update'].replace('Z', '+00:00'))
            offline_duration = (current_time - last_update.replace(tzinfo=None)).total_seconds()

            # Create offline alert if user was offline for more than 15 minutes
            if offline_duration > 900:  # 15 minutes
                offline_alert = self.alert_manager.create_offline_alert(user_id, int(offline_duration / 60))
                if offline_alert:
                    basic_result['alerts'].append({
                        'id': offline_alert,
                        'type': 'offline',
                        'duration_minutes': int(offline_duration / 60)
                    })

        # Check battery level
        if battery_level and battery_level < 25:
            battery_alert = self.alert_manager.create_battery_low_alert(user_id, battery_level, location_point)
            if battery_alert:
                basic_result['alerts'].append({
                    'id': battery_alert,
                    'type': 'battery_low',
                    'battery_level': battery_level
                })

        # Check custom alert rules
        custom_alerts = self.check_custom_alert_rules(user_id, location_point, basic_result)
        basic_result['alerts'].extend(custom_alerts)

        # Process alert escalations
        for alert_info in basic_result['alerts']:
            if 'id' in alert_info:
                self.alert_manager.process_alert_escalation(alert_info['id'])

        return basic_result

    def check_custom_alert_rules(self, user_id: str, location_point: LocationPoint, context: Dict) -> List[Dict]:
        """Check custom alert rules for the user."""
        custom_alerts = []

        # Get user's groups
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT group_id FROM user_group_members WHERE user_id = ?
        ''', (user_id,))

        user_groups = [row['group_id'] for row in cursor.fetchall()]
        conn.close()

        # Check each custom rule
        for rule_id, rule_config in self.custom_alert_rules.items():
            if not rule_config.get('is_active', False):
                continue

            # Check if rule applies to user's groups
            rule_groups = rule_config.get('target_groups', [])
            if rule_groups and not any(group in user_groups for group in rule_groups):
                continue

            # Check rule conditions
            if self.evaluate_alert_rule_conditions(rule_config.get('conditions', {}), context):
                alert = self.create_custom_alert(user_id, rule_config, location_point)
                if alert:
                    custom_alerts.append(alert)

        return custom_alerts

    def evaluate_alert_rule_conditions(self, conditions: Dict, context: Dict) -> bool:
        """Evaluate conditions for a custom alert rule."""
        if not conditions:
            return True

        for condition_type, condition_value in conditions.items():
            if condition_type == 'min_speed_mps' and context.get('speed_mps', 0) < condition_value:
                return False
            elif condition_type == 'max_speed_mps' and context.get('speed_mps', 0) > condition_value:
                return False
            elif condition_type == 'zone_entry' and not context.get('zone_changes', {}).get('zone_entered', False):
                return False
            elif condition_type == 'zone_exit' and not context.get('zone_changes', {}).get('zone_exited', False):
                return False
            elif condition_type == 'battery_level' and context.get('battery_level', 100) > condition_value:
                return False

        return True

    def create_custom_alert(self, user_id: str, rule_config: Dict, location_point: LocationPoint) -> Optional[Dict]:
        """Create a custom alert based on rule configuration."""
        alert_id = database.create_alert(
            user_id=user_id,
            zone_id=None,
            alert_type=rule_config.get('alert_type', 'custom'),
            title=rule_config.get('title', 'Custom Alert'),
            message=rule_config.get('message', 'Custom alert triggered'),
            severity=rule_config.get('severity', 'medium'),
            location_latitude=location_point.latitude,
            location_longitude=location_point.longitude
        )

        if alert_id:
            return {
                'id': alert_id,
                'type': 'custom',
                'rule_name': rule_config.get('name', 'Unknown Rule')
            }

        return None

    def add_custom_alert_rule(self, rule_config: Dict) -> int:
        """Add a custom alert rule."""
        rule_id = len(self.custom_alert_rules) + 1
        self.custom_alert_rules[rule_id] = rule_config
        return rule_id

    def remove_custom_alert_rule(self, rule_id: int) -> bool:
        """Remove a custom alert rule."""
        if rule_id in self.custom_alert_rules:
            del self.custom_alert_rules[rule_id]
            return True
        return False

    def get_group_alert_summary(self, group_id: int, days: int = 7) -> Dict[str, Any]:
        """Get alert summary for a specific user group."""
        users_in_group = database.get_users_in_group(group_id)

        if not users_in_group:
            return {'group_id': group_id, 'user_count': 0, 'alerts': {}}

        user_ids = [user['id'] for user in users_in_group]

        conn = database.get_connection()
        cursor = conn.cursor()

        # Get alerts for users in group
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)

        placeholders = ','.join(['?'] * len(user_ids))
        cursor.execute(f'''
            SELECT alert_type, severity, COUNT(*) as count
            FROM alerts
            WHERE user_id IN ({placeholders}) AND created_at >= ?
            GROUP BY alert_type, severity
        ''', user_ids + [start_date])

        alerts_by_type = {}
        for row in cursor.fetchall():
            alert_type = row['alert_type']
            severity = row['severity']
            if alert_type not in alerts_by_type:
                alerts_by_type[alert_type] = {}
            alerts_by_type[alert_type][severity] = row['count']

        conn.close()

        return {
            'group_id': group_id,
            'user_count': len(users_in_group),
            'period_days': days,
            'alerts_by_type': alerts_by_type
        }

# Global instances
geolocation_service = GeolocationService()
enhanced_geolocation_service = EnhancedGeolocationService()
alert_manager = AlertManager(geolocation_service)