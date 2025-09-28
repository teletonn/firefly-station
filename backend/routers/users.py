from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from backend import database, auth
import json
import csv
import io
from datetime import datetime

router = APIRouter()

@router.post("/")
async def create_user(
    user_data: Dict[str, Any] = Body(...),
    current_user = Depends(auth.get_current_active_user)
):
    """Create a new user."""
    if not auth.check_permission(current_user, "users"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user_id = user_data.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    existing = database.get_user(user_id)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    database.insert_or_update_user(user_id, user_data)
    database.log_audit(
        admin_user_id=current_user['id'],
        action="create",
        resource="user",
        resource_id=user_id,
        details=f"Created user {user_id}"
    )
    return {"message": "User created successfully", "user_id": user_id}

@router.get("/")
async def get_users(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user = Depends(auth.get_current_active_user)
):
    """Get all users with pagination."""
    if not auth.check_permission(current_user, "users:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    users = database.get_all_users(limit=limit, offset=offset)
    return {"users": users, "limit": limit, "offset": offset}

@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user = Depends(auth.get_current_active_user)
):
    """Get specific user by ID."""
    if not auth.check_permission(current_user, "users:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    user = database.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    database.log_audit(
        admin_user_id=current_user['id'],
        action="view",
        resource="user",
        resource_id=user_id,
        details=f"Viewed user {user_id}"
    )
    return user

@router.put("/{user_id}")
async def update_user(
    user_id: str,
    user_data: Dict[str, Any] = Body(...),
    current_user = Depends(auth.get_current_active_user)
):
    """Update user details."""
    if not auth.check_permission(current_user, "users"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    existing = database.get_user(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    database.insert_or_update_user(user_id, user_data)
    database.log_audit(
        admin_user_id=current_user['id'],
        action="update",
        resource="user",
        resource_id=user_id,
        details=f"Updated user {user_id}"
    )
    return {"message": "User updated successfully"}

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(auth.get_current_active_user)
):
    """Delete a user."""
    if not auth.check_permission(current_user, "users"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    existing = database.get_user(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    database.log_audit(
        admin_user_id=current_user['id'],
        action="delete",
        resource="user",
        resource_id=user_id,
        details=f"Deleted user {user_id}"
    )
    return {"message": "User deleted successfully"}

@router.get("/stats/overview")
async def get_user_stats(current_user = Depends(auth.get_current_active_user)):
    """Get user statistics."""
    if not auth.check_permission(current_user, "users:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    stats = database.get_bot_stats()
    return stats

# User Group Management Endpoints

@router.post("/groups")
async def create_user_group(
    name: str = Body(...),
    description: str = Body(""),
    current_user = Depends(auth.get_current_active_user)
):
    """Create a new user group."""
    if not auth.check_permission(current_user, "users"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    group_id = database.create_user_group(name, description, current_user['id'])
    if not group_id:
        raise HTTPException(status_code=500, detail="Failed to create user group")
    database.log_audit(
        admin_user_id=current_user['id'],
        action="create",
        resource="user_group",
        resource_id=str(group_id),
        details=f"Created user group '{name}'"
    )
    return {"id": group_id, "name": name, "description": description}

@router.get("/groups")
async def get_user_groups(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user = Depends(auth.get_current_active_user)
):
    """Get all user groups with pagination."""
    if not auth.check_permission(current_user, "users:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    groups = database.get_all_user_groups(limit=limit, offset=offset)
    return {"groups": groups, "limit": limit, "offset": offset}

@router.get("/groups/{group_id}")
async def get_user_group(
    group_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Get specific user group by ID."""
    if not auth.check_permission(current_user, "users:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    group = database.get_user_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    users_in_group = database.get_users_in_group(group_id)
    group_details = dict(group)
    group_details['users'] = users_in_group
    group_details['user_count'] = len(users_in_group)
    return group_details

@router.put("/groups/{group_id}")
async def update_user_group(
    group_id: int,
    name: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    current_user = Depends(auth.get_current_active_user)
):
    """Update user group."""
    if not auth.check_permission(current_user, "users"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    group = database.get_user_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")
    updates = {}
    if name is not None:
        updates['name'] = name
    if description is not None:
        updates['description'] = description
    if updates:
        conn = database.get_connection()
        cursor = conn.cursor()
        fields = []
        values = []
        for key, value in updates.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(datetime.now())
        values.append(group_id)
        query = f"UPDATE user_groups SET {', '.join(fields)}, updated_at = ? WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        database.log_audit(
            admin_user_id=current_user['id'],
            action="update",
            resource="user_group",
            resource_id=str(group_id),
            details=f"Updated user group '{group.get('name', 'Unknown')}'"
        )
    return {"message": "User group updated successfully"}

@router.delete("/groups/{group_id}")
async def delete_user_group(
    group_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Delete user group."""
    if not auth.check_permission(current_user, "users"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    group = database.get_user_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_group_members WHERE group_id = ?", (group_id,))
    cursor.execute("DELETE FROM user_groups WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()
    database.log_audit(
        admin_user_id=current_user['id'],
        action="delete",
        resource="user_group",
        resource_id=str(group_id),
        details=f"Deleted user group '{group.get('name', 'Unknown')}'"
    )
    return {"message": "User group deleted successfully"}

@router.post("/groups/{group_id}/users/{user_id}")
async def add_user_to_group(
    group_id: int,
    user_id: str,
    current_user = Depends(auth.get_current_active_user)
):
    """Add user to group."""
    if not auth.check_permission(current_user, "users"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    success = database.add_user_to_group(user_id, group_id, current_user['id'])
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add user to group")
    database.log_audit(
        admin_user_id=current_user['id'],
        action="assign",
        resource="user_group_member",
        resource_id=f"{group_id}:{user_id}",
        details=f"Added user {user_id} to group {group_id}"
    )
    return {"message": "User added to group successfully"}

@router.delete("/groups/{group_id}/users/{user_id}")
async def remove_user_from_group(
    group_id: int,
    user_id: str,
    current_user = Depends(auth.get_current_active_user)
):
    """Remove user from group."""
    if not auth.check_permission(current_user, "users"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    success = database.remove_user_from_group(user_id, group_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove user from group")
    database.log_audit(
        admin_user_id=current_user['id'],
        action="remove",
        resource="user_group_member",
        resource_id=f"{group_id}:{user_id}",
        details=f"Removed user {user_id} from group {group_id}"
    )
    return {"message": "User removed from group successfully"}

# Bulk User Operations

@router.post("/bulk/assign-groups")
async def bulk_assign_groups(
    assignments: List[Dict[str, Any]] = Body(...),
    current_user = Depends(auth.get_current_active_user)
):
    """Bulk assign users to groups."""
    if not auth.check_permission(current_user, "users"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    results = {"successful": [], "failed": []}
    for assignment in assignments:
        user_id = assignment.get("user_id")
        group_id = assignment.get("group_id")
        if not user_id or not group_id:
            results["failed"].append({"user_id": user_id, "group_id": group_id, "error": "Missing user_id or group_id"})
            continue
        success = database.add_user_to_group(user_id, group_id, current_user['id'])
        if success:
            results["successful"].append({"user_id": user_id, "group_id": group_id})
        else:
            results["failed"].append({"user_id": user_id, "group_id": group_id, "error": "Failed to assign user to group"})
    database.log_audit(
        admin_user_id=current_user['id'],
        action="bulk_assign",
        resource="user_group_members",
        details=f"Bulk assigned {len(results['successful'])} users to groups, {len(results['failed'])} failed"
    )
    return results

@router.post("/bulk/update-status")
async def bulk_update_user_status(
    user_updates: List[Dict[str, Any]] = Body(...),
    current_user = Depends(auth.get_current_active_user)
):
    """Bulk update user properties."""
    if not auth.check_permission(current_user, "users"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    results = {"successful": [], "failed": []}
    for update in user_updates:
        user_id = update.get("user_id")
        updates = {k: v for k, v in update.items() if k != "user_id"}
        if not user_id or not updates:
            results["failed"].append({"user_id": user_id, "error": "Missing user_id or updates"})
            continue
        try:
            conn = database.get_connection()
            cursor = conn.cursor()
            fields = []
            values = []
            for key, value in updates.items():
                if key in ['tracking_enabled', 'device_status', 'group_id']:
                    fields.append(f"{key} = ?")
                    values.append(value)
            if not fields:
                results["failed"].append({"user_id": user_id, "error": "No valid fields to update"})
                continue
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            results["successful"].append({"user_id": user_id, "updates": updates})
        except Exception as e:
            results["failed"].append({"user_id": user_id, "error": str(e)})
    database.log_audit(
        admin_user_id=current_user['id'],
        action="bulk_update",
        resource="users",
        details=f"Bulk updated {len(results['successful'])} users, {len(results['failed'])} failed"
    )
    return results

# Import/Export Features

@router.post("/import")
async def import_users(
    file: str = Body(..., description="CSV data as string"),
    current_user = Depends(auth.get_current_active_user)
):
    """Import users from CSV data."""
    if not auth.check_permission(current_user, "users"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        csv_reader = csv.DictReader(io.StringIO(file))
        users_data = list(csv_reader)
        results = {"successful": [], "failed": []}
        for user_data in users_data:
            user_id = user_data.get("id") or user_data.get("user_id")
            if not user_id:
                results["failed"].append({"data": user_data, "error": "Missing user ID"})
                continue
            try:
                user_info = {
                    "user": {"longName": user_data.get("long_name", ""), "shortName": user_data.get("short_name", "")},
                    "position": {
                        "latitude": float(user_data.get("latitude", 0)) if user_data.get("latitude") else None,
                        "longitude": float(user_data.get("longitude", 0)) if user_data.get("longitude") else None,
                        "altitude": float(user_data.get("altitude", 0)) if user_data.get("altitude") else None
                    },
                    "deviceMetrics": {"batteryLevel": int(user_data.get("battery_level", 0)) if user_data.get("battery_level") else None}
                }
                database.insert_or_update_user(user_id, user_info)
                if user_data.get("group_id"):
                    database.add_user_to_group(user_id, int(user_data.get("group_id")), current_user['id'])
                results["successful"].append({"user_id": user_id})
            except Exception as e:
                results["failed"].append({"user_id": user_id, "data": user_data, "error": str(e)})
        database.log_audit(
            admin_user_id=current_user['id'],
            action="import",
            resource="users",
            details=f"Imported {len(results['successful'])} users, {len(results['failed'])} failed"
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

@router.get("/export")
async def export_users(
    format: str = Query("csv", regex="^(csv|json)$"),
    group_id: Optional[int] = Query(None),
    current_user = Depends(auth.get_current_active_user)
):
    """Export users to CSV or JSON format."""
    if not auth.check_permission(current_user, "users:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if group_id:
        users = database.get_users_in_group(group_id)
    else:
        users = database.get_all_users(limit=10000)
    if format == "csv":
        output = io.StringIO()
        fieldnames = ["id", "long_name", "short_name", "battery_level", "latitude", "longitude", "altitude", "last_seen", "device_status"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for user in users:
            writer.writerow({
                "id": user.get("id", ""), "long_name": user.get("long_name", ""), "short_name": user.get("short_name", ""),
                "battery_level": user.get("battery_level", ""), "latitude": user.get("latitude", ""), "longitude": user.get("longitude", ""),
                "altitude": user.get("altitude", ""), "last_seen": user.get("last_seen", ""), "device_status": user.get("device_status", "")
            })
        content = output.getvalue()
        media_type = "text/csv"
    else:
        content = json.dumps(users, indent=2, default=str)
        media_type = "application/json"
    database.log_audit(
        admin_user_id=current_user['id'],
        action="export",
        resource="users",
        details=f"Exported {len(users)} users in {format} format"
    )
    return {
        "content": content,
        "filename": f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}",
        "media_type": media_type
    }