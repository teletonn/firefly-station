from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import yaml
import datetime
from backend import database, auth

router = APIRouter()

# Pydantic Models
class BotCommand(BaseModel):
    command: str
    parameters: dict = {}

class TriggerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str  # 'keyword', 'emoji', 'location', 'time', 'user_activity'
    trigger_config: Dict[str, Any]
    conditions: Optional[Dict[str, Any]] = None
    priority: int = 0
    cooldown_seconds: int = 0

class TriggerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[Dict[str, Any]] = None
    conditions: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    cooldown_seconds: Optional[int] = None
    is_active: Optional[bool] = None

class ResponseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    response_type: str  # 'text', 'template', 'dynamic'
    content: str
    variables: Optional[Dict[str, Any]] = None
    language: str = 'en'
    target_type: str = 'all'  # 'all', 'user', 'group', 'zone'
    target_ids: Optional[List[str]] = None
    channels: Optional[List[str]] = None
    priority: int = 0

class ResponseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    response_type: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    language: Optional[str] = None
    target_type: Optional[str] = None
    target_ids: Optional[List[str]] = None
    channels: Optional[List[str]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None

class TriggerTest(BaseModel):
    message_text: str
    user_id: Optional[str] = None
    location_data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

# Enhanced Bot Status and Management
@router.get("/status")
async def get_bot_status(current_user = Depends(auth.get_current_active_user)):
    """Get enhanced bot status and statistics."""
    if not auth.check_permission(current_user, "bot_controls:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    stats = database.get_bot_stats()

    # Get trigger and response statistics
    trigger_stats = {
        "total_triggers": len(database.get_all_triggers(limit=1000, active_only=False)),
        "active_triggers": len(database.get_all_triggers(limit=1000, active_only=True)),
        "total_responses": len(database.get_all_responses(limit=1000, active_only=False)),
        "active_responses": len(database.get_all_responses(limit=1000, active_only=True))
    }

    # Get recent trigger logs
    recent_logs = database.get_trigger_logs(limit=10)

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="view",
        resource="bot_status",
        details="Viewed enhanced bot status"
    )

    return {
        "status": "running",
        "stats": stats,
        "trigger_stats": trigger_stats,
        "recent_activity": recent_logs,
        "uptime": "N/A"
    }

@router.post("/command")
async def send_bot_command(
    command: BotCommand,
    current_user = Depends(auth.get_current_active_user)
):
    """Send a command to the bot via the database queue."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    command_id = database.add_to_bot_command_queue(command.command, command.parameters)
    if not command_id:
        raise HTTPException(status_code=500, detail="Failed to queue command for the bot")

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="command",
        resource="bot",
        details=f"Queued command: {command.command} with params: {command.parameters}"
    )

    return {"message": f"Command '{command.command}' queued for execution.", "status": "queued", "command_id": command_id}

@router.get("/sessions")
async def get_active_sessions(current_user = Depends(auth.get_current_active_user)):
    """Get active user sessions."""
    if not auth.check_permission(current_user, "bot_controls:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    sessions = database.get_all_sessions(limit=50, offset=0)

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="view",
        resource="sessions",
        details=f"Viewed {len(sessions)} sessions"
    )

    return {"sessions": sessions}

@router.post("/restart")
async def restart_bot(current_user = Depends(auth.get_current_active_user)):
    """Logs a restart request for the bot."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="restart_request",
        resource="bot",
        details="Bot restart requested by admin"
    )

    return {"message": "Bot restart request logged. Please restart the application service manually for changes to take effect.", "status": "logged"}

@router.get("/config")
async def get_bot_config(current_user = Depends(auth.get_current_active_user)):
    """Get bot-related configuration from config.yaml."""
    if not auth.check_permission(current_user, "bot_controls:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="config.yaml not found")

    bot_config = {
        "llm_provider": config_data.get("llm_provider"),
        "model": config_data.get("model"),
        "message_delivery": config_data.get("message_delivery"),
        "tools": config_data.get("tools")
    }

    database.log_audit(
        admin_user_id=current_user['id'],
        action="view",
        resource="config",
        details="Viewed bot configuration"
    )

    return bot_config

# Trigger Management Endpoints
@router.post("/triggers")
async def create_trigger(
    trigger: TriggerCreate,
    current_user = Depends(auth.get_current_active_user)
):
    """Create a new trigger."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    trigger_id = database.create_trigger(
        name=trigger.name,
        description=trigger.description,
        trigger_type=trigger.trigger_type,
        trigger_config=json.dumps(trigger.trigger_config),
        conditions=json.dumps(trigger.conditions) if trigger.conditions else None,
        priority=trigger.priority,
        cooldown_seconds=trigger.cooldown_seconds,
        created_by=current_user['id']
    )

    if not trigger_id:
        raise HTTPException(status_code=500, detail="Failed to create trigger")

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="create",
        resource="trigger",
        resource_id=str(trigger_id),
        details=f"Created trigger: {trigger.name}"
    )

    return {"id": trigger_id, "message": "Trigger created successfully"}

@router.get("/triggers")
async def get_triggers(
    limit: int = 50,
    offset: int = 0,
    active_only: bool = True,
    current_user = Depends(auth.get_current_active_user)
):
    """Get all triggers with pagination."""
    if not auth.check_permission(current_user, "bot_controls:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    triggers = database.get_all_triggers(limit=limit, offset=offset, active_only=active_only)

    # Parse JSON fields
    for trigger in triggers:
        if trigger.get('trigger_config'):
            trigger['trigger_config'] = json.loads(trigger['trigger_config'])
        if trigger.get('conditions'):
            trigger['conditions'] = json.loads(trigger['conditions'])

    return {"triggers": triggers, "total": len(triggers)}

@router.get("/triggers/{trigger_id}")
async def get_trigger(
    trigger_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Get a specific trigger."""
    if not auth.check_permission(current_user, "bot_controls:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    trigger = database.get_trigger(trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    # Parse JSON fields
    if trigger.get('trigger_config'):
        trigger['trigger_config'] = json.loads(trigger['trigger_config'])
    if trigger.get('conditions'):
        trigger['conditions'] = json.loads(trigger['conditions'])

    return trigger

@router.put("/triggers/{trigger_id}")
async def update_trigger(
    trigger_id: int,
    trigger_update: TriggerUpdate,
    current_user = Depends(auth.get_current_active_user)
):
    """Update a trigger."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    update_data = trigger_update.dict(exclude_unset=True)
    if 'trigger_config' in update_data:
        update_data['trigger_config'] = json.dumps(update_data['trigger_config'])
    if 'conditions' in update_data:
        update_data['conditions'] = json.dumps(update_data['conditions'])

    success = database.update_trigger(trigger_id, **update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update trigger")

    database.log_audit(
        admin_user_id=current_user['id'],
        action="update",
        resource="trigger",
        resource_id=str(trigger_id),
        details=f"Updated trigger: {trigger_update.name or trigger_id}"
    )

    return {"message": "Trigger updated successfully"}

@router.delete("/triggers/{trigger_id}")
async def delete_trigger(
    trigger_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Delete a trigger."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    success = database.delete_trigger(trigger_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete trigger")

    database.log_audit(
        admin_user_id=current_user['id'],
        action="delete",
        resource="trigger",
        resource_id=str(trigger_id),
        details="Deleted trigger"
    )

    return {"message": "Trigger deleted successfully"}

@router.post("/triggers/{trigger_id}/test")
async def test_trigger(
    trigger_id: int,
    test_data: TriggerTest,
    current_user = Depends(auth.get_current_active_user)
):
    """Test a trigger with sample data."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    trigger = database.get_trigger(trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    from backend.triggers import test_trigger_conditions

    result = test_trigger_conditions(
        trigger_config=json.loads(trigger['trigger_config']),
        conditions=json.loads(trigger['conditions']) if trigger['conditions'] else None,
        message_text=test_data.message_text,
        user_id=test_data.user_id,
        location_data=test_data.location_data,
        timestamp=test_data.timestamp
    )

    return {
        "trigger_id": trigger_id,
        "trigger_name": trigger['name'],
        "test_result": result,
        "test_input": test_data.dict()
    }

# Response Management Endpoints
@router.post("/responses")
async def create_response(
    response: ResponseCreate,
    current_user = Depends(auth.get_current_active_user)
):
    """Create a new response."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    response_id = database.create_response(
        name=response.name,
        description=response.description,
        response_type=response.response_type,
        content=response.content,
        variables=json.dumps(response.variables) if response.variables else None,
        language=response.language,
        target_type=response.target_type,
        target_ids=json.dumps(response.target_ids) if response.target_ids else None,
        channels=json.dumps(response.channels) if response.channels else None,
        priority=response.priority,
        created_by=current_user['id']
    )

    if not response_id:
        raise HTTPException(status_code=500, detail="Failed to create response")

    database.log_audit(
        admin_user_id=current_user['id'],
        action="create",
        resource="response",
        resource_id=str(response_id),
        details=f"Created response: {response.name}"
    )

    return {"id": response_id, "message": "Response created successfully"}

@router.get("/responses")
async def get_responses(
    limit: int = 50,
    offset: int = 0,
    active_only: bool = True,
    current_user = Depends(auth.get_current_active_user)
):
    """Get all responses with pagination."""
    if not auth.check_permission(current_user, "bot_controls:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    responses = database.get_all_responses(limit=limit, offset=offset, active_only=active_only)

    for response in responses:
        if response.get('variables'):
            response['variables'] = json.loads(response['variables'])
        if response.get('target_ids'):
            response['target_ids'] = json.loads(response['target_ids'])
        if response.get('channels'):
            response['channels'] = json.loads(response['channels'])

    return {"responses": responses, "total": len(responses)}

@router.get("/responses/{response_id}")
async def get_response(
    response_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Get a specific response."""
    if not auth.check_permission(current_user, "bot_controls:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    response = database.get_response(response_id)
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    if response.get('variables'):
        response['variables'] = json.loads(response['variables'])
    if response.get('target_ids'):
        response['target_ids'] = json.loads(response['target_ids'])
    if response.get('channels'):
        response['channels'] = json.loads(response['channels'])

    return response

@router.put("/responses/{response_id}")
async def update_response(
    response_id: int,
    response_update: ResponseUpdate,
    current_user = Depends(auth.get_current_active_user)
):
    """Update a response."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    update_data = response_update.dict(exclude_unset=True)
    for field in ['variables', 'target_ids', 'channels']:
        if field in update_data:
            update_data[field] = json.dumps(update_data[field])

    success = database.update_response(response_id, **update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update response")

    database.log_audit(
        admin_user_id=current_user['id'],
        action="update",
        resource="response",
        resource_id=str(response_id),
        details=f"Updated response: {response_update.name or response_id}"
    )

    return {"message": "Response updated successfully"}

@router.delete("/responses/{response_id}")
async def delete_response(
    response_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Delete a response."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    success = database.delete_response(response_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete response")

    database.log_audit(
        admin_user_id=current_user['id'],
        action="delete",
        resource="response",
        resource_id=str(response_id),
        details="Deleted response"
    )

    return {"message": "Response deleted successfully"}

# Analytics and Monitoring Endpoints
@router.get("/analytics/triggers")
async def get_trigger_analytics(
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(auth.get_current_active_user)
):
    """Get trigger analytics and performance metrics."""
    if not auth.check_permission(current_user, "bot_controls:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    logs = database.get_trigger_logs(limit=limit, offset=offset)

    analytics = {
        "total_executions": len(logs),
        "successful_executions": len([log for log in logs if log['success']]),
        "failed_executions": len([log for log in logs if not log['success']]),
        "average_execution_time": sum(log['execution_time_ms'] for log in logs if log['execution_time_ms']) / len([log for log in logs if log['execution_time_ms']]) if logs else 0,
        "recent_logs": logs[:10]
    }

    return analytics

@router.get("/analytics/responses")
async def get_response_analytics(
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(auth.get_current_active_user)
):
    """Get response analytics and delivery metrics."""
    if not auth.check_permission(current_user, "bot_controls:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    logs = database.get_response_logs(limit=limit, offset=offset)

    analytics = {
        "total_deliveries": len(logs),
        "successful_deliveries": len([log for log in logs if log['delivery_status'] == 'delivered']),
        "failed_deliveries": len([log for log in logs if log['delivery_status'] == 'failed']),
        "average_delivery_time": sum(log['delivery_time_ms'] for log in logs if log['delivery_time_ms']) / len([log for log in logs if log['delivery_time_ms']]) if logs else 0,
        "recent_logs": logs[:10]
    }

    return analytics