from fastapi import APIRouter, Depends, HTTPException, Query
from backend import database, auth

router = APIRouter()

@router.get("/")
async def get_messages(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user = Depends(auth.get_current_active_user)
):
    """Get all messages with pagination."""
    if not auth.check_permission(current_user, "messages:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    messages = database.get_all_messages(limit=limit, offset=offset)

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="view",
        resource="messages",
        details=f"Viewed {len(messages)} messages"
    )

    return {"messages": messages, "limit": limit, "offset": offset}

@router.get("/user/{user_id}")
async def get_user_messages(
    user_id: str,
    limit: int = Query(50, ge=1, le=500),
    current_user = Depends(auth.get_current_active_user)
):
    """Get messages for a specific user."""
    if not auth.check_permission(current_user, "messages:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    messages = database.get_messages_for_user(user_id, limit=limit)

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="view",
        resource="messages",
        resource_id=user_id,
        details=f"Viewed messages for user {user_id}"
    )

    return {"messages": messages, "user_id": user_id}

@router.delete("/{message_id}", status_code=204)
async def delete_message(
    message_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Delete a message."""
    if not auth.check_permission(current_user, "messages:delete"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    success = database.delete_message(message_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found or could not be deleted")

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="delete",
        resource="message",
        resource_id=str(message_id),
        details=f"Deleted message {message_id}"
    )

    return

@router.get("/stats/overview")
async def get_message_stats(current_user = Depends(auth.get_current_active_user)):
    """Get message statistics."""
    if not auth.check_permission(current_user, "messages:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    stats = database.get_bot_stats()
    return {
        "total_messages": stats['total_messages'],
        "active_sessions": stats['active_sessions']
    }

@router.get("/stats/daily")
async def get_daily_message_stats(days: int = 7, current_user = Depends(auth.get_current_active_user)):
    """Get daily message statistics for the last N days."""
    if not auth.check_permission(current_user, "messages:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    from datetime import datetime, timedelta

    daily_stats = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).date()
        count = database.get_message_count_for_date(date)
        daily_stats.append({
            "date": date.isoformat(),
            "message_count": count
        })

    return {"daily_stats": daily_stats}