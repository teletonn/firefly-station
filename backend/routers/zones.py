from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import csv
import io
from collections import defaultdict

from backend import database, auth

router = APIRouter()

# Pydantic Models
class ZoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    center_latitude: float = Field(..., ge=-90, le=90)
    center_longitude: float = Field(..., ge=-180, le=180)
    radius_meters: float = Field(..., gt=0, le=100000)  # Max 100km radius
    zone_type: str = Field('circular', pattern='^(circular|polygon)$')

class ZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    center_latitude: Optional[float] = Field(None, ge=-90, le=90)
    center_longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius_meters: Optional[float] = Field(None, gt=0, le=100000)
    zone_type: Optional[str] = Field(None, pattern='^(circular|polygon)$')
    is_active: Optional[bool] = None

class ZoneResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    center_latitude: float
    center_longitude: float
    radius_meters: float
    zone_type: str
    coordinates: Optional[str]
    is_active: bool
    created_by: Optional[int]
    created_by_username: Optional[str]
    created_at: str
    updated_at: str

class UserGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class UserGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: Optional[int]
    created_by_username: Optional[str]
    created_at: str
    updated_at: str
    member_count: int

class AlertResponse(BaseModel):
    id: int
    user_id: Optional[str]
    zone_id: Optional[int]
    alert_type: str
    severity: str
    title: str
    message: str
    location_latitude: Optional[float]
    location_longitude: Optional[float]
    is_acknowledged: bool
    acknowledged_by: Optional[int]
    acknowledged_by_username: Optional[str]
    acknowledged_at: Optional[str]
    is_resolved: bool
    resolved_by: Optional[int]
    created_at: str
    user_name: Optional[str]
    zone_name: Optional[str]

class BulkZoneCreate(BaseModel):
    zones: List[ZoneCreate]

class BulkZoneResponse(BaseModel):
    success_count: int
    failure_count: int
    errors: List[Dict[str, Any]]
    created_zones: List[ZoneResponse]

class ZoneAnalytics(BaseModel):
    zone_id: int
    zone_name: str
    total_users_entered: int
    total_users_exited: int
    current_users_inside: int
    total_alerts: int
    alerts_last_24h: int
    alerts_last_7d: int
    avg_time_spent_minutes: Optional[float]
    peak_concurrent_users: int
    created_at: str
    is_active: bool

class ZoneStatistics(BaseModel):
    total_zones: int
    active_zones: int
    zones_by_type: Dict[str, int]
    total_alerts: int
    alerts_by_severity: Dict[str, int]
    alerts_by_type: Dict[str, int]
    most_active_zones: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]

class ZoneStatsResponse(BaseModel):
    total: int
    active_zones: int
    avg_users_per_zone: float

class ZoneImportExport(BaseModel):
    format: str = Field('json', pattern='^(json|csv|geojson)$')
    include_history: bool = False
    date_range: Optional[Dict[str, str]] = None

# Zone Management Endpoints

@router.post("", response_model=ZoneResponse)
async def create_zone(
    zone: ZoneCreate,
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Create a new geographic zone.
    """
    try:
        zone_id = database.create_zone(
            name=zone.name,
            description=zone.description,
            center_latitude=zone.center_latitude,
            center_longitude=zone.center_longitude,
            radius_meters=zone.radius_meters,
            zone_type=zone.zone_type,
            created_by=current_user.get('id')
        )

        if not zone_id:
            raise HTTPException(status_code=400, detail="Failed to create zone")

        # Get the created zone for response
        created_zone = database.get_zone(zone_id)
        if not created_zone:
            raise HTTPException(status_code=500, detail="Zone created but failed to retrieve")

        # Add creator username
        if created_zone['created_by']:
            admin_user = database.get_admin_user_by_id(created_zone['created_by'])
            created_zone['created_by_username'] = admin_user['username'] if admin_user else None

        return ZoneResponse(**created_zone)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating zone: {str(e)}")

@router.get("", response_model=List[ZoneResponse])
async def get_zones(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    include_inactive: bool = Query(False),
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Get all zones with optional filtering.
    """
    try:
        if include_inactive:
            # Get all zones including inactive
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT z.*, a.username as created_by_username
                FROM zones z
                LEFT JOIN admin_users a ON z.created_by = a.id
                ORDER BY z.created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            zones = cursor.fetchall()
            conn.close()
            zones = [dict(row) for row in zones]
        else:
            # Get only active zones
            zones = database.get_all_zones(limit=limit, offset=offset)

        return [ZoneResponse(**zone) for zone in zones]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting zones: {str(e)}")

@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: int,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Get a specific zone by ID.
    """
    if not auth.check_permission(current_user, "zones:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        zone = database.get_zone(zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")

        # Add creator username
        if zone['created_by']:
            admin_user = database.get_admin_user_by_id(zone['created_by'])
            zone['created_by_username'] = admin_user['username'] if admin_user else None

        return ZoneResponse(**zone)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting zone: {str(e)}")

@router.put("/{zone_id}", response_model=ZoneResponse)
async def update_zone(
    zone_id: int,
    zone_update: ZoneUpdate,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Update a zone.
    """
    if not auth.check_permission(current_user, "zones"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        # Filter out None values
        update_data = {k: v for k, v in zone_update.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid updates provided")

        success = database.update_zone(zone_id, **update_data)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update zone")

        # Get updated zone
        updated_zone = database.get_zone(zone_id)
        if not updated_zone:
            raise HTTPException(status_code=404, detail="Zone not found after update")

        # Add creator username
        if updated_zone['created_by']:
            admin_user = database.get_admin_user_by_id(updated_zone['created_by'])
            updated_zone['created_by_username'] = admin_user['username'] if admin_user else None

        return ZoneResponse(**updated_zone)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating zone: {str(e)}")

@router.delete("/{zone_id}")
async def delete_zone(
    zone_id: int,
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Soft delete a zone (mark as inactive).
    """
    try:
        success = database.delete_zone(zone_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete zone")

        return {
            "success": True,
            "message": f"Zone {zone_id} has been deactivated",
            "zone_id": zone_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting zone: {str(e)}")

# User Group Management Endpoints

@router.post("/groups", response_model=UserGroupResponse)
async def create_user_group(
    group: UserGroupCreate,
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Create a new user group.
    """
    try:
        group_id = database.create_user_group(
            name=group.name,
            description=group.description,
            created_by=current_user.get('id')
        )

        if not group_id:
            raise HTTPException(status_code=400, detail="Failed to create user group")

        # Get the created group
        created_group = database.get_user_group(group_id)
        if not created_group:
            raise HTTPException(status_code=500, detail="Group created but failed to retrieve")

        # Add creator username and member count
        if created_group['created_by']:
            admin_user = database.get_admin_user_by_id(created_group['created_by'])
            created_group['created_by_username'] = admin_user['username'] if admin_user else None

        # Get member count
        members = database.get_users_in_group(group_id)
        created_group['member_count'] = len(members)

        return UserGroupResponse(**created_group)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user group: {str(e)}")

@router.get("/groups", response_model=List[UserGroupResponse])
async def get_user_groups(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Get all user groups.
    """
    try:
        groups = database.get_all_user_groups(limit=limit, offset=offset)

        # Add member counts and creator usernames
        for group in groups:
            if group['created_by']:
                admin_user = database.get_admin_user_by_id(group['created_by'])
                group['created_by_username'] = admin_user['username'] if admin_user else None

            members = database.get_users_in_group(group['id'])
            group['member_count'] = len(members)

        return [UserGroupResponse(**group) for group in groups]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user groups: {str(e)}")

@router.post("/groups/{group_id}/users/{user_id}")
async def add_user_to_group(
    group_id: int,
    user_id: str,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Add a user to a group.
    """
    if not auth.check_permission(current_user, "zones"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        success = database.add_user_to_group(user_id, group_id, current_user.get('id'))
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add user to group")

        return {
            "success": True,
            "message": f"User {user_id} added to group {group_id}",
            "user_id": user_id,
            "group_id": group_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding user to group: {str(e)}")

@router.delete("/groups/{group_id}/users/{user_id}")
async def remove_user_from_group(
    group_id: int,
    user_id: str,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Remove a user from a group.
    """
    if not auth.check_permission(current_user, "zones"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        success = database.remove_user_from_group(user_id, group_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to remove user from group")

        return {
            "success": True,
            "message": f"User {user_id} removed from group {group_id}",
            "user_id": user_id,
            "group_id": group_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing user from group: {str(e)}")

@router.get("/groups/{group_id}/users")
async def get_group_users(
    group_id: int,
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Get all users in a group.
    """
    try:
        users = database.get_users_in_group(group_id)

        return {
            "group_id": group_id,
            "count": len(users),
            "users": users
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting group users: {str(e)}")

# Alert Management Endpoints

@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    include_acknowledged: bool = Query(False),
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Get all alerts with optional filtering.
    """
    try:
        alerts = database.get_all_alerts(limit=limit, offset=offset, include_acknowledged=include_acknowledged)

        # Add usernames and zone names
        for alert in alerts:
            if alert['acknowledged_by']:
                admin_user = database.get_admin_user_by_id(alert['acknowledged_by'])
                alert['acknowledged_by_username'] = admin_user['username'] if admin_user else None

            if alert['user_id']:
                user = database.get_user(alert['user_id'])
                alert['user_name'] = user['long_name'] if user else None

            if alert['zone_id']:
                zone = database.get_zone(alert['zone_id'])
                alert['zone_name'] = zone['name'] if zone else None

        return [AlertResponse(**alert) for alert in alerts]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting alerts: {str(e)}")

@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """
    Acknowledge an alert.
    """
    if not auth.check_permission(current_user, "zones"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        success = database.acknowledge_alert(alert_id, current_user.get('id'))
        if not success:
            raise HTTPException(status_code=400, detail="Failed to acknowledge alert")

        return {
            "success": True,
            "message": f"Alert {alert_id} acknowledged",
            "alert_id": alert_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error acknowledging alert: {str(e)}")

@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Resolve an alert.
    """
    try:
        success = database.resolve_alert(alert_id, current_user.get('id'))
        if not success:
            raise HTTPException(status_code=400, detail="Failed to resolve alert")

        return {
            "success": True,
            "message": f"Alert {alert_id} resolved",
            "alert_id": alert_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving alert: {str(e)}")

# Zone Statistics Endpoints

@router.get("/stats", response_model=ZoneStatsResponse)
async def get_zones_stats(current_user: dict = Depends(auth.get_current_active_user)):
    """Get overall zones statistics."""
    if not auth.check_permission(current_user, "zones:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"get_zones_stats called by user: {current_user.get('id')}")

    try:
        stats = database.get_zone_stats()
        logger.info(f"get_zone_stats returned: {stats}")
        logger.info(f"Stats types - total: {type(stats.get('total'))}, active: {type(stats.get('active'))}, avg_users: {type(stats.get('avg_users_per_zone'))}")
        return ZoneStatsResponse(
            total=stats['total'],
            active_zones=stats['active'],
            avg_users_per_zone=stats['avg_users_per_zone']
        )
    except Exception as e:
        logger.error(f"Error in get_zones_stats: {str(e)}")
        raise

@router.get("/{zone_id}/stats")
async def get_zone_stats(
    zone_id: int,
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Get statistics for a specific zone.
    """
    try:
        zone = database.get_zone(zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")

        # Get users currently in zone
        users_in_zone = database.get_users_by_zone(zone_id)

        # Get recent alerts for this zone
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) as alert_count FROM alerts
            WHERE zone_id = ? AND created_at >= datetime('now', '-24 hours')
        ''', (zone_id,))
        recent_alerts = cursor.fetchone()['alert_count']

        cursor.execute('''
            SELECT COUNT(*) as total_alerts FROM alerts WHERE zone_id = ?
        ''', (zone_id,))
        total_alerts = cursor.fetchone()['total_alerts']

        conn.close()

        return {
            "zone_id": zone_id,
            "zone_name": zone['name'],
            "users_currently_in_zone": len(users_in_zone),
            "recent_alerts_24h": recent_alerts,
            "total_alerts": total_alerts,
            "zone_created": zone['created_at'],
            "is_active": zone['is_active']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting zone stats: {str(e)}")

# Bulk Zone Operations

@router.post("/bulk", response_model=BulkZoneResponse)
async def bulk_create_zones(
    bulk_data: BulkZoneCreate,
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Create multiple zones in a single operation.
    """
    try:
        success_count = 0
        failure_count = 0
        errors = []
        created_zones = []

        for i, zone_data in enumerate(bulk_data.zones):
            try:
                zone_id = database.create_zone(
                    name=zone_data.name,
                    description=zone_data.description,
                    center_latitude=zone_data.center_latitude,
                    center_longitude=zone_data.center_longitude,
                    radius_meters=zone_data.radius_meters,
                    zone_type=zone_data.zone_type,
                    created_by=current_user.get('id')
                )

                if zone_id:
                    # Get the created zone for response
                    created_zone = database.get_zone(zone_id)
                    if created_zone:
                        # Add creator username
                        if created_zone['created_by']:
                            admin_user = database.get_admin_user_by_id(created_zone['created_by'])
                            created_zone['created_by_username'] = admin_user['username'] if admin_user else None

                        created_zones.append(ZoneResponse(**created_zone))
                        success_count += 1
                    else:
                        failure_count += 1
                        errors.append({
                            "index": i,
                            "error": "Zone created but failed to retrieve"
                        })
                else:
                    failure_count += 1
                    errors.append({
                        "index": i,
                        "error": "Failed to create zone"
                    })

            except Exception as e:
                failure_count += 1
                errors.append({
                    "index": i,
                    "error": str(e)
                })

        return BulkZoneResponse(
            success_count=success_count,
            failure_count=failure_count,
            errors=errors,
            created_zones=created_zones
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in bulk zone creation: {str(e)}")

@router.post("/bulk-delete")
async def bulk_delete_zones(
    zone_ids: List[int],
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Delete multiple zones in a single operation.
    """
    try:
        success_count = 0
        failure_count = 0
        errors = []

        for zone_id in zone_ids:
            try:
                success = database.delete_zone(zone_id)
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                    errors.append({
                        "zone_id": zone_id,
                        "error": "Failed to delete zone"
                    })
            except Exception as e:
                failure_count += 1
                errors.append({
                    "zone_id": zone_id,
                    "error": str(e)
                })

        return {
            "success": True,
            "message": f"Successfully deleted {success_count} zones, {failure_count} failed",
            "success_count": success_count,
            "failure_count": failure_count,
            "errors": errors
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in bulk zone deletion: {str(e)}")

@router.post("/bulk-update")
async def bulk_update_zones(
    updates: List[Dict[str, Any]],
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Update multiple zones in a single operation.
    Expected format: [{"id": 1, "updates": {...}}, {"id": 2, "updates": {...}}]
    """
    try:
        success_count = 0
        failure_count = 0
        errors = []

        for update_item in updates:
            zone_id = update_item.get('id')
            zone_updates = update_item.get('updates', {})

            if not zone_id:
                failure_count += 1
                errors.append({
                    "error": "Missing zone ID in update item"
                })
                continue

            try:
                # Filter out None values
                filtered_updates = {k: v for k, v in zone_updates.items() if v is not None}

                if not filtered_updates:
                    failure_count += 1
                    errors.append({
                        "zone_id": zone_id,
                        "error": "No valid updates provided"
                    })
                    continue

                success = database.update_zone(zone_id, **filtered_updates)
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                    errors.append({
                        "zone_id": zone_id,
                        "error": "Failed to update zone"
                    })

            except Exception as e:
                failure_count += 1
                errors.append({
                    "zone_id": zone_id,
                    "error": str(e)
                })

        return {
            "success": True,
            "message": f"Successfully updated {success_count} zones, {failure_count} failed",
            "success_count": success_count,
            "failure_count": failure_count,
            "errors": errors
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in bulk zone update: {str(e)}")

# Zone Analytics and Statistics

@router.get("/analytics", response_model=ZoneStatistics)
async def get_zone_statistics(
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Get comprehensive zone statistics and analytics.
    """
    try:
        # Get all zones
        zones = database.get_all_zones(limit=1000)

        # Basic counts
        total_zones = len(zones)
        active_zones = len([z for z in zones if z.get('is_active', True)])

        # Zones by type
        zones_by_type = defaultdict(int)
        for zone in zones:
            zones_by_type[zone.get('zone_type', 'unknown')] += 1

        # Get all alerts
        alerts = database.get_all_alerts(limit=10000, include_acknowledged=True)

        # Alert statistics
        total_alerts = len(alerts)
        alerts_by_severity = defaultdict(int)
        alerts_by_type = defaultdict(int)

        for alert in alerts:
            alerts_by_severity[alert.get('severity', 'medium')] += 1
            alerts_by_type[alert.get('alert_type', 'unknown')] += 1

        # Most active zones (by alert count)
        zone_alerts = defaultdict(int)
        for alert in alerts:
            if alert.get('zone_id'):
                zone_alerts[alert['zone_id']] += 1

        most_active_zones = []
        for zone_id, alert_count in sorted(zone_alerts.items(), key=lambda x: x[1], reverse=True)[:10]:
            zone = next((z for z in zones if z['id'] == zone_id), None)
            if zone:
                most_active_zones.append({
                    "zone_id": zone_id,
                    "zone_name": zone['name'],
                    "alert_count": alert_count,
                    "zone_type": zone.get('zone_type')
                })

        # Recent activity (last 24 hours)
        recent_activity = []
        cutoff_time = datetime.now() - timedelta(hours=24)

        for alert in alerts:
            alert_time = datetime.fromisoformat(alert['created_at'].replace('Z', '+00:00'))
            if alert_time > cutoff_time:
                recent_activity.append({
                    "alert_id": alert['id'],
                    "alert_type": alert['alert_type'],
                    "zone_name": alert.get('zone_name'),
                    "user_name": alert.get('user_name'),
                    "created_at": alert['created_at'],
                    "severity": alert.get('severity', 'medium')
                })

        return ZoneStatistics(
            total_zones=total_zones,
            active_zones=active_zones,
            zones_by_type=dict(zones_by_type),
            total_alerts=total_alerts,
            alerts_by_severity=dict(alerts_by_severity),
            alerts_by_type=dict(alerts_by_type),
            most_active_zones=most_active_zones,
            recent_activity=recent_activity
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting zone statistics: {str(e)}")

@router.get("/{zone_id}/analytics", response_model=ZoneAnalytics)
async def get_zone_analytics(
    zone_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Get detailed analytics for a specific zone.
    """
    try:
        zone = database.get_zone(zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")

        # Get users currently in zone
        users_in_zone = database.get_users_by_zone(zone_id)
        current_users_inside = len(users_in_zone)

        # Get alerts for this zone
        conn = database.get_connection()
        cursor = conn.cursor()

        # Total alerts
        cursor.execute('SELECT COUNT(*) as total_alerts FROM alerts WHERE zone_id = ?', (zone_id,))
        total_alerts = cursor.fetchone()['total_alerts']

        # Alerts in last 24 hours
        cursor.execute('''
            SELECT COUNT(*) as alerts_24h FROM alerts
            WHERE zone_id = ? AND created_at >= datetime('now', '-24 hours')
        ''', (zone_id,))
        alerts_24h = cursor.fetchone()['alerts_24h']

        # Alerts in last 7 days
        cursor.execute('''
            SELECT COUNT(*) as alerts_7d FROM alerts
            WHERE zone_id = ? AND created_at >= datetime('now', '-7 days')
        ''', (zone_id,))
        alerts_7d = cursor.fetchone()['alerts_7d']

        # Zone entry/exit events (approximated from alerts)
        cursor.execute('''
            SELECT COUNT(*) as entries FROM alerts
            WHERE zone_id = ? AND alert_type = 'zone_entry'
        ''', (zone_id,))
        total_users_entered = cursor.fetchone()['entries']

        cursor.execute('''
            SELECT COUNT(*) as exits FROM alerts
            WHERE zone_id = ? AND alert_type = 'zone_exit'
        ''', (zone_id,))
        total_users_exited = cursor.fetchone()['exits']

        # Peak concurrent users (simplified calculation)
        peak_concurrent_users = current_users_inside  # This would need more complex tracking

        conn.close()

        return ZoneAnalytics(
            zone_id=zone_id,
            zone_name=zone['name'],
            total_users_entered=total_users_entered,
            total_users_exited=total_users_exited,
            current_users_inside=current_users_inside,
            total_alerts=total_alerts,
            alerts_last_24h=alerts_24h,
            alerts_last_7d=alerts_7d,
            avg_time_spent_minutes=None,  # Would need session tracking
            peak_concurrent_users=peak_concurrent_users,
            created_at=zone['created_at'],
            is_active=zone['is_active']
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting zone analytics: {str(e)}")

# Zone Import/Export

@router.post("/export")
async def export_zones(
    format: str = Query('json', pattern='^(json|csv|geojson)$'),
    include_history: bool = Query(False),
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Export zones in various formats.
    """
    try:
        zones = database.get_all_zones(limit=10000)

        if format == 'csv':
            # CSV export
            output = io.StringIO()
            fieldnames = ['id', 'name', 'description', 'center_latitude', 'center_longitude',
                         'radius_meters', 'zone_type', 'is_active', 'created_at']
            writer = csv.DictWriter(output, fieldnames=fieldnames)

            writer.writeheader()
            for zone in zones:
                writer.writerow({
                    'id': zone['id'],
                    'name': zone['name'],
                    'description': zone['description'] or '',
                    'center_latitude': zone['center_latitude'],
                    'center_longitude': zone['center_longitude'],
                    'radius_meters': zone['radius_meters'],
                    'zone_type': zone['zone_type'],
                    'is_active': zone['is_active'],
                    'created_at': zone['created_at']
                })

            return {
                "format": "csv",
                "data": output.getvalue(),
                "filename": f"zones_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }

        elif format == 'geojson':
            # GeoJSON export
            features = []
            for zone in zones:
                features.append({
                    "type": "Feature",
                    "properties": {
                        "id": zone['id'],
                        "name": zone['name'],
                        "description": zone['description'],
                        "zone_type": zone['zone_type'],
                        "radius_meters": zone['radius_meters'],
                        "is_active": zone['is_active'],
                        "created_at": zone['created_at']
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [zone['center_longitude'], zone['center_latitude']]
                    }
                })

            geojson_data = {
                "type": "FeatureCollection",
                "features": features
            }

            return {
                "format": "geojson",
                "data": geojson_data,
                "filename": f"zones_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.geojson"
            }

        else:
            # JSON export (default)
            return {
                "format": "json",
                "data": zones,
                "filename": f"zones_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting zones: {str(e)}")

@router.post("/import")
async def import_zones(
    format: str = Query('json', pattern='^(json|csv|geojson)$'),
    data: str = None,
    current_user: dict = Depends(auth.get_current_active_user)
):
    if not auth.check_permission(current_user, "zones"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    """
    Import zones from various formats.
    """
    try:
        import json as json_module

        zones_to_create = []

        if format == 'csv':
            # Parse CSV data
            csv_reader = csv.DictReader(io.StringIO(data))
            for row in csv_reader:
                zones_to_create.append({
                    'name': row['name'],
                    'description': row.get('description', ''),
                    'center_latitude': float(row['center_latitude']),
                    'center_longitude': float(row['center_longitude']),
                    'radius_meters': float(row['radius_meters']),
                    'zone_type': row.get('zone_type', 'circular')
                })

        elif format == 'geojson':
            # Parse GeoJSON data
            geojson_data = json_module.loads(data)
            for feature in geojson_data.get('features', []):
                props = feature['properties']
                coords = feature['geometry']['coordinates']
                zones_to_create.append({
                    'name': props['name'],
                    'description': props.get('description', ''),
                    'center_latitude': coords[1],  # GeoJSON is [lng, lat]
                    'center_longitude': coords[0],
                    'radius_meters': props.get('radius_meters', 100),
                    'zone_type': props.get('zone_type', 'circular')
                })

        else:
            # JSON format
            zones_data = json_module.loads(data)
            if isinstance(zones_data, list):
                zones_to_create = zones_data
            else:
                zones_to_create = [zones_data]

        # Create zones
        success_count = 0
        failure_count = 0
        errors = []

        for i, zone_data in enumerate(zones_to_create):
            try:
                zone_id = database.create_zone(
                    name=zone_data['name'],
                    description=zone_data.get('description'),
                    center_latitude=zone_data['center_latitude'],
                    center_longitude=zone_data['center_longitude'],
                    radius_meters=zone_data['radius_meters'],
                    zone_type=zone_data.get('zone_type', 'circular'),
                    created_by=current_user.get('id')
                )

                if zone_id:
                    success_count += 1
                else:
                    failure_count += 1
                    errors.append({
                        "index": i,
                        "error": "Failed to create zone"
                    })

            except Exception as e:
                failure_count += 1
                errors.append({
                    "index": i,
                    "error": str(e)
                })

        return {
            "success": True,
            "message": f"Successfully imported {success_count} zones, {failure_count} failed",
            "success_count": success_count,
            "failure_count": failure_count,
            "errors": errors
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing zones: {str(e)}")