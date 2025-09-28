import re
import json
import datetime
import time
import emoji
from typing import Dict, List, Optional, Any, Tuple
from backend import database

class TriggerEngine:
    """Advanced trigger detection and processing engine."""

    def __init__(self):
        self.trigger_cache = {}
        self.cooldown_cache = {}

    def load_active_triggers(self) -> List[Dict[str, Any]]:
        """Load all active triggers from database."""
        triggers = database.get_all_triggers(active_only=True)
        for trigger in triggers:
            if trigger['trigger_config']:
                trigger['trigger_config'] = json.loads(trigger['trigger_config'])
            if trigger['conditions']:
                trigger['conditions'] = json.loads(trigger['conditions'])
        return triggers

    def check_trigger_cooldown(self, trigger_id: int) -> bool:
        """Check if trigger is in cooldown period."""
        current_time = time.time()
        cooldown_key = f"trigger_{trigger_id}"

        if cooldown_key in self.cooldown_cache:
            last_triggered = self.cooldown_cache[cooldown_key]
            # Get cooldown period from trigger config
            trigger = self.trigger_cache.get(trigger_id)
            if trigger:
                cooldown_seconds = trigger.get('cooldown_seconds', 0)
                if current_time - last_triggered < cooldown_seconds:
                    return False

        return True

    def set_trigger_cooldown(self, trigger_id: int):
        """Set trigger cooldown timestamp."""
        self.cooldown_cache[f"trigger_{trigger_id}"] = time.time()

    def process_message(self, message_text: str, user_id: str = None,
                       location_data: Dict[str, Any] = None,
                       timestamp: str = None) -> List[Dict[str, Any]]:
        """Process a message against all active triggers."""
        if not hasattr(self, '_triggers') or not self._triggers:
            self._triggers = self.load_active_triggers()
            self.trigger_cache = {t['id']: t for t in self._triggers}

        triggered = []

        for trigger in self._triggers:
            if not self.check_trigger_cooldown(trigger['id']):
                continue

            result = self.evaluate_trigger(trigger, message_text, user_id, location_data, timestamp)
            if result['matched']:
                triggered.append({
                    'trigger': trigger,
                    'result': result,
                    'message_text': message_text,
                    'user_id': user_id
                })

        # Sort by priority (highest first)
        triggered.sort(key=lambda x: x['trigger']['priority'], reverse=True)

        return triggered

    def evaluate_trigger(self, trigger: Dict[str, Any], message_text: str,
                        user_id: str = None, location_data: Dict[str, Any] = None,
                        timestamp: str = None) -> Dict[str, Any]:
        """Evaluate a single trigger against message data."""
        start_time = time.time()
        trigger_type = trigger['trigger_type']
        config = trigger['trigger_config']
        conditions = trigger.get('conditions', {})

        try:
            if trigger_type == 'keyword':
                result = self._check_keyword_trigger(config, message_text, conditions)
            elif trigger_type == 'emoji':
                result = self._check_emoji_trigger(config, message_text, conditions)
            elif trigger_type == 'location':
                result = self._check_location_trigger(config, location_data, conditions)
            elif trigger_type == 'time':
                result = self._check_time_trigger(config, timestamp, conditions)
            elif trigger_type == 'user_activity':
                result = self._check_user_activity_trigger(config, user_id, conditions)
            else:
                result = {'matched': False, 'reason': f'Unknown trigger type: {trigger_type}'}

            execution_time = int((time.time() - start_time) * 1000)

            return {
                'matched': result['matched'],
                'reason': result.get('reason', ''),
                'matched_conditions': result.get('matched_conditions', []),
                'execution_time_ms': execution_time,
                'trigger_data': result.get('trigger_data', {})
            }

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return {
                'matched': False,
                'reason': f'Error evaluating trigger: {str(e)}',
                'matched_conditions': [],
                'execution_time_ms': execution_time,
                'trigger_data': {}
            }

    def _check_keyword_trigger(self, config: Dict[str, Any], message_text: str,
                              conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Check keyword-based triggers with regex support."""
        keywords = config.get('keywords', [])
        use_regex = config.get('use_regex', False)
        case_sensitive = config.get('case_sensitive', False)
        match_all = config.get('match_all', False)  # AND vs OR logic

        if not case_sensitive:
            message_text = message_text.lower()
            keywords = [k.lower() if isinstance(k, str) else k for k in keywords]

        matched_keywords = []

        for keyword in keywords:
            if use_regex:
                try:
                    pattern = keyword if case_sensitive else f"(?i){keyword}"
                    if re.search(pattern, message_text):
                        matched_keywords.append(keyword)
                except re.error:
                    # Invalid regex, treat as literal text
                    if keyword in message_text:
                        matched_keywords.append(keyword)
            else:
                if keyword in message_text:
                    matched_keywords.append(keyword)

        # Apply match logic
        if match_all:
            matched = len(matched_keywords) == len(keywords)
        else:
            matched = len(matched_keywords) > 0

        return {
            'matched': matched,
            'matched_conditions': matched_keywords,
            'trigger_data': {
                'matched_keywords': matched_keywords,
                'total_keywords': len(keywords),
                'match_logic': 'all' if match_all else 'any'
            }
        }

    def _check_emoji_trigger(self, config: Dict[str, Any], message_text: str,
                            conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Check emoji-based triggers."""
        target_emojis = config.get('emojis', [])
        require_exact = config.get('require_exact', False)

        # Extract emojis from message
        message_emojis = [char for char in message_text if char in emoji.EMOJI_DATA]

        if require_exact:
            # Check if message contains exactly the target emojis
            matched = all(emoji_char in message_emojis for emoji_char in target_emojis)
        else:
            # Check if message contains any of the target emojis
            matched = any(emoji_char in message_emojis for emoji_char in target_emojis)

        return {
            'matched': matched,
            'matched_conditions': [e for e in target_emojis if e in message_emojis],
            'trigger_data': {
                'message_emojis': message_emojis,
                'target_emojis': target_emojis,
                'require_exact': require_exact
            }
        }

    def _check_location_trigger(self, config: Dict[str, Any],
                               location_data: Dict[str, Any],
                               conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Check location-based triggers."""
        if not location_data:
            return {'matched': False, 'reason': 'No location data provided'}

        user_lat = location_data.get('latitude')
        user_lon = location_data.get('longitude')

        if not user_lat or not user_lon:
            return {'matched': False, 'reason': 'Invalid location coordinates'}

        trigger_zones = config.get('zones', [])
        trigger_action = config.get('action', 'enter')  # 'enter', 'exit', 'inside'

        matched_zones = []

        for zone_id in trigger_zones:
            zone = database.get_zone(zone_id)
            if not zone:
                continue

            # Simple point-in-circle calculation
            distance = self._calculate_distance(
                user_lat, user_lon,
                zone['center_latitude'], zone['center_longitude']
            )

            is_inside = distance <= zone['radius_meters']

            if trigger_action == 'enter':
                # Check if user just entered the zone
                # This would require tracking previous location
                if is_inside:
                    matched_zones.append({
                        'zone_id': zone_id,
                        'zone_name': zone['name'],
                        'distance': distance
                    })
            elif trigger_action == 'exit':
                # Check if user just exited the zone
                if not is_inside:
                    matched_zones.append({
                        'zone_id': zone_id,
                        'zone_name': zone['name'],
                        'distance': distance
                    })
            elif trigger_action == 'inside':
                # Check if user is currently inside
                if is_inside:
                    matched_zones.append({
                        'zone_id': zone_id,
                        'zone_name': zone['name'],
                        'distance': distance
                    })

        return {
            'matched': len(matched_zones) > 0,
            'matched_conditions': matched_zones,
            'trigger_data': {
                'user_location': {'lat': user_lat, 'lon': user_lon},
                'matched_zones': matched_zones
            }
        }

    def _check_time_trigger(self, config: Dict[str, Any], timestamp: str,
                           conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Check time-based triggers."""
        if not timestamp:
            timestamp = datetime.datetime.now()
        else:
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.datetime.now()

        time_ranges = config.get('time_ranges', [])
        days_of_week = config.get('days_of_week', [])
        specific_dates = config.get('specific_dates', [])

        current_time = timestamp.time()
        current_weekday = timestamp.weekday()  # 0=Monday, 6=Sunday
        current_date = timestamp.date()

        matched_conditions = []

        # Check time ranges
        for time_range in time_ranges:
            start_time = datetime.datetime.strptime(time_range['start'], '%H:%M').time()
            end_time = datetime.datetime.strptime(time_range['end'], '%H:%M').time()

            if start_time <= current_time <= end_time:
                matched_conditions.append({
                    'type': 'time_range',
                    'range': f"{time_range['start']}-{time_range['end']}"
                })

        # Check days of week
        if current_weekday in days_of_week:
            matched_conditions.append({
                'type': 'day_of_week',
                'day': current_weekday
            })

        # Check specific dates
        for date_str in specific_dates:
            try:
                target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                if current_date == target_date:
                    matched_conditions.append({
                        'type': 'specific_date',
                        'date': date_str
                    })
            except ValueError:
                pass

        return {
            'matched': len(matched_conditions) > 0,
            'matched_conditions': matched_conditions,
            'trigger_data': {
                'current_time': current_time.isoformat(),
                'current_weekday': current_weekday,
                'current_date': current_date.isoformat()
            }
        }

    def _check_user_activity_trigger(self, config: Dict[str, Any], user_id: str,
                                    conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Check user activity-based triggers."""
        if not user_id:
            return {'matched': False, 'reason': 'No user ID provided'}

        activity_types = config.get('activity_types', [])
        user_status = config.get('user_status', [])
        group_requirements = config.get('group_requirements', [])

        matched_conditions = []

        # Get user data
        user = database.get_user(user_id)
        if not user:
            return {'matched': False, 'reason': 'User not found'}

        # Check user status
        if user['device_status'] in user_status:
            matched_conditions.append({
                'type': 'user_status',
                'status': user['device_status']
            })

        # Check user groups
        if group_requirements:
            user_groups = database.get_users_in_group(group_requirements[0]) if group_requirements else []
            if any(u['id'] == user_id for u in user_groups):
                matched_conditions.append({
                    'type': 'user_group',
                    'group_id': group_requirements[0]
                })

        # Check activity patterns (simplified)
        if 'recent_messages' in activity_types:
            recent_messages = database.get_messages_for_user(user_id, limit=10)
            if len(recent_messages) > 0:
                matched_conditions.append({
                    'type': 'recent_activity',
                    'message_count': len(recent_messages)
                })

        return {
            'matched': len(matched_conditions) > 0,
            'matched_conditions': matched_conditions,
            'trigger_data': {
                'user_status': user.get('device_status'),
                'user_groups': group_requirements
            }
        }

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in meters."""
        # Simple Euclidean distance (not accurate for large distances)
        # In production, use proper geodesic calculation
        return ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5 * 111000  # Rough conversion to meters

def test_trigger_conditions(trigger_config: Dict[str, Any], conditions: Dict[str, Any] = None,
                          message_text: str = "", user_id: str = None,
                          location_data: Dict[str, Any] = None,
                          timestamp: str = None) -> Dict[str, Any]:
    """Test trigger conditions with sample data."""
    engine = TriggerEngine()

    # Create a mock trigger for testing
    mock_trigger = {
        'id': 0,
        'trigger_type': trigger_config.get('trigger_type', 'keyword'),
        'trigger_config': trigger_config,
        'conditions': conditions or {},
        'cooldown_seconds': 0
    }

    return engine.evaluate_trigger(mock_trigger, message_text, user_id, location_data, timestamp)

def process_trigger_response(trigger_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process trigger results and determine responses."""
    if not trigger_result['result']['matched']:
        return []

    trigger = trigger_result['trigger']
    responses = database.get_responses_for_trigger(trigger['id'])

    # Filter responses based on target criteria
    applicable_responses = []

    for response in responses:
        if not response['is_active']:
            continue

        # Parse JSON fields
        if response['target_ids']:
            response['target_ids'] = json.loads(response['target_ids'])
        if response['channels']:
            response['channels'] = json.loads(response['channels'])

        # Check if response applies to this user/context
        if response['target_type'] == 'user' and trigger_result['user_id'] not in response['target_ids']:
            continue
        elif response['target_type'] == 'group':
            # Check if user is in required groups
            user_groups = []  # Would need to get user's groups
            if not any(group_id in user_groups for group_id in response['target_ids']):
                continue
        elif response['target_type'] == 'zone':
            # Check if user is in required zones
            user_zone = None  # Would need to get user's current zone
            if user_zone not in response['target_ids']:
                continue

        applicable_responses.append(response)

    return applicable_responses

def execute_trigger_response(trigger_result: Dict[str, Any], response: Dict[str, Any]) -> bool:
    """Execute a trigger response."""
    try:
        start_time = time.time()

        # Generate response content
        content = generate_response_content(response, trigger_result)

        # Determine delivery channels
        channels = response.get('channels', ['meshtastic'])

        # Log trigger execution
        trigger_log_id = database.log_trigger_execution(
            trigger_id=trigger_result['trigger']['id'],
            user_id=trigger_result['user_id'],
            message_text=trigger_result['message_text'],
            trigger_data=json.dumps(trigger_result['result']['trigger_data']),
            matched_conditions=json.dumps(trigger_result['result']['matched_conditions']),
            executed_responses=json.dumps([response['id']]),
            execution_time_ms=trigger_result['result']['execution_time_ms'],
            success=True
        )

        # Deliver to each channel
        for channel in channels:
            delivery_time = time.time()
            try:
                if channel == 'firefly':
                    # Send via Firefly
                    success = send_firefly_message(trigger_result['user_id'], content)
                elif channel == 'websocket':
                    # Send via WebSocket
                    success = send_websocket_message(trigger_result['user_id'], content)
                elif channel == 'alert':
                    # Create alert
                    success = create_trigger_alert(response, trigger_result, content)
                else:
                    success = False

                # Log delivery
                database.log_response_delivery(
                    response_id=response['id'],
                    trigger_log_id=trigger_log_id,
                    user_id=trigger_result['user_id'],
                    channel=channel,
                    content=content,
                    delivery_status='delivered' if success else 'failed',
                    delivery_time_ms=int((time.time() - delivery_time) * 1000),
                    error_message=None if success else 'Delivery failed'
                )

                if success:
                    database.increment_response_usage(response['id'])

            except Exception as e:
                database.log_response_delivery(
                    response_id=response['id'],
                    trigger_log_id=trigger_log_id,
                    user_id=trigger_result['user_id'],
                    channel=channel,
                    content=content,
                    delivery_status='failed',
                    delivery_time_ms=int((time.time() - delivery_time) * 1000),
                    error_message=str(e)
                )

        # Update trigger cooldown and count
        database.increment_trigger_count(trigger_result['trigger']['id'])

        return True

    except Exception as e:
        print(f"Error executing trigger response: {e}")
        return False

def generate_response_content(response: Dict[str, Any], trigger_result: Dict[str, Any]) -> str:
    """Generate response content with variable substitution."""
    content = response['content']
    variables = response.get('variables', {})

    # Basic variable substitution
    if '{user_name}' in content:
        user_id = trigger_result['user_id']
        user = database.get_user(user_id)
        user_name = user.get('long_name', 'User') if user else 'User'
        content = content.replace('{user_name}', user_name)

    if '{trigger_name}' in content:
        trigger_name = trigger_result['trigger']['name']
        content = content.replace('{trigger_name}', trigger_name)

    if '{timestamp}' in content:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        content = content.replace('{timestamp}', timestamp)

    # Custom variable substitution from trigger data
    trigger_data = trigger_result['result']['trigger_data']
    for var_name, var_value in variables.items():
        placeholder = f"{{{var_name}}}"
        if placeholder in content:
            # Get value from trigger data or use default
            value = trigger_data.get(var_value, var_value)
            content = content.replace(placeholder, str(value))

    return content

def send_firefly_message(user_id: str, content: str) -> bool:
    """Send message via Firefly (placeholder implementation)."""
    # In a real implementation, this would interface with the Firefly radio
    print(f"Firefly message to {user_id}: {content}")
    return True

def send_websocket_message(user_id: str, content: str) -> bool:
    """Send message via WebSocket (placeholder implementation)."""
    # In a real implementation, this would send via WebSocket connection
    print(f"WebSocket message to {user_id}: {content}")
    return True

def create_trigger_alert(response: Dict[str, Any], trigger_result: Dict[str, Any], content: str) -> bool:
    """Create an alert from trigger response."""
    try:
        # Determine alert severity based on response priority
        severity_map = {0: 'low', 1: 'medium', 2: 'high', 3: 'critical'}
        severity = severity_map.get(response['priority'], 'medium')

        alert_title = f"Trigger: {trigger_result['trigger']['name']}"
        alert_message = content

        # Create alert in database
        database.create_alert(
            user_id=trigger_result['user_id'],
            zone_id=None,  # Could be determined from trigger data
            alert_type='trigger_response',
            title=alert_title,
            message=alert_message,
            severity=severity
        )

        return True
    except Exception as e:
        print(f"Error creating trigger alert: {e}")
        return False

# Global trigger engine instance
trigger_engine = TriggerEngine()