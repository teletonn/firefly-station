from fastapi import APIRouter, Depends, HTTPException, Query
from backend import database, auth

router = APIRouter()

@router.get("/")
async def get_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    action: str = Query(None),
    resource: str = Query(None),
    admin_user_id: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user = Depends(auth.get_current_active_user)
):
    """Get audit logs with pagination and filtering."""
    if not auth.check_permission(current_user, "audit"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Build query with filters
    conn = database.get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT al.*, au.username
        FROM audit_logs al
        LEFT JOIN admin_users au ON al.admin_user_id = au.id
        WHERE 1=1
    '''
    params = []

    if action:
        query += ' AND al.action = ?'
        params.append(action)

    if resource:
        query += ' AND al.resource = ?'
        params.append(resource)

    if admin_user_id:
        query += ' AND al.admin_user_id = ?'
        params.append(admin_user_id)

    if start_date:
        query += ' AND al.timestamp >= ?'
        params.append(start_date)

    if end_date:
        query += ' AND al.timestamp <= ?'
        params.append(end_date)

    query += ' ORDER BY al.timestamp DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    logs = [dict(row) for row in rows]

    # Log the audit view itself
    database.log_audit(
        admin_user_id=current_user['id'],
        action="view",
        resource="audit_logs",
        details=f"Viewed {len(logs)} audit logs with filters"
    )

    return {"logs": logs, "limit": limit, "offset": offset, "total": len(logs)}

@router.get("/user/{admin_user_id}")
async def get_user_audit_logs(
    admin_user_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user = Depends(auth.get_current_active_user)
):
    """Get audit logs for a specific admin user."""
    if not auth.check_permission(current_user, "audit"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Get logs filtered by admin_user_id
    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT al.*, au.username
        FROM audit_logs al
        LEFT JOIN admin_users au ON al.admin_user_id = au.id
        WHERE al.admin_user_id = ?
        ORDER BY al.timestamp DESC
        LIMIT ? OFFSET ?
    ''', (admin_user_id, limit, offset))

    rows = cursor.fetchall()
    conn.close()
    logs = [dict(row) for row in rows]

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="view",
        resource="audit_logs",
        resource_id=str(admin_user_id),
        details=f"Viewed audit logs for admin user {admin_user_id}"
    )

    return {"logs": logs, "admin_user_id": admin_user_id, "limit": limit, "offset": offset}

@router.get("/stats/overview")
async def get_audit_stats(current_user = Depends(auth.get_current_active_user)):
    """Get audit statistics."""
    if not auth.check_permission(current_user, "audit"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    # Get total logs count
    cursor.execute('SELECT COUNT(*) as total_logs FROM audit_logs')
    total_logs = cursor.fetchone()['total_logs']

    # Get logs by action
    cursor.execute('''
        SELECT action, COUNT(*) as count
        FROM audit_logs
        GROUP BY action
        ORDER BY count DESC
    ''')
    action_stats = cursor.fetchall()

    # Get recent activity (last 24 hours)
    cursor.execute('''
        SELECT COUNT(*) as recent_logs
        FROM audit_logs
        WHERE timestamp > datetime('now', '-1 day')
    ''')
    recent_logs = cursor.fetchone()['recent_logs']

    conn.close()

    return {
        "total_logs": total_logs,
        "recent_logs": recent_logs,
        "action_breakdown": [dict(row) for row in action_stats]
    }

@router.get("/recent")
async def get_recent_audit_logs(limit: int = 50, current_user = Depends(auth.get_current_active_user)):
    """Get recent audit logs."""
    if not auth.check_permission(current_user, "audit:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    logs = database.get_audit_logs(limit=limit, offset=0)

    return {"activities": logs}