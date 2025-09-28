from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
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
    """Send a command to the bot."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="command",
        resource="bot",
        details=f"Sent command: {command.command} with params: {command.parameters}"
    )

    return {"message": f"Command '{command.command}' logged", "status": "queued"}

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
    """Restart the bot."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="restart",
        resource="bot",
        details="Initiated bot restart"
    )

    return {"message": "Bot restart initiated", "status": "restarting"}

@router.get("/config")
async def get_bot_config(current_user = Depends(auth.get_current_active_user)):
    """Get enhanced bot configuration."""
    if not auth.check_permission(current_user, "bot_controls:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    config = {
        "llm_provider": "openrouter",
        "model": "gpt-5-nano",
        "web_search_enabled": False,
        "tools_enabled": True,
        "supported_languages": ["en", "ru"],
        "supported_trigger_types": ["keyword", "emoji", "location", "time", "user_activity"],
        "supported_channels": ["meshtastic", "websocket", "alert"],
        "max_trigger_priority": 100,
        "default_cooldown": 30
    }

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="view",
        resource="config",
        details="Viewed enhanced bot configuration"
    )

    return config

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
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    triggers = database.get_all_triggers(limit=limit, offset=offset, active_only=active_only)

    # Parse JSON fields
    for trigger in triggers:
        if trigger['trigger_config']:
            trigger['trigger_config'] = json.loads(trigger['trigger_config'])
        if trigger['conditions']:
            trigger['conditions'] = json.loads(trigger['conditions'])

    return {"triggers": triggers, "total": len(triggers)}

@router.get("/triggers/{trigger_id}")
async def get_trigger(
    trigger_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Get a specific trigger."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    trigger = database.get_trigger(trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    # Parse JSON fields
    if trigger['trigger_config']:
        trigger['trigger_config'] = json.loads(trigger['trigger_config'])
    if trigger['conditions']:
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

    # Build update data
    update_data = {}
    if trigger_update.name is not None:
        update_data['name'] = trigger_update.name
    if trigger_update.description is not None:
        update_data['description'] = trigger_update.description
    if trigger_update.trigger_type is not None:
        update_data['trigger_type'] = trigger_update.trigger_type
    if trigger_update.trigger_config is not None:
        update_data['trigger_config'] = json.dumps(trigger_update.trigger_config)
    if trigger_update.conditions is not None:
        update_data['conditions'] = json.dumps(trigger_update.conditions)
    if trigger_update.priority is not None:
        update_data['priority'] = trigger_update.priority
    if trigger_update.cooldown_seconds is not None:
        update_data['cooldown_seconds'] = trigger_update.cooldown_seconds
    if trigger_update.is_active is not None:
        update_data['is_active'] = trigger_update.is_active

    success = database.update_trigger(trigger_id, **update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update trigger")

    # Log audit
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

    # Log audit
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

    # Get trigger configuration
    trigger = database.get_trigger(trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    # Import trigger system for testing
    from backend.triggers import test_trigger_conditions

    # Test the trigger
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

    # Log audit
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

    # Parse JSON fields
    for response in responses:
        if response['variables']:
            response['variables'] = json.loads(response['variables'])
        if response['target_ids']:
            response['target_ids'] = json.loads(response['target_ids'])
        if response['channels']:
            response['channels'] = json.loads(response['channels'])

    return {"responses": responses, "total": len(responses)}

@router.get("/responses/{response_id}")
async def get_response(
    response_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Get a specific response."""
    if not auth.check_permission(current_user, "bot_controls"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    response = database.get_response(response_id)
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    # Parse JSON fields
    if response['variables']:
        response['variables'] = json.loads(response['variables'])
    if response['target_ids']:
        response['target_ids'] = json.loads(response['target_ids'])
    if response['channels']:
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

    # Build update data
    update_data = {}
    if response_update.name is not None:
        update_data['name'] = response_update.name
    if response_update.description is not None:
        update_data['description'] = response_update.description
    if response_update.response_type is not None:
        update_data['response_type'] = response_update.response_type
    if response_update.content is not None:
        update_data['content'] = response_update.content
    if response_update.variables is not None:
        update_data['variables'] = json.dumps(response_update.variables)
    if response_update.language is not None:
        update_data['language'] = response_update.language
    if response_update.target_type is not None:
        update_data['target_type'] = response_update.target_type
    if response_update.target_ids is not None:
        update_data['target_ids'] = json.dumps(response_update.target_ids)
    if response_update.channels is not None:
        update_data['channels'] = json.dumps(response_update.channels)
    if response_update.priority is not None:
        update_data['priority'] = response_update.priority
    if response_update.is_active is not None:
        update_data['is_active'] = response_update.is_active

    success = database.update_response(response_id, **update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update response")

    # Log audit
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

    # Log audit
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

    # Calculate analytics
    analytics = {
        "total_executions": len(logs),
        "successful_executions": len([log for log in logs if log['success']]),
        "failed_executions": len([log for log in logs if not log['success']]),
        "average_execution_time": sum(log['execution_time_ms'] for log in logs if log['execution_time_ms']) / len([log for log in logs if log['execution_time_ms']]) if logs else 0,
        "recent_logs": logs[:10]  # Last 10 executions
    }

    return analytics

@router.get("/response-suggestions")
async def get_response_suggestions(
    trigger_type: str = Query(..., description="Type of trigger (location, emergency, help_request, etc.)"),
    user_id: Optional[str] = Query(None, description="User ID for context"),
    zone_id: Optional[str] = Query(None, description="Zone ID for context"),
    language: str = Query("en", description="Language for suggestions"),
    count: int = Query(3, ge=1, le=10, description="Number of suggestions to generate"),
    current_user = Depends(auth.get_current_active_user)
):
    """Get AI-powered response suggestions for bot interactions."""
    if not auth.check_permission(current_user, "bot_controls:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        from backend.bot_responses import response_manager

        # Create mock trigger result for suggestions
        mock_trigger_result = {
            'trigger': {
                'trigger_type': trigger_type,
                'name': f'{trigger_type} trigger'
            },
            'user_id': user_id,
            'zone_id': zone_id
        }

        # Generate suggestions
        suggestions = response_manager.generator.generate_response_suggestions(
            trigger_result=mock_trigger_result,
            context={'language': language},
            language=language,
            count=count
        )

        return {
            "suggestions": suggestions,
            "trigger_type": trigger_type,
            "language": language,
            "count": len(suggestions)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating suggestions: {str(e)}")

@router.get("/template-functions")
async def get_template_functions(
    current_user = Depends(auth.get_current_active_user)
):
    """Get available template functions for bot responses."""
    if not auth.check_permission(current_user, "bot_controls:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    from backend.bot_responses import response_manager

    functions = list(response_manager.generator.template_functions.keys())

    return {
        "functions": functions,
        "descriptions": {
            "time_of_day": "Get current time of day (morning, afternoon, evening, night)",
            "weather_info": "Get weather information for current location",
            "battery_status": "Get battery status description",
            "distance_to": "Calculate distance to a target location",
            "random_greeting": "Get a random greeting",
            "zone_safety": "Get safety information for current zone",
            "emergency_contacts": "Get emergency contact information",
            "user_history": "Get user interaction history summary",
            "predictive_help": "Get predictive help based on user behavior"
        }
    }

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

    # Calculate analytics
    analytics = {
        "total_deliveries": len(logs),
        "successful_deliveries": len([log for log in logs if log['delivery_status'] == 'delivered']),
        "failed_deliveries": len([log for log in logs if log['delivery_status'] == 'failed']),
        "average_delivery_time": sum(log['delivery_time_ms'] for log in logs if log['delivery_time_ms']) / len([log for log in logs if log['delivery_time_ms']]) if logs else 0,
        "recent_logs": logs[:10]
    }

    return analytics