from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from backend import database, auth
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def get_alerts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    include_acknowledged: bool = Query(False),
    alert_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    zone_id: Optional[int] = Query(None),
    user_id: Optional[str] = Query(None),
    current_user = Depends(auth.get_current_active_user)
):
    """Get all alerts with filtering and pagination."""
    if not auth.check_permission(current_user, "alerts:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Get alerts from database
    alerts = database.get_all_alerts(
        limit=limit,
        offset=offset,
        include_acknowledged=include_acknowledged
    )

    # Apply additional filters
    filtered_alerts = alerts
    if alert_type:
        filtered_alerts = [a for a in filtered_alerts if a.get('alert_type') == alert_type]
    if severity:
        filtered_alerts = [a for a in filtered_alerts if a.get('severity') == severity]
    if zone_id:
        filtered_alerts = [a for a in filtered_alerts if a.get('zone_id') == zone_id]
    if user_id:
        filtered_alerts = [a for a in filtered_alerts if a.get('user_id') == user_id]

    return {
        "alerts": filtered_alerts,
        "limit": limit,
        "offset": offset,
        "total": len(filtered_alerts)
    }

@router.get("/{alert_id}")
async def get_alert(
    alert_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Get specific alert by ID."""
    if not auth.check_permission(current_user, "alerts:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    alert = database.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert

@router.post("/", status_code=201)
async def create_alert(
    user_id: Optional[str] = Body(None),
    zone_id: Optional[int] = Body(None),
    alert_type: str = Body(...),
    severity: str = Body("medium"),
    title: str = Body(...),
    message: str = Body(...),
    location_latitude: Optional[float] = Body(None),
    location_longitude: Optional[float] = Body(None),
    target_groups: List[int] = Body(default=[]),
    escalation_rules: Dict[str, Any] = Body(default={}),
    current_user = Depends(auth.get_current_active_user)
):
    """Create a new alert."""
    if not auth.check_permission(current_user, "alerts:create"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Validate severity
    valid_severities = ["low", "medium", "high", "critical"]
    if severity not in valid_severities:
        raise HTTPException(status_code=400, detail="Invalid severity level")

    # Create the main alert
    alert_id = database.create_alert(
        user_id=user_id,
        zone_id=zone_id,
        alert_type=alert_type,
        title=title,
        message=message,
        severity=severity,
        location_latitude=location_latitude,
        location_longitude=location_longitude
    )

    if not alert_id:
        raise HTTPException(status_code=500, detail="Failed to create alert")

    # If target_groups specified, create group-targeted alerts
    created_alerts = [alert_id]

    if target_groups:
        for group_id in target_groups:
            group_alert_id = database.create_alert(
                user_id=user_id,
                zone_id=zone_id,
                alert_type=f"group_{alert_type}",
                title=f"[Group {group_id}] {title}",
                message=f"Group Alert: {message}",
                severity=severity,
                location_latitude=location_latitude,
                location_longitude=location_longitude
            )
            if group_alert_id:
                created_alerts.append(group_alert_id)

    # Store escalation rules if provided
    if escalation_rules:
        conn = database.get_connection()
        cursor = conn.cursor()

        # Create alert_escalation_rules table if it doesn't exist
        # NOTE: This table should be created in init_db, but keeping here for backward compatibility
        logger.warning("Creating alert_escalation_rules table dynamically - consider adding to init_db")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_escalation_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                rules TEXT NOT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (alert_id) REFERENCES alerts (id),
                FOREIGN KEY (created_by) REFERENCES admin_users (id)
            )
        ''')

        cursor.execute('''
            INSERT INTO alert_escalation_rules (alert_id, rules, created_by)
            VALUES (?, ?, ?)
        ''', (alert_id, json.dumps(escalation_rules), current_user['id']))

        conn.commit()
        conn.close()

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="create",
        resource="alert",
        resource_id=str(alert_id),
        details=f"Created alert '{title}' with severity {severity}"
    )

    return {
        "alert_id": alert_id,
        "created_alerts": created_alerts,
        "target_groups": target_groups
    }

@router.put("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Acknowledge an alert."""
    if not auth.check_permission(current_user, "alerts:acknowledge"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    success = database.acknowledge_alert(alert_id, current_user['id'])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="acknowledge",
        resource="alert",
        resource_id=str(alert_id),
        details="Alert acknowledged"
    )

    return {"message": "Alert acknowledged successfully"}

@router.put("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    resolution_notes: Optional[str] = Body(""),
    current_user = Depends(auth.get_current_active_user)
):
    """Resolve an alert."""
    if not auth.check_permission(current_user, "alerts:resolve"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    success = database.resolve_alert(alert_id, current_user['id'])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to resolve alert")

    # Add resolution notes if provided
    if resolution_notes:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE alerts SET message = message || '\n\nResolution: ' || ? WHERE id = ?
        ''', (resolution_notes, alert_id))
        conn.commit()
        conn.close()

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="resolve",
        resource="alert",
        resource_id=str(alert_id),
        details=f"Alert resolved with notes: {resolution_notes}"
    )

    return {"message": "Alert resolved successfully"}

@router.get("/stats/overview")
async def get_alert_stats(
    days: int = Query(30, ge=1, le=365),
    current_user = Depends(auth.get_current_active_user)
):
    """Get alert statistics."""
    if not auth.check_permission(current_user, "alerts:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    # Get total alerts count
    cursor.execute('SELECT COUNT(*) as total_alerts FROM alerts')
    total_alerts = cursor.fetchone()['total_alerts']

    # Get alerts by type
    cursor.execute('''
        SELECT alert_type, COUNT(*) as count
        FROM alerts
        GROUP BY alert_type
        ORDER BY count DESC
    ''')
    alerts_by_type = {row['alert_type']: row['count'] for row in cursor.fetchall()}

    # Get alerts by severity
    cursor.execute('''
        SELECT severity, COUNT(*) as count
        FROM alerts
        GROUP BY severity
        ORDER BY count DESC
    ''')
    alerts_by_severity = {row['severity']: row['count'] for row in cursor.fetchall()}

    # Get unacknowledged alerts
    cursor.execute('SELECT COUNT(*) as unacknowledged FROM alerts WHERE is_acknowledged = FALSE')
    unacknowledged = cursor.fetchone()['unacknowledged']

    # Get unresolved alerts
    cursor.execute('SELECT COUNT(*) as unresolved FROM alerts WHERE is_resolved = FALSE')
    unresolved = cursor.fetchone()['unresolved']

    # Get recent alerts (last N days)
    start_date = datetime.now() - timedelta(days=days)
    cursor.execute('''
        SELECT COUNT(*) as recent_alerts
        FROM alerts
        WHERE created_at >= ?
    ''', (start_date,))
    recent_alerts = cursor.fetchone()['recent_alerts']

    # Get average resolution time
    cursor.execute('''
        SELECT AVG(CAST((julianday(resolved_at) - julianday(created_at)) * 24 * 60 * 60 AS INTEGER)) as avg_resolution_seconds
        FROM alerts
        WHERE is_resolved = TRUE AND resolved_at IS NOT NULL
    ''')
    avg_resolution_time = cursor.fetchone()['avg_resolution_seconds']

    conn.close()

    return {
        "total_alerts": total_alerts,
        "unacknowledged_alerts": unacknowledged,
        "unresolved_alerts": unresolved,
        "recent_alerts": recent_alerts,
        "alerts_by_type": alerts_by_type,
        "alerts_by_severity": alerts_by_severity,
        "average_resolution_time_seconds": avg_resolution_time,
        "period_days": days
    }

@router.get("/escalation-rules/{alert_id}")
async def get_alert_escalation_rules(
    alert_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Get escalation rules for a specific alert."""
    if not auth.check_permission(current_user, "alerts:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT rules FROM alert_escalation_rules WHERE alert_id = ?
    ''', (alert_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="No escalation rules found for this alert")

    try:
        rules = json.loads(row['rules'])
        return {"alert_id": alert_id, "escalation_rules": rules}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid escalation rules format")

@router.post("/escalation-rules/{alert_id}")
async def update_alert_escalation_rules(
    alert_id: int,
    rules: Dict[str, Any] = Body(...),
    current_user = Depends(auth.get_current_active_user)
):
    """Update escalation rules for an alert."""
    if not auth.check_permission(current_user, "alerts:create"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    # Check if escalation rules already exist
    cursor.execute('SELECT id FROM alert_escalation_rules WHERE alert_id = ?', (alert_id,))
    existing = cursor.fetchone()

    if existing:
        # Update existing rules
        cursor.execute('''
            UPDATE alert_escalation_rules SET rules = ?, created_by = ? WHERE alert_id = ?
        ''', (json.dumps(rules), current_user['id'], alert_id))
    else:
        # Create new rules
        cursor.execute('''
            INSERT INTO alert_escalation_rules (alert_id, rules, created_by)
            VALUES (?, ?, ?)
        ''', (alert_id, json.dumps(rules), current_user['id']))

    conn.commit()
    conn.close()

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="update",
        resource="alert_escalation_rules",
        resource_id=str(alert_id),
        details="Updated alert escalation rules"
    )

    return {"message": "Escalation rules updated successfully"}

@router.post("/bulk-acknowledge")
async def bulk_acknowledge_alerts(
    alert_ids: List[int] = Body(...),
    current_user = Depends(auth.get_current_active_user)
):
    """Bulk acknowledge multiple alerts."""
    if not auth.check_permission(current_user, "alerts:acknowledge"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    results = {"successful": [], "failed": []}

    for alert_id in alert_ids:
        success = database.acknowledge_alert(alert_id, current_user['id'])
        if success:
            results["successful"].append(alert_id)
        else:
            results["failed"].append(alert_id)

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="bulk_acknowledge",
        resource="alerts",
        details=f"Bulk acknowledged {len(results['successful'])} alerts, {len(results['failed'])} failed"
    )

    return results

@router.post("/bulk-resolve")
async def bulk_resolve_alerts(
    alert_ids: List[int] = Body(...),
    resolution_notes: str = Body(""),
    current_user = Depends(auth.get_current_active_user)
):
    """Bulk resolve multiple alerts."""
    if not auth.check_permission(current_user, "alerts:resolve"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    results = {"successful": [], "failed": []}

    for alert_id in alert_ids:
        success = database.resolve_alert(alert_id, current_user['id'])
        if success:
            results["successful"].append(alert_id)
        else:
            results["failed"].append(alert_id)

    # Add resolution notes to all resolved alerts
    if resolution_notes and results["successful"]:
        conn = database.get_connection()
        cursor = conn.cursor()
        for alert_id in results["successful"]:
            cursor.execute('''
                UPDATE alerts SET message = message || '\n\nResolution: ' || ? WHERE id = ?
            ''', (resolution_notes, alert_id))
        conn.commit()
        conn.close()

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="bulk_resolve",
        resource="alerts",
        details=f"Bulk resolved {len(results['successful'])} alerts, {len(results['failed'])} failed"
    )

    return results

@router.get("/user/{user_id}/history")
async def get_user_alert_history(
    user_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user = Depends(auth.get_current_active_user)
):
    """Get alert history for a specific user."""
    if not auth.check_permission(current_user, "alerts:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT a.*, z.name as zone_name, au.username as acknowledged_by_username, ar.username as resolved_by_username
        FROM alerts a
        LEFT JOIN zones z ON a.zone_id = z.id
        LEFT JOIN admin_users au ON a.acknowledged_by = au.id
        LEFT JOIN admin_users ar ON a.resolved_by = ar.id
        WHERE a.user_id = ?
        ORDER BY a.created_at DESC
        LIMIT ? OFFSET ?
    ''', (user_id, limit, offset))

    rows = cursor.fetchall()
    conn.close()

    alerts = [dict(row) for row in rows]
    return {
        "alerts": alerts,
        "limit": limit,
        "offset": offset,
        "total": len(alerts)
    }


# Alert Rules Management Endpoints

@router.get("/rules/")
async def get_alert_rules(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(True),
    current_user = Depends(auth.get_current_active_user)
):
    """Get all alert rules with filtering and pagination."""
    if not auth.check_permission(current_user, "alerts:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    rules = database.get_all_alert_rules(limit=limit, offset=offset, active_only=active_only)

    return {
        "rules": rules,
        "limit": limit,
        "offset": offset,
        "total": len(rules)
    }

@router.get("/rules/{rule_id}")
async def get_alert_rule(
    rule_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Get specific alert rule by ID."""
    if not auth.check_permission(current_user, "alerts:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    rule = database.get_alert_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    return rule

@router.post("/rules/")
async def create_alert_rule(
    name: str = Body(...),
    description: str = Body(""),
    alert_type: str = Body(...),
    severity: str = Body("medium"),
    zone_id: Optional[int] = Body(None),
    conditions: Dict[str, Any] = Body(default={}),
    target_groups: List[int] = Body(default=[]),
    escalation_rules: Dict[str, Any] = Body(default={}),
    current_user = Depends(auth.get_current_active_user)
):
    """Create a new alert rule."""
    if not auth.check_permission(current_user, "alerts:create"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Validate severity
    valid_severities = ["low", "medium", "high", "critical"]
    if severity not in valid_severities:
        raise HTTPException(status_code=400, detail="Invalid severity level")

    # Validate alert type
    valid_types = ["zone_entry", "zone_exit", "speeding", "offline", "battery_low"]
    if alert_type not in valid_types:
        raise HTTPException(status_code=400, detail="Invalid alert type")

    # Convert data to JSON strings
    conditions_json = json.dumps(conditions) if conditions else None
    target_groups_json = json.dumps(target_groups) if target_groups else None
    escalation_rules_json = json.dumps(escalation_rules) if escalation_rules else None

    rule_id = database.create_alert_rule(
        name=name,
        description=description,
        alert_type=alert_type,
        severity=severity,
        zone_id=zone_id,
        conditions=conditions_json,
        target_groups=target_groups_json,
        escalation_rules=escalation_rules_json,
        created_by=current_user['id']
    )

    if not rule_id:
        raise HTTPException(status_code=500, detail="Failed to create alert rule")

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="create",
        resource="alert_rule",
        resource_id=str(rule_id),
        details=f"Created alert rule '{name}' with type {alert_type}"
    )

    return {
        "rule_id": rule_id,
        "message": "Alert rule created successfully"
    }

@router.put("/rules/{rule_id}")
async def update_alert_rule(
    rule_id: int,
    name: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    alert_type: Optional[str] = Body(None),
    severity: Optional[str] = Body(None),
    zone_id: Optional[int] = Body(None),
    conditions: Optional[Dict[str, Any]] = Body(None),
    target_groups: Optional[List[int]] = Body(None),
    escalation_rules: Optional[Dict[str, Any]] = Body(None),
    is_active: Optional[bool] = Body(None),
    current_user = Depends(auth.get_current_active_user)
):
    """Update an alert rule."""
    if not auth.check_permission(current_user, "alerts:create"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Validate severity if provided
    if severity:
        valid_severities = ["low", "medium", "high", "critical"]
        if severity not in valid_severities:
            raise HTTPException(status_code=400, detail="Invalid severity level")

    # Validate alert type if provided
    if alert_type:
        valid_types = ["zone_entry", "zone_exit", "speeding", "offline", "battery_low"]
        if alert_type not in valid_types:
            raise HTTPException(status_code=400, detail="Invalid alert type")

    # Prepare update data
    update_data = {}
    if name is not None:
        update_data['name'] = name
    if description is not None:
        update_data['description'] = description
    if alert_type is not None:
        update_data['alert_type'] = alert_type
    if severity is not None:
        update_data['severity'] = severity
    if zone_id is not None:
        update_data['zone_id'] = zone_id
    if conditions is not None:
        update_data['conditions'] = json.dumps(conditions)
    if target_groups is not None:
        update_data['target_groups'] = json.dumps(target_groups)
    if escalation_rules is not None:
        update_data['escalation_rules'] = json.dumps(escalation_rules)
    if is_active is not None:
        update_data['is_active'] = is_active

    success = database.update_alert_rule(rule_id, **update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update alert rule")

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="update",
        resource="alert_rule",
        resource_id=str(rule_id),
        details=f"Updated alert rule {rule_id}"
    )

    return {"message": "Alert rule updated successfully"}

@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Delete an alert rule."""
    if not auth.check_permission(current_user, "alerts:create"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    success = database.delete_alert_rule(rule_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete alert rule")

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="delete",
        resource="alert_rule",
        resource_id=str(rule_id),
        details=f"Deleted alert rule {rule_id}"
    )

    return {"message": "Alert rule deleted successfully"}

@router.get("/zone/{zone_id}/history")
async def get_zone_alert_history(
    zone_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user = Depends(auth.get_current_active_user)
):
    """Get alert history for a specific zone."""
    if not auth.check_permission(current_user, "alerts:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT a.*, u.long_name as user_name, au.username as acknowledged_by_username, ar.username as resolved_by_username
        FROM alerts a
        LEFT JOIN users u ON a.user_id = u.id
        LEFT JOIN admin_users au ON a.acknowledged_by = au.id
        LEFT JOIN admin_users ar ON a.resolved_by = ar.id
        WHERE a.zone_id = ?
        ORDER BY a.created_at DESC
        LIMIT ? OFFSET ?
    ''', (zone_id, limit, offset))

    rows = cursor.fetchall()
    conn.close()

    alerts = [dict(row) for row in rows]
    return {
        "alerts": alerts,
        "limit": limit,
        "offset": offset,
        "total": len(alerts)
    }