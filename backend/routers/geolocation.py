from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime
import json

from backend import database, auth
from backend.geolocation import geolocation_service

router = APIRouter()

# Pydantic Models
class LocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    battery_level: Optional[int] = Field(None, ge=0, le=100)

class LocationResponse(BaseModel):
    success: bool
    is_moving: bool
    speed_mps: float
    zone_changes: Dict
    alerts: List[Dict]
    update_data: Dict

class LocationHistoryResponse(BaseModel):
    user_id: str
    latitude: float
    longitude: float
    altitude: Optional[float]
    accuracy: Optional[float]
    speed: Optional[float]
    heading: Optional[float]
    battery_level: Optional[int]
    is_moving: bool
    recorded_at: str

class UserLocationSummary(BaseModel):
    user_id: str
    current_location: Dict
    current_zone: Optional[Dict]
    tracking_enabled: bool
    tracking_config: Dict
    motion_state: bool
    recent_history_count: int
    device_status: str

class TrackingConfigUpdate(BaseModel):
    active_interval_seconds: Optional[int] = Field(None, gt=0)
    stationary_interval_seconds: Optional[int] = Field(None, gt=0)
    motion_threshold_mps: Optional[float] = Field(None, gt=0)

# API Endpoints

@router.post("/location/update", response_model=LocationResponse)
async def update_location(
    user_id: str,
    location: LocationUpdate,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Update user location and process geolocation data.
    This endpoint receives location updates from user devices.
    """
    try:
        result = geolocation_service.process_location_update(
            user_id=user_id,
            latitude=location.latitude,
            longitude=location.longitude,
            altitude=location.altitude,
            accuracy=location.accuracy,
            battery_level=location.battery_level
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail="Failed to process location update")

        return LocationResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing location update: {str(e)}")

@router.get("/location/summary/{user_id}", response_model=UserLocationSummary)
async def get_user_location_summary(
    user_id: str,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Get comprehensive location summary for a user.
    """
    try:
        summary = geolocation_service.get_user_location_summary(user_id)

        if 'error' in summary:
            raise HTTPException(status_code=404, detail=summary['error'])

        return UserLocationSummary(**summary)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting location summary: {str(e)}")

@router.get("/location/history/{user_id}")
async def get_location_history(
    user_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Get location history for a user with optional time filtering.
    """
    try:
        # Parse datetime strings if provided
        start_dt = None
        end_dt = None

        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format")

        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format")

        history = database.get_location_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
            start_time=start_dt,
            end_time=end_dt
        )

        # Convert to response format
        response_data = []
        for record in history:
            response_data.append(LocationHistoryResponse(
                user_id=record['user_id'],
                latitude=record['latitude'],
                longitude=record['longitude'],
                altitude=record['altitude'],
                accuracy=record['accuracy'],
                speed=record['speed'],
                heading=record['heading'],
                battery_level=record['battery_level'],
                is_moving=record['is_moving'],
                recorded_at=record['recorded_at']
            ))

        return {
            "user_id": user_id,
            "count": len(response_data),
            "limit": limit,
            "offset": offset,
            "history": response_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting location history: {str(e)}")

@router.post("/tracking/config/{user_id}")
async def update_tracking_config(
    user_id: str,
    config: TrackingConfigUpdate,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Update tracking configuration for a user.
    """
    try:
        # Filter out None values
        config_updates = {k: v for k, v in config.dict().items() if v is not None}

        if not config_updates:
            raise HTTPException(status_code=400, detail="No valid configuration updates provided")

        success = geolocation_service.update_user_tracking_config(user_id, **config_updates)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update tracking configuration")

        return {
            "success": True,
            "message": "Tracking configuration updated successfully",
            "user_id": user_id,
            "updates": config_updates
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating tracking config: {str(e)}")

@router.get("/tracking/config/{user_id}")
async def get_tracking_config(
    user_id: str,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Get current tracking configuration for a user.
    """
    try:
        summary = geolocation_service.get_user_location_summary(user_id)

        if 'error' in summary:
            raise HTTPException(status_code=404, detail=summary['error'])

        return {
            "user_id": user_id,
            "tracking_config": summary['tracking_config'],
            "tracking_enabled": summary['tracking_enabled']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tracking config: {str(e)}")

@router.post("/cleanup")
async def cleanup_old_data(
    days_to_keep: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Clean up old location history data.
    Admin endpoint for maintenance.
    """
    try:
        result = geolocation_service.cleanup_old_data(days_to_keep)

        return {
            "success": True,
            "message": f"Cleanup completed successfully",
            "result": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")

@router.get("/stats")
async def get_geolocation_stats(
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Get geolocation system statistics.
    """
    try:
        # Get basic stats
        conn = database.get_connection()

        # Count location history records
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as history_count FROM location_history')
        history_count = cursor.fetchone()['history_count']

        # Count active zones
        cursor.execute('SELECT COUNT(*) as zones_count FROM zones WHERE is_active = TRUE')
        zones_count = cursor.fetchone()['zones_count']

        # Count active alerts
        cursor.execute('SELECT COUNT(*) as alerts_count FROM alerts WHERE is_acknowledged = FALSE')
        alerts_count = cursor.fetchone()['alerts_count']

        # Count users with tracking enabled
        cursor.execute('SELECT COUNT(*) as tracking_users FROM users WHERE tracking_enabled = TRUE')
        tracking_users = cursor.fetchone()['tracking_users']

        # Count cache entries
        cursor.execute('SELECT COUNT(*) as cache_count FROM location_cache WHERE synced = FALSE')
        cache_count = cursor.fetchone()['cache_count']

        conn.close()

        return {
            "location_history_records": history_count,
            "active_zones": zones_count,
            "pending_alerts": alerts_count,
            "users_with_tracking": tracking_users,
            "unsynced_cache_entries": cache_count,
            "tracked_users": len(geolocation_service.user_locations),
            "users_with_motion_data": len(geolocation_service.user_motion_state)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

# WebSocket broadcast functions for real-time updates
async def broadcast_location_update(user_id: str, location_data: Dict):
    """Broadcast location update to WebSocket clients."""
    from backend.routers.websocket import broadcast_update

    await broadcast_update("location_update", {
        "user_id": user_id,
        "location": location_data,
        "timestamp": datetime.now().isoformat()
    })

async def broadcast_zone_change(user_id: str, zone_change: Dict):
    """Broadcast zone change to WebSocket clients."""
    from backend.routers.websocket import broadcast_update

    await broadcast_update("zone_change", {
        "user_id": user_id,
        "zone_change": zone_change,
        "timestamp": datetime.now().isoformat()
    })

async def broadcast_new_alert(alert: Dict):
    """Broadcast new alert to WebSocket clients."""
    from backend.routers.websocket import broadcast_update

    await broadcast_update("new_alert", {
        "alert": alert,
        "timestamp": datetime.now().isoformat()
    })

@router.post("/offline/sync")
async def sync_offline_data(
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Sync offline location data to main database.
    """
    try:
        result = geolocation_service.sync_offline_data()

        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', 'Sync failed'))

        return {
            "success": True,
            "message": "Offline data sync completed",
            "result": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing offline data: {str(e)}")

@router.get("/offline/status")
async def get_offline_status(
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Get status of offline location data queue.
    """
    try:
        status = geolocation_service.get_offline_queue_status()

        if 'error' in status:
            raise HTTPException(status_code=500, detail=status['error'])

        return {
            "success": True,
            "offline_status": status
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting offline status: {str(e)}")

@router.post("/offline/location")
async def store_offline_location(
    user_id: str,
    latitude: float,
    longitude: float,
    altitude: Optional[float] = None,
    accuracy: Optional[float] = None,
    battery_level: Optional[int] = None,
    timestamp: Optional[str] = None,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Store location data for offline sync.
    """
    try:
        # Parse timestamp if provided
        timestamp_dt = None
        if timestamp:
            try:
                timestamp_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid timestamp format")

        result = geolocation_service.process_offline_location_update(
            user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            accuracy=accuracy,
            battery_level=battery_level,
            timestamp=timestamp_dt
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to store offline location'))

        return {
            "success": True,
            "message": result.get('message', 'Location stored for offline sync'),
            "cached": result.get('cached', True)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing offline location: {str(e)}")

@router.get("/analytics/heatmap")
async def get_location_heatmap(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get location heatmap data for visualization."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        heatmap_data = database.get_location_heatmap_data(days)

        return {
            "period_days": days,
            "data_points": len(heatmap_data),
            "heatmap_data": heatmap_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting heatmap data: {str(e)}")

@router.get("/analytics/dwell-time")
async def get_zone_dwell_times(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get zone dwell time analytics."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        dwell_times = database.get_zone_dwell_times(days)

        return {
            "period_days": days,
            "zones": len(dwell_times),
            "dwell_times": dwell_times
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting dwell times: {str(e)}")

@router.get("/analytics/movement-patterns")
async def get_movement_patterns(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get movement pattern analytics."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        movement_patterns = database.get_movement_patterns(days)

        return {
            "period_days": days,
            "users_analyzed": len(movement_patterns),
            "movement_patterns": movement_patterns
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting movement patterns: {str(e)}")

@router.get("/analytics/predictive")
async def get_predictive_analytics(
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get predictive analytics for location patterns."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        predictions = database.get_location_predictions()

        return {
            "predictions": predictions,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting predictive analytics: {str(e)}")

@router.get("/analytics/speed-analysis")
async def get_speed_analysis(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get speed analysis for users."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        speed_analysis = database.get_speed_analysis(days)

        return {
            "period_days": days,
            "speed_categories": speed_analysis
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting speed analysis: {str(e)}")

@router.get("/analytics/zone/{zone_id}")
async def get_zone_analytics(
    zone_id: int,
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get detailed analytics for a specific zone."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        zone_stats = geolocation_service.aggregate_zone_statistics(zone_id, days)

        if 'error' in zone_stats:
            raise HTTPException(status_code=404, detail=zone_stats['error'])

        return {
            "zone_id": zone_id,
            "period_days": days,
            "analytics": zone_stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting zone analytics: {str(e)}")

@router.get("/analytics/motion-detection")
async def get_motion_detection_stats(
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get motion detection statistics."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        motion_stats = {
            "total_users_tracked": len(geolocation_service.user_locations),
            "users_in_motion": len([uid for uid, motion in geolocation_service.user_motion_state.items() if motion]),
            "motion_threshold_mps": geolocation_service.tracking_configs.get('default', {}).get('motion_threshold_mps', 2.0),
            "active_tracking_configs": len(geolocation_service.tracking_configs)
        }

        return motion_stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting motion detection stats: {str(e)}")

@router.post("/analytics/zone-alert-rules/{zone_id}")
async def create_zone_alert_rules(
    zone_id: int,
    rules: Dict,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Create custom alert rules for a zone."""
    try:
        success = geolocation_service.create_zone_alert_rules(zone_id, rules)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to create zone alert rules")

        return {
            "success": True,
            "message": "Zone alert rules created successfully",
            "zone_id": zone_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating zone alert rules: {str(e)}")

@router.get("/analytics/zones-with-stats")
async def get_zones_with_statistics(
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get all zones with their current statistics."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        zones_with_stats = geolocation_service.get_zones_with_statistics(limit)

        return {
            "count": len(zones_with_stats),
            "zones": zones_with_stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting zones with statistics: {str(e)}")