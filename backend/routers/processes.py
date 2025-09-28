from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from backend import database, auth
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def get_processes(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(True),
    template_id: Optional[int] = Query(None),
    created_by: Optional[int] = Query(None),
    current_user = Depends(auth.get_current_active_user)
):
    """Get all processes with filtering and pagination."""
    if not auth.check_permission(current_user, "processes:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT p.*, pt.name as template_name, au.username as created_by_username
        FROM processes p
        LEFT JOIN process_templates pt ON p.template_id = pt.id
        LEFT JOIN admin_users au ON p.created_by = au.id
    '''
    params = []
    conditions = []

    if active_only:
        conditions.append('p.is_active = TRUE')
    if template_id:
        conditions.append('p.template_id = ?')
        params.append(template_id)
    if created_by:
        conditions.append('p.created_by = ?')
        params.append(created_by)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    query += ' ORDER BY p.created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(query, params)
    processes = [dict(row) for row in cursor.fetchall()]

    # Get total count
    count_query = 'SELECT COUNT(*) as total FROM processes p'
    if conditions:
        count_query += ' WHERE ' + ' AND '.join(conditions)

    cursor.execute(count_query, params[:-2] if params else [])
    total = cursor.fetchone()['total']

    conn.close()
    return {
        "processes": processes,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/{process_id}")
async def get_process(
    process_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Get process details with triggers and actions."""
    if not auth.check_permission(current_user, "processes:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    # Get process
    cursor.execute('''
        SELECT p.*, pt.name as template_name, au.username as created_by_username
        FROM processes p
        LEFT JOIN process_templates pt ON p.template_id = pt.id
        LEFT JOIN admin_users au ON p.created_by = au.id
        WHERE p.id = ?
    ''', (process_id,))

    process = cursor.fetchone()
    if not process:
        conn.close()
        raise HTTPException(status_code=404, detail="Process not found")

    process = dict(process)

    # Get triggers
    cursor.execute('SELECT * FROM process_triggers WHERE process_id = ? ORDER BY priority DESC, created_at ASC', (process_id,))
    triggers = [dict(row) for row in cursor.fetchall()]

    # Get actions
    cursor.execute('SELECT * FROM process_actions WHERE process_id = ? ORDER BY action_order ASC', (process_id,))
    actions = [dict(row) for row in cursor.fetchall()]

    conn.close()

    process['triggers'] = triggers
    process['actions'] = actions

    return process

@router.post("/")
async def create_process(
    name: str = Body(...),
    description: Optional[str] = Body(None),
    template_id: Optional[int] = Body(None),
    triggers: List[Dict[str, Any]] = Body(default=[]),
    actions: List[Dict[str, Any]] = Body(default=[]),
    current_user = Depends(auth.get_current_active_user)
):
    """Create a new process."""
    if not auth.check_permission(current_user, "processes:create"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    try:
        # Create process
        cursor.execute('''
            INSERT INTO processes (name, description, template_id, created_by)
            VALUES (?, ?, ?, ?)
        ''', (name, description, template_id, current_user['id']))

        process_id = cursor.lastrowid

        # Add triggers
        for trigger in triggers:
            cursor.execute('''
                INSERT INTO process_triggers (process_id, trigger_type, trigger_config, conditions, priority, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                process_id,
                trigger['trigger_type'],
                json.dumps(trigger.get('trigger_config', {})),
                json.dumps(trigger.get('conditions', {})),
                trigger.get('priority', 0),
                trigger.get('is_active', True)
            ))

        # Add actions
        for action in actions:
            cursor.execute('''
                INSERT INTO process_actions (process_id, action_type, action_config, conditions, action_order, timeout_seconds, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                process_id,
                action['action_type'],
                json.dumps(action.get('action_config', {})),
                json.dumps(action.get('conditions', {})),
                action['action_order'],
                action.get('timeout_seconds', 30),
                action.get('retry_count', 0)
            ))

        conn.commit()

        # Log audit
        database.log_audit(
            admin_user_id=current_user['id'],
            action="create",
            resource="process",
            resource_id=str(process_id),
            details=f"Created process '{name}'"
        )

        return {"process_id": process_id}

    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating process: {e}")
        raise HTTPException(status_code=500, detail="Failed to create process")
    finally:
        conn.close()

@router.put("/{process_id}")
async def update_process(
    process_id: int,
    name: str = Body(...),
    description: Optional[str] = Body(None),
    template_id: Optional[int] = Body(None),
    triggers: List[Dict[str, Any]] = Body(default=[]),
    actions: List[Dict[str, Any]] = Body(default=[]),
    current_user = Depends(auth.get_current_active_user)
):
    """Update an existing process."""
    if not auth.check_permission(current_user, "processes:update"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    try:
        # Update process
        cursor.execute('''
            UPDATE processes SET name = ?, description = ?, template_id = ?, updated_at = ?
            WHERE id = ?
        ''', (name, description, template_id, datetime.now(), process_id))

        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Process not found")

        # Delete existing triggers and actions
        cursor.execute('DELETE FROM process_triggers WHERE process_id = ?', (process_id,))
        cursor.execute('DELETE FROM process_actions WHERE process_id = ?', (process_id,))

        # Add new triggers
        for trigger in triggers:
            cursor.execute('''
                INSERT INTO process_triggers (process_id, trigger_type, trigger_config, conditions, priority, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                process_id,
                trigger['trigger_type'],
                json.dumps(trigger.get('trigger_config', {})),
                json.dumps(trigger.get('conditions', {})),
                trigger.get('priority', 0),
                trigger.get('is_active', True)
            ))

        # Add new actions
        for action in actions:
            cursor.execute('''
                INSERT INTO process_actions (process_id, action_type, action_config, conditions, action_order, timeout_seconds, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                process_id,
                action['action_type'],
                json.dumps(action.get('action_config', {})),
                json.dumps(action.get('conditions', {})),
                action['action_order'],
                action.get('timeout_seconds', 30),
                action.get('retry_count', 0)
            ))

        conn.commit()

        # Log audit
        database.log_audit(
            admin_user_id=current_user['id'],
            action="update",
            resource="process",
            resource_id=str(process_id),
            details=f"Updated process '{name}'"
        )

        return {"message": "Process updated successfully"}

    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating process: {e}")
        raise HTTPException(status_code=500, detail="Failed to update process")
    finally:
        conn.close()

@router.delete("/{process_id}")
async def delete_process(
    process_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Deactivate a process."""
    if not auth.check_permission(current_user, "processes:delete"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute('UPDATE processes SET is_active = FALSE WHERE id = ?', (process_id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Process not found")

    conn.commit()
    conn.close()

    # Log audit
    database.log_audit(
        admin_user_id=current_user['id'],
        action="delete",
        resource="process",
        resource_id=str(process_id),
        details="Deactivated process"
    )

    return {"message": "Process deactivated successfully"}

@router.post("/{process_id}/execute")
async def execute_process(
    process_id: int,
    trigger_data: Dict[str, Any] = Body(default={}),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Manually execute a process."""
    if not auth.check_permission(current_user, "processes:execute"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    try:
        # Create execution record
        cursor.execute('''
            INSERT INTO process_executions (process_id, triggered_by, trigger_event, status)
            VALUES (?, ?, ?, 'running')
        ''', (process_id, str(current_user['id']), json.dumps(trigger_data)))
        execution_id = cursor.lastrowid

        # Get process actions
        cursor.execute('SELECT * FROM process_actions WHERE process_id = ? ORDER BY action_order ASC', (process_id,))
        actions = cursor.fetchall()

        # Execute actions
        for action in actions:
            action_config = json.loads(action['action_config'])
            action_type = action['action_type']
            result = {}
            status = 'completed'
            error_message = None

            try:
                if action_type == 'send_message':
                    to_id = action_config.get('to_id')
                    message = action_config.get('message')
                    if to_id and message:
                        database.add_to_outgoing_queue(to_id, message)
                        result = {"status": "queued"}
                    else:
                        raise ValueError("Missing 'to_id' or 'message' in action config")

                elif action_type == 'create_alert':
                    database.create_alert(
                        user_id=action_config.get('user_id'),
                        zone_id=action_config.get('zone_id'),
                        alert_type=action_config.get('alert_type', 'process_generated'),
                        title=action_config.get('title', 'Process Alert'),
                        message=action_config.get('message', 'Alert from process'),
                        severity=action_config.get('severity', 'medium')
                    )
                    result = {"status": "alert_created"}

                # Add other action handlers here
                else:
                    status = 'failed'
                    error_message = f"Unknown action type: {action_type}"

            except Exception as e:
                status = 'failed'
                error_message = str(e)
                logger.error(f"Error executing action {action['id']}: {e}")

            # Record step execution
            cursor.execute('''
                INSERT INTO process_execution_steps (execution_id, action_id, status, result, error_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (execution_id, action['id'], status, json.dumps(result), error_message))

        # Update execution status
        cursor.execute("SELECT COUNT(*) as failed_steps FROM process_execution_steps WHERE execution_id = ? AND status = 'failed'", (execution_id,))
        failed_steps = cursor.fetchone()['failed_steps']
        final_status = 'failed' if failed_steps > 0 else 'completed'

        cursor.execute('''
            UPDATE process_executions SET status = ?, completed_at = ?, steps_completed = ?, total_steps = ?
            WHERE id = ?
        ''', (final_status, datetime.now(), len(actions), len(actions), execution_id))

        # Update process stats
        cursor.execute('''
            UPDATE processes SET execution_count = execution_count + 1, last_executed = ?
            WHERE id = ?
        ''', (datetime.now(), process_id))

        conn.commit()

        # Log audit
        database.log_audit(
            admin_user_id=current_user['id'],
            action="execute",
            resource="process",
            resource_id=str(process_id),
            details=f"Manually executed process, execution_id: {execution_id}"
        )

        return {"execution_id": execution_id, "status": final_status}

    except Exception as e:
        conn.rollback()
        logger.error(f"Error executing process: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute process")
    finally:
        conn.close()

@router.get("/executions/")
async def get_process_executions(
    process_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user = Depends(auth.get_current_active_user)
):
    """Get process executions."""
    if not auth.check_permission(current_user, "processes:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT pe.*, p.name as process_name, au.username as triggered_by_username
        FROM process_executions pe
        JOIN processes p ON pe.process_id = p.id
        LEFT JOIN admin_users au ON pe.triggered_by = au.username
    '''
    params = []
    conditions = []

    if process_id:
        conditions.append('pe.process_id = ?')
        params.append(process_id)
    if status:
        conditions.append('pe.status = ?')
        params.append(status)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    query += ' ORDER BY pe.started_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(query, params)
    executions = [dict(row) for row in cursor.fetchall()]

    # Get total count
    count_query = 'SELECT COUNT(*) as total FROM process_executions pe'
    if conditions:
        count_query += ' WHERE ' + ' AND '.join(conditions)

    cursor.execute(count_query, params[:-2] if params else [])
    total = cursor.fetchone()['total']

    conn.close()
    return {
        "executions": executions,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/executions/{execution_id}")
async def get_process_execution(
    execution_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Get execution details with steps."""
    if not auth.check_permission(current_user, "processes:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    # Get execution
    cursor.execute('''
        SELECT pe.*, p.name as process_name
        FROM process_executions pe
        JOIN processes p ON pe.process_id = p.id
        WHERE pe.id = ?
    ''', (execution_id,))

    execution = cursor.fetchone()
    if not execution:
        conn.close()
        raise HTTPException(status_code=404, detail="Execution not found")

    execution = dict(execution)

    # Get steps
    cursor.execute('''
        SELECT pes.*, pa.action_type, pa.action_config
        FROM process_execution_steps pes
        JOIN process_actions pa ON pes.action_id = pa.id
        WHERE pes.execution_id = ?
        ORDER BY pes.started_at ASC
    ''', (execution_id,))

    steps = [dict(row) for row in cursor.fetchall()]

    conn.close()

    execution['steps'] = steps
    return execution

@router.get("/executions/{execution_id}/logs")
async def get_execution_logs(
    execution_id: int,
    current_user = Depends(auth.get_current_active_user)
):
    """Get execution logs."""
    if not auth.check_permission(current_user, "processes:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM process_execution_steps
        WHERE execution_id = ?
        ORDER BY started_at ASC
    ''', (execution_id,))

    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {"logs": logs}

@router.get("/templates/")
async def get_process_templates(
    category: Optional[str] = Query(None),
    current_user = Depends(auth.get_current_active_user)
):
    """Get available process templates."""
    if not auth.check_permission(current_user, "processes:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT pt.*, au.username as created_by_username
        FROM process_templates pt
        LEFT JOIN admin_users au ON pt.created_by = au.id
        WHERE pt.is_public = TRUE
    '''
    params = []

    if category:
        query += ' AND pt.category = ?'
        params.append(category)

    query += ' ORDER BY pt.usage_count DESC, pt.created_at DESC'

    cursor.execute(query, params)
    templates = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return {"templates": templates}

@router.post("/templates/")
async def create_process_template(
    process_id: int = Body(...),
    name: str = Body(...),
    description: Optional[str] = Body(None),
    category: str = Body(...),
    current_user = Depends(auth.get_current_active_user)
):
    """Create template from existing process."""
    if not auth.check_permission(current_user, "processes:create"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    try:
        # Get process data
        cursor.execute('''
            SELECT p.*, pt.trigger_type, pt.trigger_config, pt.conditions, pa.action_type, pa.action_config, pa.action_order, pa.timeout_seconds, pa.retry_count
            FROM processes p
            LEFT JOIN process_triggers pt ON p.id = pt.process_id
            LEFT JOIN process_actions pa ON p.id = pa.process_id
            WHERE p.id = ?
        ''', (process_id,))

        rows = cursor.fetchall()
        if not rows:
            conn.close()
            raise HTTPException(status_code=404, detail="Process not found")

        # Build template data
        process_data = dict(rows[0])
        template_data = {
            "name": process_data['name'],
            "description": process_data['description'],
            "triggers": [],
            "actions": []
        }

        for row in rows:
            if row['trigger_type']:
                template_data['triggers'].append({
                    "trigger_type": row['trigger_type'],
                    "trigger_config": json.loads(row['trigger_config'] or '{}'),
                    "conditions": json.loads(row['conditions'] or '{}')
                })
            if row['action_type']:
                template_data['actions'].append({
                    "action_type": row['action_type'],
                    "action_config": json.loads(row['action_config'] or '{}'),
                    "action_order": row['action_order'],
                    "timeout_seconds": row['timeout_seconds'],
                    "retry_count": row['retry_count']
                })

        # Create template
        cursor.execute('''
            INSERT INTO process_templates (name, description, category, template_data, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, category, json.dumps(template_data), current_user['id']))

        template_id = cursor.lastrowid
        conn.commit()

        # Log audit
        database.log_audit(
            admin_user_id=current_user['id'],
            action="create",
            resource="process_template",
            resource_id=str(template_id),
            details=f"Created template '{name}' from process {process_id}"
        )

        return {"template_id": template_id}

    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create template")
    finally:
        conn.close()

@router.post("/templates/{template_id}/instantiate")
async def instantiate_template(
    template_id: int,
    customizations: Dict[str, Any] = Body(default={}),
    current_user = Depends(auth.get_current_active_user)
):
    """Create process from template."""
    if not auth.check_permission(current_user, "processes:create"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    try:
        # Get template
        cursor.execute('SELECT * FROM process_templates WHERE id = ? AND is_public = TRUE', (template_id,))
        template = cursor.fetchone()
        if not template:
            conn.close()
            raise HTTPException(status_code=404, detail="Template not found")

        template_data = json.loads(template['template_data'])

        # Apply customizations
        name = customizations.get('name', template_data.get('name', 'New Process'))
        description = customizations.get('description', template_data.get('description'))

        # Create process
        cursor.execute('''
            INSERT INTO processes (name, description, template_id, created_by)
            VALUES (?, ?, ?, ?)
        ''', (name, description, template_id, current_user['id']))

        process_id = cursor.lastrowid

        # Add triggers
        for trigger in template_data.get('triggers', []):
            cursor.execute('''
                INSERT INTO process_triggers (process_id, trigger_type, trigger_config, conditions, priority, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                process_id,
                trigger['trigger_type'],
                json.dumps(trigger.get('trigger_config', {})),
                json.dumps(trigger.get('conditions', {})),
                trigger.get('priority', 0),
                trigger.get('is_active', True)
            ))

        # Add actions
        for action in template_data.get('actions', []):
            cursor.execute('''
                INSERT INTO process_actions (process_id, action_type, action_config, conditions, action_order, timeout_seconds, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                process_id,
                action['action_type'],
                json.dumps(action.get('action_config', {})),
                json.dumps(action.get('conditions', {})),
                action['action_order'],
                action.get('timeout_seconds', 30),
                action.get('retry_count', 0)
            ))

        # Update template usage count
        cursor.execute('UPDATE process_templates SET usage_count = usage_count + 1 WHERE id = ?', (template_id,))

        conn.commit()

        # Log audit
        database.log_audit(
            admin_user_id=current_user['id'],
            action="instantiate",
            resource="process_template",
            resource_id=str(template_id),
            details=f"Instantiated template to create process {process_id}"
        )

        return {"process_id": process_id}

    except Exception as e:
        conn.rollback()
        logger.error(f"Error instantiating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to instantiate template")
    finally:
        conn.close()

@router.get("/analytics/overview")
async def get_process_analytics_overview(
    days: int = Query(30, ge=1, le=365),
    current_user = Depends(auth.get_current_active_user)
):
    """Get system-wide process analytics."""
    if not auth.check_permission(current_user, "processes:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    # Get total processes
    cursor.execute('SELECT COUNT(*) as total_processes FROM processes WHERE is_active = TRUE')
    total_processes = cursor.fetchone()['total_processes']

    # Get total executions
    cursor.execute('SELECT COUNT(*) as total_executions FROM process_executions')
    total_executions = cursor.fetchone()['total_executions']

    # Get successful executions
    cursor.execute("SELECT COUNT(*) as successful_executions FROM process_executions WHERE status = 'completed'")
    successful_executions = cursor.fetchone()['successful_executions']

    # Calculate success rate
    success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0

    # Get average execution time
    cursor.execute('SELECT AVG(execution_time_ms) as avg_execution_time FROM process_executions WHERE execution_time_ms IS NOT NULL')
    avg_execution_time = cursor.fetchone()['avg_execution_time'] or 0

    # Get recent executions
    start_date = datetime.now() - timedelta(days=days)
    cursor.execute('SELECT COUNT(*) as recent_executions FROM process_executions WHERE started_at >= ?', (start_date,))
    recent_executions = cursor.fetchone()['recent_executions']

    conn.close()

    return {
        "total_processes": total_processes,
        "total_executions": total_executions,
        "success_rate": success_rate,
        "avg_execution_time": avg_execution_time,
        "recent_executions": recent_executions,
        "period_days": days
    }

@router.get("/{process_id}/analytics")
async def get_process_analytics(
    process_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user = Depends(auth.get_current_active_user)
):
    """Get process-specific analytics."""
    if not auth.check_permission(current_user, "processes:read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    conn = database.get_connection()
    cursor = conn.cursor()

    # Get process executions
    cursor.execute('SELECT COUNT(*) as execution_count FROM process_executions WHERE process_id = ?', (process_id,))
    execution_count = cursor.fetchone()['execution_count']

    # Get successful executions
    cursor.execute("SELECT COUNT(*) as successful FROM process_executions WHERE process_id = ? AND status = 'completed'", (process_id,))
    successful = cursor.fetchone()['successful']

    # Calculate success rate
    success_rate = (successful / execution_count * 100) if execution_count > 0 else 0

    # Get average execution time
    cursor.execute('SELECT AVG(execution_time_ms) as avg_execution_time FROM process_executions WHERE process_id = ? AND execution_time_ms IS NOT NULL', (process_id,))
    avg_execution_time = cursor.fetchone()['avg_execution_time'] or 0

    # Get failure reasons
    cursor.execute("SELECT error_message, COUNT(*) as count FROM process_executions WHERE process_id = ? AND status != 'completed' AND error_message IS NOT NULL GROUP BY error_message ORDER BY count DESC LIMIT 10", (process_id,))
    failure_reasons = [{"reason": row['error_message'], "count": row['count']} for row in cursor.fetchall()]

    conn.close()

    return {
        "execution_count": execution_count,
        "success_rate": success_rate,
        "avg_execution_time": avg_execution_time,
        "failure_reasons": failure_reasons
    }