import json
import datetime
import re
import random
from typing import Dict, List, Optional, Any
from backend import database
from model.llm_chat_session import ChatSession

class ResponseGenerator:
    """Advanced bot response generation system."""

    def __init__(self):
        self.llm_session = None
        self.language_templates = {
            'en': {
                'greeting': 'Hello {user_name}!',
                'location_entry': 'Welcome to {zone_name}, {user_name}!',
                'location_exit': 'Goodbye {user_name}! Safe travels!',
                'emergency': '🚨 EMERGENCY: {user_name} needs assistance at {location}',
                'help_request': 'I understand you need help, {user_name}. Let me assist you.',
                'status_check': 'Current status: All systems operational.',
                'unknown_command': 'I didn\'t understand that, {user_name}. Type "help" for available commands.'
            },
            'ru': {
                'greeting': 'Привет {user_name}!',
                'location_entry': 'Добро пожаловать в {zone_name}, {user_name}!',
                'location_exit': 'До свидания {user_name}! Хорошего пути!',
                'emergency': '🚨 ЧРЕЗВЫЧАЙНАЯ СИТУАЦИЯ: {user_name} нужна помощь в {location}',
                'help_request': 'Я понимаю, что вам нужна помощь, {user_name}. Позвольте мне помочь вам.',
                'status_check': 'Текущий статус: Все системы работают нормально.',
                'unknown_command': 'Я не понял, {user_name}. Напишите "помощь" для доступных команд.'
            }
        }

        # Advanced template variables and functions
        self.template_functions = {
            'time_of_day': self._get_time_of_day,
            'weather_info': self._get_weather_info,
            'battery_status': self._get_battery_status,
            'distance_to': self._calculate_distance_to,
            'random_greeting': self._get_random_greeting,
            'zone_safety': self._get_zone_safety_info,
            'emergency_contacts': self._get_emergency_contacts,
            'user_history': self._get_user_interaction_history,
            'predictive_help': self._get_predictive_help
        }

        # AI-powered response suggestions cache
        self.response_suggestions_cache = {}

    # Advanced Template Functions

    def _get_time_of_day(self, **kwargs) -> str:
        """Get time of day greeting."""
        hour = datetime.datetime.now().hour
        if hour < 6:
            return "night"
        elif hour < 12:
            return "morning"
        elif hour < 18:
            return "afternoon"
        else:
            return "evening"

    def _get_weather_info(self, latitude=None, longitude=None, **kwargs) -> str:
        """Get weather information (placeholder for weather API integration)."""
        # In real implementation, integrate with weather API
        return "clear skies"

    def _get_battery_status(self, user_id=None, **kwargs) -> str:
        """Get battery status description."""
        if not user_id:
            return "unknown"

        user = database.get_user(user_id)
        if not user or user.get('battery_level') is None:
            return "unknown"

        battery = user['battery_level']
        if battery > 80:
            return "excellent"
        elif battery > 60:
            return "good"
        elif battery > 30:
            return "moderate"
        elif battery > 10:
            return "low"
        else:
            return "critical"

    def _calculate_distance_to(self, target="home", user_id=None, **kwargs) -> str:
        """Calculate distance to a target location."""
        if not user_id:
            return "unknown"

        user = database.get_user(user_id)
        if not user or not user.get('latitude') or not user.get('longitude'):
            return "unknown"

        # In real implementation, calculate distance to target
        # For now, return placeholder
        return "2.5 km"

    def _get_random_greeting(self, language="en", **kwargs) -> str:
        """Get a random greeting."""
        greetings = {
            'en': ['Hi', 'Hello', 'Hey', 'Greetings', 'Good day'],
            'ru': ['Привет', 'Здравствуйте', 'Приветствую', 'Добрый день']
        }

        lang_greetings = greetings.get(language, greetings['en'])
        return random.choice(lang_greetings)

    def _get_zone_safety_info(self, zone_id=None, **kwargs) -> str:
        """Get safety information for a zone."""
        if not zone_id:
            return "general safety guidelines apply"

        zone = database.get_zone(zone_id)
        if not zone:
            return "general safety guidelines apply"

        zone_type = zone.get('zone_type', 'safe_zone')
        safety_info = {
            'safe_zone': 'This is a safe area with standard security measures.',
            'danger_zone': '⚠️ This area has potential hazards. Exercise caution.',
            'restricted': '🚫 This is a restricted area. Access may be limited.',
            'poi': '📍 Point of interest with special considerations.'
        }

        return safety_info.get(zone_type, 'general safety guidelines apply')

    def _get_emergency_contacts(self, zone_id=None, **kwargs) -> str:
        """Get emergency contact information."""
        # In real implementation, get zone-specific emergency contacts
        return "Emergency: Call 112 | Local Security: Ext 911"

    def _get_user_interaction_history(self, user_id=None, **kwargs) -> str:
        """Get summary of user interaction history."""
        if not user_id:
            return "new user"

        # Get recent interactions
        recent_messages = database.get_recent_messages_for_user(user_id, limit=5)
        interaction_count = len(recent_messages)

        if interaction_count == 0:
            return "first interaction"
        elif interaction_count < 3:
            return "occasional user"
        else:
            return "regular user"

    def _get_predictive_help(self, user_id=None, context=None, **kwargs) -> str:
        """Get predictive help based on user behavior."""
        if not user_id or not context:
            return ""

        # Analyze context for predictive suggestions
        trigger_type = context.get('trigger_type', '')

        if trigger_type == 'location' and context.get('is_moving'):
            return "Would you like directions or safety information for your route?"
        elif trigger_type == 'battery_low':
            return "Consider finding a charging station or conserving battery."
        elif trigger_type == 'emergency':
            return "Stay calm. Help is on the way."

        return ""

    def initialize_llm(self, provider: str = "openrouter", model: str = "gpt-5-nano"):
        """Initialize LLM session for dynamic response generation."""
        try:
            self.llm_session = ChatSession(provider=provider, model=model)
            return True
        except Exception as e:
            print(f"Failed to initialize LLM session: {e}")
            return False

    def generate_response(self, response_config: Dict[str, Any],
                         trigger_result: Dict[str, Any],
                         context: Dict[str, Any] = None) -> str:
        """Generate a response based on configuration and context."""
        response_type = response_config.get('response_type', 'text')
        language = response_config.get('language', 'en')

        if response_type == 'template':
            return self._generate_template_response(response_config, trigger_result, language)
        elif response_type == 'dynamic':
            return self._generate_dynamic_response(response_config, trigger_result, context, language)
        else:
            return self._generate_static_response(response_config, trigger_result, language)

    def _generate_static_response(self, response_config: Dict[str, Any],
                                 trigger_result: Dict[str, Any], language: str) -> str:
        """Generate static text response."""
        content = response_config.get('content', '')

        # Basic variable substitution
        variables = self._extract_variables(trigger_result)

        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            content = content.replace(placeholder, str(var_value))

        return content

    def _generate_template_response(self, response_config: Dict[str, Any],
                                    trigger_result: Dict[str, Any], language: str) -> str:
        """Generate response from template with advanced substitution."""
        template_name = response_config.get('template', 'default')
        content = response_config.get('content', '')

        # Get context variables
        variables = self._extract_variables(trigger_result)

        # Apply template logic
        if template_name == 'location_entry':
            zone_name = variables.get('zone_name', 'the area')
            return self.language_templates[language]['location_entry'].format(
                user_name=variables.get('user_name', 'User'),
                zone_name=zone_name
            )
        elif template_name == 'emergency':
            return self.language_templates[language]['emergency'].format(
                user_name=variables.get('user_name', 'User'),
                location=variables.get('location', 'unknown location')
            )
        else:
            # Advanced template with variable and function substitution
            content = self._process_template_variables(content, variables)
            content = self._process_template_functions(content, variables)

            return content

    def _process_template_variables(self, content: str, variables: Dict[str, Any]) -> str:
        """Process basic variable substitution in template."""
        for var_name, var_value in variables.items():
            if var_name.startswith('_'):  # Skip internal variables
                continue
            placeholder = f"{{{var_name}}}"
            content = content.replace(placeholder, str(var_value))

        return content

    def _process_template_functions(self, content: str, variables: Dict[str, Any]) -> str:
        """Process function calls in template."""
        # Pattern to match function calls like {function_name(arg1=value1, arg2=value2)}
        function_pattern = r'\{(\w+)\(([^}]*)\)\}'

        def replace_function(match):
            func_name = match.group(1)
            args_str = match.group(2)

            if func_name not in self.template_functions:
                return match.group(0)  # Return original if function not found

            # Parse arguments
            kwargs = {}
            if args_str.strip():
                # Simple argument parsing (can be enhanced)
                for arg in args_str.split(','):
                    if '=' in arg:
                        key, value = arg.split('=', 1)
                        kwargs[key.strip()] = value.strip().strip('"').strip("'")

            # Add context variables
            kwargs.update(variables.get('_context', {}))

            try:
                result = self.template_functions[func_name](**kwargs)
                return str(result)
            except Exception as e:
                print(f"Error executing template function {func_name}: {e}")
                return match.group(0)  # Return original on error

        return re.sub(function_pattern, replace_function, content)

    def generate_response_suggestions(self, trigger_result: Dict[str, Any],
                                    context: Dict[str, Any] = None,
                                    language: str = 'en', count: int = 3) -> List[str]:
        """Generate AI-powered response suggestions."""
        if not self.llm_session:
            return self._generate_fallback_suggestions(trigger_result, language, count)

        try:
            # Create cache key
            cache_key = self._create_suggestion_cache_key(trigger_result, context, language)

            # Check cache first
            if cache_key in self.response_suggestions_cache:
                cached = self.response_suggestions_cache[cache_key]
                if datetime.datetime.now() - cached['timestamp'] < datetime.timedelta(hours=1):
                    return cached['suggestions'][:count]

            # Build suggestion prompt
            prompt = self._build_suggestion_prompt(trigger_result, context, language, count)

            # Get LLM suggestions
            response = self.llm_session.chat(prompt, context=context or {})

            # Parse suggestions from response
            suggestions = self._parse_suggestion_response(response.get('content', ''), count)

            # Cache suggestions
            self.response_suggestions_cache[cache_key] = {
                'suggestions': suggestions,
                'timestamp': datetime.datetime.now()
            }

            # Clean old cache entries
            self._clean_suggestion_cache()

            return suggestions

        except Exception as e:
            print(f"Error generating AI suggestions: {e}")
            return self._generate_fallback_suggestions(trigger_result, language, count)

    def _create_suggestion_cache_key(self, trigger_result: Dict[str, Any],
                                    context: Dict[str, Any], language: str) -> str:
        """Create a cache key for response suggestions."""
        trigger_type = trigger_result.get('trigger', {}).get('trigger_type', 'unknown')
        user_id = trigger_result.get('user_id', 'unknown')
        zone_id = trigger_result.get('zone_id', 'none')

        return f"{trigger_type}_{user_id}_{zone_id}_{language}"

    def _build_suggestion_prompt(self, trigger_result: Dict[str, Any],
                               context: Dict[str, Any], language: str, count: int) -> str:
        """Build prompt for AI response suggestions."""
        trigger = trigger_result.get('trigger', {})
        trigger_type = trigger.get('trigger_type', 'unknown')

        base_prompt = f"""Generate {count} helpful response suggestions in {language} for a bot responding to a {trigger_type} trigger.

Context:
- Trigger: {trigger.get('name', 'Unknown')}
- User: {trigger_result.get('user_id', 'Unknown')}
"""

        if trigger_type == 'location':
            base_prompt += "- User has entered/exited a location zone\n"
        elif trigger_type == 'emergency':
            base_prompt += "- This is an emergency situation requiring immediate attention\n"
        elif trigger_type == 'help_request':
            base_prompt += "- User is requesting assistance\n"

        base_prompt += """
Requirements:
- Keep suggestions concise and actionable
- Consider the user's safety and context
- Use appropriate tone for the situation
- Include relevant location/time information when applicable
- Format as a numbered list

Suggestions:"""

        return base_prompt

    def _parse_suggestion_response(self, response: str, count: int) -> List[str]:
        """Parse suggestions from LLM response."""
        suggestions = []

        # Split by numbered lines
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            # Match numbered items like "1. Suggestion" or "- Suggestion"
            if re.match(r'^(\d+\.|\-)\s+', line):
                suggestion = re.sub(r'^(\d+\.|\-)\s+', '', line).strip()
                if suggestion:
                    suggestions.append(suggestion)

        # If no numbered suggestions found, try to extract sentences
        if not suggestions:
            sentences = re.split(r'[.!?]+', response)
            suggestions = [s.strip() for s in sentences if len(s.strip()) > 10][:count]

        return suggestions[:count] if suggestions else [response.strip()]

    def _generate_fallback_suggestions(self, trigger_result: Dict[str, Any],
                                     language: str, count: int) -> List[str]:
        """Generate fallback suggestions when AI is not available."""
        trigger_type = trigger_result.get('trigger', {}).get('trigger_type', 'unknown')

        fallback_suggestions = {
            'location': [
                "Welcome! Please let me know if you need any assistance.",
                "Location updated. Is everything okay?",
                "I've noted your location change. Stay safe!"
            ],
            'emergency': [
                "Emergency acknowledged. Help is on the way.",
                "Stay calm. Emergency services have been notified.",
                "Emergency situation detected. Please provide more details if safe."
            ],
            'help_request': [
                "I'm here to help. What do you need assistance with?",
                "How can I assist you right now?",
                "Let me know what help you need."
            ]
        }

        suggestions = fallback_suggestions.get(trigger_type, [
            "How can I assist you?",
            "Please provide more details.",
            "I'm here to help."
        ])

        return suggestions[:count]

    def _clean_suggestion_cache(self):
        """Clean old entries from suggestion cache."""
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=2)
        to_remove = []

        for key, data in self.response_suggestions_cache.items():
            if data['timestamp'] < cutoff:
                to_remove.append(key)

        for key in to_remove:
            del self.response_suggestions_cache[key]

    def _generate_dynamic_response(self, response_config: Dict[str, Any],
                                  trigger_result: Dict[str, Any],
                                  context: Dict[str, Any], language: str) -> str:
        """Generate dynamic response using LLM."""
        if not self.llm_session:
            # Fallback to template if LLM not available
            return self._generate_template_response(response_config, trigger_result, language)

        try:
            # Build context for LLM
            llm_context = self._build_llm_context(trigger_result, context, language)

            # Generate prompt
            prompt = self._build_llm_prompt(response_config, llm_context, language)

            # Get LLM response
            response = self.llm_session.chat(prompt, context=llm_context)

            return response.get('content', '')

        except Exception as e:
            print(f"Error generating dynamic response: {e}")
            # Fallback to template
            return self._generate_template_response(response_config, trigger_result, language)

    def _extract_variables(self, trigger_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract variables from trigger result for substitution."""
        variables = {}

        # User information
        user_id = trigger_result.get('user_id')
        if user_id:
            user = database.get_user(user_id)
            if user:
                variables['user_name'] = user.get('long_name', user.get('short_name', 'User'))
                variables['user_id'] = user_id
                variables['user_status'] = user.get('device_status', 'unknown')
                variables['battery_level'] = user.get('battery_level')

        # Trigger information
        trigger = trigger_result.get('trigger', {})
        variables['trigger_name'] = trigger.get('name', 'Unknown Trigger')
        variables['trigger_type'] = trigger.get('trigger_type', 'unknown')

        # Trigger data
        trigger_data = trigger_result.get('result', {}).get('trigger_data', {})
        variables.update(trigger_data)

        # Location data
        location_data = trigger_result.get('location_data', {})
        if location_data:
            variables['latitude'] = location_data.get('latitude')
            variables['longitude'] = location_data.get('longitude')
            variables['location'] = f"{location_data.get('latitude', 0):.4f}, {location_data.get('longitude', 0):.4f}"
            variables['altitude'] = location_data.get('altitude')
            variables['accuracy'] = location_data.get('accuracy')

        # Zone information
        zone_id = trigger_data.get('zone_id') or trigger_result.get('zone_id')
        if zone_id:
            zone = database.get_zone(zone_id)
            if zone:
                variables['zone_name'] = zone.get('name', 'Unknown Zone')
                variables['zone_type'] = zone.get('zone_type', 'unknown')
                variables['zone_description'] = zone.get('description', '')

        # Timestamp and time-based variables
        now = datetime.datetime.now()
        variables['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')
        variables['date'] = now.strftime('%Y-%m-%d')
        variables['time'] = now.strftime('%H:%M:%S')
        variables['day_of_week'] = now.strftime('%A')

        # Context variables for function calls
        variables['_context'] = {
            'user_id': user_id,
            'zone_id': zone_id,
            'trigger_type': trigger.get('trigger_type'),
            'is_moving': trigger_data.get('is_moving', False),
            'location_data': location_data
        }

        return variables

    def _build_llm_context(self, trigger_result: Dict[str, Any],
                          context: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Build context for LLM response generation."""
        base_context = {
            'language': language,
            'current_time': datetime.datetime.now().isoformat(),
            'trigger_info': trigger_result.get('trigger', {}),
            'user_info': {},
            'location_info': {},
            'system_status': 'operational'
        }

        # Add user context
        user_id = trigger_result.get('user_id')
        if user_id:
            user = database.get_user(user_id)
            if user:
                base_context['user_info'] = {
                    'id': user_id,
                    'name': user.get('long_name', user.get('short_name', 'Unknown')),
                    'status': user.get('device_status', 'unknown'),
                    'battery_level': user.get('battery_level'),
                    'last_seen': user.get('last_seen')
                }

        # Add location context
        location_data = trigger_result.get('location_data', {})
        if location_data:
            base_context['location_info'] = location_data

            # Add zone information if available
            if 'matched_zones' in trigger_result.get('result', {}).get('trigger_data', {}):
                zones = trigger_result['result']['trigger_data']['matched_zones']
                if zones:
                    base_context['current_zone'] = zones[0]

        # Add system context
        if context:
            base_context.update(context)

        return base_context

    def _build_llm_prompt(self, response_config: Dict[str, Any],
                         llm_context: Dict[str, Any], language: str) -> str:
        """Build prompt for LLM response generation."""
        prompt_template = response_config.get('prompt_template',
            'Generate a helpful response in {language} for the following situation:')

        # Determine response intent
        intent = self._determine_response_intent(response_config, llm_context)

        prompt = prompt_template.format(
            language=language,
            intent=intent,
            context=json.dumps(llm_context, ensure_ascii=False)
        )

        # Add specific instructions based on trigger type
        trigger_type = llm_context.get('trigger_info', {}).get('trigger_type')
        if trigger_type == 'emergency':
            prompt += "\n\nIMPORTANT: This is an emergency situation. Provide clear, actionable assistance and consider escalating to administrators if needed."
        elif trigger_type == 'location':
            prompt += "\n\nProvide location-aware assistance and consider the user's current zone or movement."
        elif trigger_type == 'help_request':
            prompt += "\n\nThe user is requesting help. Be helpful, clear, and provide actionable guidance."

        return prompt

    def _determine_response_intent(self, response_config: Dict[str, Any],
                                  llm_context: Dict[str, Any]) -> str:
        """Determine the intent of the response based on context."""
        trigger_type = llm_context.get('trigger_info', {}).get('trigger_type')

        intent_mapping = {
            'keyword': 'general_assistance',
            'emoji': 'visual_communication',
            'location': 'location_guidance',
            'time': 'time_based_assistance',
            'user_activity': 'activity_support',
            'emergency': 'emergency_response'
        }

        return intent_mapping.get(trigger_type, 'general_assistance')

class ResponseManager:
    """Manages bot responses and delivery."""

    def __init__(self):
        self.generator = ResponseGenerator()

    def process_responses(self, trigger_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process and execute all applicable responses for a trigger."""
        responses = database.get_responses_for_trigger(trigger_result['trigger']['id'])
        executed_responses = []

        for response in responses:
            if not response['is_active']:
                continue

            try:
                # Generate response content
                content = self.generator.generate_response(
                    response,
                    trigger_result,
                    context={'trigger_result': trigger_result}
                )

                # Execute response delivery
                success = self._deliver_response(response, trigger_result, content)

                executed_responses.append({
                    'response_id': response['id'],
                    'response_name': response['name'],
                    'content': content,
                    'success': success,
                    'channels': response.get('channels', ['firefly'])
                })

            except Exception as e:
                print(f"Error processing response {response['id']}: {e}")
                executed_responses.append({
                    'response_id': response['id'],
                    'response_name': response['name'],
                    'content': '',
                    'success': False,
                    'error': str(e)
                })

        return executed_responses

    def _deliver_response(self, response: Dict[str, Any],
                         trigger_result: Dict[str, Any], content: str) -> bool:
        """Deliver response through specified channels."""
        channels = response.get('channels', ['meshtastic'])
        user_id = trigger_result.get('user_id')

        if not user_id:
            return False

        success_count = 0

        for channel in channels:
            try:
                if channel == 'meshtastic':
                    success = self._send_meshtastic(user_id, content)
                elif channel == 'websocket':
                    success = self._send_websocket(user_id, content)
                elif channel == 'alert':
                    success = self._create_alert(response, trigger_result, content)
                elif channel == 'email':
                    success = self._send_email(user_id, content)
                elif channel == 'sms':
                    success = self._send_sms(user_id, content)
                else:
                    print(f"Unknown channel: {channel}")
                    success = False

                if success:
                    success_count += 1

            except Exception as e:
                print(f"Error delivering to channel {channel}: {e}")

        # Consider delivery successful if at least one channel worked
        return success_count > 0

    def _send_meshtastic(self, user_id: str, content: str) -> bool:
        """Send message via Firefly."""
        try:
            # In real implementation, interface with Firefly radio
            print(f"FIREFLY -> {user_id}: {content}")
            return True
        except Exception as e:
            print(f"Firefly send error: {e}")
            return False

    def _send_websocket(self, user_id: str, content: str) -> bool:
        """Send message via WebSocket."""
        try:
            # In real implementation, send via WebSocket connection
            print(f"WEBSOCKET -> {user_id}: {content}")
            return True
        except Exception as e:
            print(f"WebSocket send error: {e}")
            return False

    def _create_alert(self, response: Dict[str, Any],
                     trigger_result: Dict[str, Any], content: str) -> bool:
        """Create an alert from response."""
        try:
            # Determine severity based on response priority
            severity = 'high' if response['priority'] >= 2 else 'medium'

            database.create_alert(
                user_id=trigger_result.get('user_id'),
                zone_id=None,
                alert_type='bot_response',
                title=f"Bot Response: {response['name']}",
                message=content,
                severity=severity
            )
            return True
        except Exception as e:
            print(f"Alert creation error: {e}")
            return False

    def _send_email(self, user_id: str, content: str) -> bool:
        """Send email (placeholder)."""
        print(f"EMAIL -> {user_id}: {content}")
        return True

    def _send_sms(self, user_id: str, content: str) -> bool:
        """Send SMS (placeholder)."""
        print(f"SMS -> {user_id}: {content}")
        return True

# Global response manager instance
response_manager = ResponseManager()