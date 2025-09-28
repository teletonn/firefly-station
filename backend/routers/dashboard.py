from fastapi import APIRouter, Depends
from backend import database, auth

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(current_user: dict = Depends(auth.get_current_active_user)):
    """
    Get aggregated statistics for the main dashboard.
    """
    if not auth.check_permission(current_user, "dashboard:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user_stats = database.get_user_stats()
    message_stats = database.get_message_stats()
    alert_stats = database.get_alert_stats()
    zone_stats = database.get_zone_stats()

    # In a real scenario, bot status would be fetched from the bot process
    # or a shared status store like Redis. For now, we'll assume it's running.
    bot_status = "Online"

    return {
        "total_users": user_stats.get("total_users", 0),
        "active_sessions": user_stats.get("active_sessions", 0),
        "online_users": user_stats.get("online_now", 0),
        "messages_today": message_stats.get("today", 0),
        "bot_status": bot_status,
        "total_alerts": alert_stats.get("total", 0),
        "active_zones": zone_stats.get("active", 0)
    }

@router.get("/map-data")
async def get_map_data(current_user: dict = Depends(auth.get_current_active_user)):
    """
    Get all data needed for the map view.
    """
    if not auth.check_permission(current_user, "dashboard:read"): # Assuming map is part of dashboard
        raise HTTPException(status_code=403, detail="Not enough permissions")

    users = database.get_all_users(limit=1000) # Get a reasonable number of users for the map
    zones = database.get_all_zones(limit=1000) # Get all zones

    return {
        "users": users,
        "zones": zones
    }