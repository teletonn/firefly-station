import json
import datetime
from typing import Dict, List, Optional, Any
from .llm_chat_session import ChatSession
from backend import database

class BotLLMSession:
    """Enhanced LLM session for bot operations with context awareness and multi-language support."""

    def __init__(self, provider: str = "openrouter", model: str = "gpt-5-nano"):
        self.provider = provider
        self.model = model
        self.chat_session = None
        self.context_cache = {}

        # Multi-language system prompts
        self.system_prompts = {
            'en': """
            You are an intelligent bot assistant for a Светлячок mesh network community.
            Your name is Firefly Bot and you help users with communication, navigation, and emergency coordination.

            Communication Guidelines:
            - Keep messages concise (<200 characters for Meshtastic compatibility)
            - Be helpful, clear, and actionable
            - Use appropriate language based on user preference and context
            - Provide location-aware assistance when possible

            Context Awareness:
            - Consider user's current location and zone
            - Be aware of user groups and community structure
            - Monitor for emergency situations and respond appropriately
            - Adapt responses based on user activity and status

            Emergency Response:
            - Prioritize emergency communications
            - Provide clear instructions for emergency situations
            - Coordinate with administrators when needed
            - Escalate critical situations automatically

            Multi-language Support:
            - Respond in the user's preferred language when known
            - Default to English for international users
            - Provide clear translations when switching languages
            """,
            'ru': """
            Вы - интеллектуальный бот-помощник для сообщества сети Светлячок.
            Ваше имя - Firefly Bot и вы помогаете пользователям с коммуникацией, навигацией и координацией в чрезвычайных ситуациях.

            Рекомендации по коммуникации:
            - Держите сообщения краткими (<200 символов для совместимости с Meshtastic)
            - Будьте полезны, ясны и действенны
            - Используйте соответствующий язык в зависимости от предпочтений пользователя и контекста
            - Предоставляйте помощь с учетом местоположения когда возможно

            Осведомленность о контексте:
            - Учитывайте текущее местоположение и зону пользователя
            - Знайте о группах пользователей и структуре сообщества
            - Мониторьте чрезвычайные ситуации и реагируйте соответствующим образом
            - Адаптируйте ответы в зависимости от активности и статуса пользователя

            Реагирование на чрезвычайные ситуации:
            - Отдавайте приоритет чрезвычайным коммуникациям
            - Предоставляйте четкие инструкции для чрезвычайных ситуаций
            - Координируйте с администраторами при необходимости
            - Автоматически эскалируйте критические ситуации

            Многоязычная поддержка:
            - Отвечайте на предпочтительном языке пользователя когда известно
            - По умолчанию используйте русский для локальных пользователей
            - Предоставляйте четкие переводы при смене языков
            """
        }

    def initialize_session(self, user_id: str = None) -> bool:
        """Initialize the chat session with appropriate context."""
        try:
            # Get user context if available
            user_context = self._get_user_context(user_id) if user_id else {}

            # Determine language preference
            language = user_context.get('language', 'en')

            # Create system prompt
            system_prompt = self.system_prompts.get(language, self.system_prompts['en'])

            # Add user-specific context
            if user_context:
                user_info = f"User ID: {user_id}, Name: {user_context.get('name', 'Unknown')}, Status: {user_context.get('status', 'unknown')}"
                location_info = ""

                if user_context.get('location'):
                    loc = user_context['location']
                    location_info = f"Current location: {loc.get('lat', 0):.4f}, {loc.get('lon', 0):.4f}"

                    if user_context.get('zone'):
                        location_info += f", Zone: {user_context['zone']['name']}"

                system_prompt += f"\n\nCurrent User Context:\n{user_info}\n{location_info}"

            # Initialize chat session
            self.chat_session = ChatSession(provider=self.provider, model=self.model)
            self.chat_session.system_prompt = system_prompt

            return True

        except Exception as e:
            print(f"Failed to initialize bot LLM session: {e}")
            return False

    def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user context for enhanced responses."""
        context = {}

        try:
            # Get user data
            user = database.get_user(user_id)
            if user:
                context['name'] = user.get('long_name', user.get('short_name', 'Unknown'))
                context['status'] = user.get('device_status', 'unknown')
                context['battery_level'] = user.get('battery_level')
                context['last_seen'] = user.get('last_seen')

                # Get user location
                if user.get('latitude') and user.get('longitude'):
                    context['location'] = {
                        'lat': user['latitude'],
                        'lon': user['longitude'],
                        'altitude': user.get('altitude')
                    }

                    # Get current zone
                    if user.get('current_zone_id'):
                        zone = database.get_zone(user['current_zone_id'])
                        if zone:
                            context['zone'] = {
                                'id': zone['id'],
                                'name': zone['name'],
                                'type': zone['zone_type']
                            }

                # Get user groups
                user_groups = []
                group_memberships = database.get_all_user_groups(limit=100)
                for group in group_memberships:
                    members = database.get_users_in_group(group['id'])
                    if any(u['id'] == user_id for u in members):
                        user_groups.append({
                            'id': group['id'],
                            'name': group['name']
                        })

                if user_groups:
                    context['groups'] = user_groups

                # Get recent user activity
                recent_messages = database.get_messages_for_user(user_id, limit=5)
                if recent_messages:
                    context['recent_activity'] = recent_messages

        except Exception as e:
            print(f"Error getting user context: {e}")

        return context

    def generate_contextual_response(self, message: str, user_id: str = None,
                                   trigger_context: Dict[str, Any] = None,
                                   language: str = 'en') -> Dict[str, Any]:
        """Generate a contextual response using LLM with full context awareness."""
        if not self.chat_session:
            if not self.initialize_session(user_id):
                return {
                    'content': 'Sorry, I am currently unable to process your request.',
                    'language': language,
                    'confidence': 0.0
                }

        try:
            # Build enhanced context
            context = {
                'user_message': message,
                'timestamp': datetime.datetime.now().isoformat(),
                'language': language,
                'user_context': self._get_user_context(user_id) if user_id else {},
                'trigger_context': trigger_context or {},
                'system_status': 'operational'
            }

            # Add location context if available
            if user_id:
                user_context = context['user_context']
                if user_context.get('location'):
                    # Get nearby users
                    nearby_users = self._get_nearby_users(user_context['location'])
                    if nearby_users:
                        context['nearby_users'] = nearby_users

                    # Get zone-specific information
                    if user_context.get('zone'):
                        zone_info = self._get_zone_information(user_context['zone']['id'])
                        if zone_info:
                            context['zone_info'] = zone_info

            # Generate response using LLM
            prompt = self._build_enhanced_prompt(message, context, language)

            # Get response from LLM
            llm_response = self.chat_session.chat(prompt, context=context)

            return {
                'content': llm_response.get('content', ''),
                'language': language,
                'confidence': 0.9,  # Could be enhanced with actual confidence scoring
                'context_used': context,
                'response_metadata': {
                    'model': self.model,
                    'provider': self.provider,
                    'timestamp': datetime.datetime.now().isoformat()
                }
            }

        except Exception as e:
            print(f"Error generating contextual response: {e}")
            return {
                'content': self._get_fallback_response(message, language),
                'language': language,
                'confidence': 0.0,
                'error': str(e)
            }

    def _build_enhanced_prompt(self, message: str, context: Dict[str, Any], language: str) -> str:
        """Build an enhanced prompt with full context for LLM."""
        base_prompt = f"""
        Generate a helpful response in {language} to the following user message.

        User Message: {message}

        Context Information:
        - Current Time: {context.get('timestamp', 'Unknown')}
        - User Status: {context.get('user_context', {}).get('status', 'Unknown')}
        - User Location: {context.get('user_context', {}).get('location', 'Unknown')}
        - Current Zone: {context.get('user_context', {}).get('zone', {}).get('name', 'None')}
        - Language: {language}

        Response Guidelines:
        1. Keep response concise (<200 characters for Firefly compatibility)
        2. Be helpful and actionable
        3. Consider user's location and context
        4. Use appropriate language and tone
        5. If this is an emergency, prioritize urgency and clarity

        Generate a natural, contextual response:
        """

        # Add trigger-specific context if available
        trigger_context = context.get('trigger_context', {})
        if trigger_context:
            base_prompt += f"\n\nTrigger Context: {json.dumps(trigger_context, ensure_ascii=False)}"

        # Add emergency context if detected
        if self._is_emergency_message(message):
            base_prompt += """
            \n\nEMERGENCY DETECTED: This appears to be an emergency situation.
            Provide immediate, clear assistance and consider escalating to administrators.
            """

        return base_prompt

    def _get_nearby_users(self, location: Dict[str, float], radius_meters: int = 1000) -> List[Dict[str, Any]]:
        """Get users within specified radius of location."""
        try:
            # This is a simplified implementation
            # In production, you'd use proper geospatial queries
            all_users = database.get_all_users(limit=100)

            nearby = []
            user_lat, user_lon = location['lat'], location['lon']

            for user in all_users:
                if user.get('latitude') and user.get('longitude'):
                    # Simple distance calculation
                    distance = self._calculate_distance(
                        user_lat, user_lon,
                        user['latitude'], user['longitude']
                    )

                    if distance <= radius_meters:
                        nearby.append({
                            'id': user['id'],
                            'name': user.get('long_name', user.get('short_name', 'Unknown')),
                            'distance': distance,
                            'status': user.get('device_status', 'unknown')
                        })

            return nearby

        except Exception as e:
            print(f"Error getting nearby users: {e}")
            return []

    def _get_zone_information(self, zone_id: int) -> Dict[str, Any]:
        """Get detailed information about a zone."""
        try:
            zone = database.get_zone(zone_id)
            if not zone:
                return {}

            # Get users currently in zone
            users_in_zone = database.get_users_by_zone(zone_id)

            return {
                'id': zone['id'],
                'name': zone['name'],
                'description': zone['description'],
                'type': zone['zone_type'],
                'user_count': len(users_in_zone),
                'users': [
                    {
                        'id': user['id'],
                        'name': user.get('long_name', user.get('short_name', 'Unknown')),
                        'status': user.get('device_status', 'unknown')
                    }
                    for user in users_in_zone
                ]
            }

        except Exception as e:
            print(f"Error getting zone information: {e}")
            return {}

    def _is_emergency_message(self, message: str) -> bool:
        """Detect if a message indicates an emergency situation."""
        emergency_keywords = {
            'en': ['emergency', 'help', 'urgent', 'danger', 'injured', 'stuck', 'lost', '911', 'sos'],
            'ru': ['экстренно', 'помогите', 'срочно', 'опасность', 'ранен', 'застрял', 'потерялся', '911', 'sos']
        }

        message_lower = message.lower()

        # Check for emergency keywords
        for lang_keywords in emergency_keywords.values():
            if any(keyword in message_lower for keyword in lang_keywords):
                return True

        # Check for emergency emojis
        emergency_emojis = ['🚨', '⚠️', '🆘', '❗', '‼️']
        if any(emoji in message for emoji in emergency_emojis):
            return True

        return False

    def _get_fallback_response(self, message: str, language: str) -> str:
        """Get fallback response when LLM is unavailable."""
        fallback_responses = {
            'en': {
                'greeting': 'Hello! How can I help you today?',
                'emergency': 'I understand this may be an emergency. Please contact administrators directly.',
                'location': 'I can help with location and navigation assistance.',
                'general': 'I\'m here to help with communication and coordination.'
            },
            'ru': {
                'greeting': 'Привет! Чем могу помочь?',
                'emergency': 'Я понимаю, что это может быть чрезвычайная ситуация. Пожалуйста, свяжитесь с администраторами напрямую.',
                'location': 'Я могу помочь с навигацией и определением местоположения.',
                'general': 'Я здесь, чтобы помочь с коммуникацией и координацией.'
            }
        }

        responses = fallback_responses.get(language, fallback_responses['en'])

        if self._is_emergency_message(message):
            return responses['emergency']
        else:
            return responses['general']

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in meters."""
        # Simplified distance calculation
        return ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5 * 111000

    def translate_message(self, message: str, from_lang: str, to_lang: str) -> str:
        """Translate message between languages (placeholder implementation)."""
        # In a real implementation, this would use a translation service
        # For now, return the original message with a note
        if from_lang == to_lang:
            return message
        else:
            return f"[{to_lang.upper()}] {message} [Translation service unavailable]"

    def detect_language(self, message: str) -> str:
        """Detect the language of a message (simplified implementation)."""
        # In a real implementation, this would use proper language detection
        # For now, use simple heuristics

        russian_chars = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')
        message_chars = set(message.lower())

        # If message contains many Russian characters, assume Russian
        russian_char_count = len(message_chars.intersection(russian_chars))

        if russian_char_count > len(message) * 0.3:  # 30% threshold
            return 'ru'
        else:
            return 'en'

class EmergencyResponseHandler:
    """Handles emergency detection and response coordination."""

    def __init__(self, llm_session: BotLLMSession):
        self.llm_session = llm_session
        self.emergency_keywords = {
            'en': ['emergency', 'help', 'urgent', 'danger', 'injured', 'stuck', 'lost', 'attack', 'fire', 'medical'],
            'ru': ['экстренно', 'помогите', 'срочно', 'опасность', 'ранен', 'застрял', 'потерялся', 'нападение', 'пожар', 'медицина']
        }

    def analyze_emergency_situation(self, message: str, user_id: str,
                                  location_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze message for emergency indicators and determine response strategy."""
        analysis = {
            'is_emergency': False,
            'severity': 'low',  # 'low', 'medium', 'high', 'critical'
            'category': 'general',  # 'medical', 'security', 'navigation', 'technical'
            'urgency': 0.0,  # 0.0 to 1.0
            'required_actions': [],
            'notification_targets': []
        }

        message_lower = message.lower()
        detected_language = self.llm_session.detect_language(message)

        # Check for emergency keywords
        keywords = self.emergency_keywords.get(detected_language, self.emergency_keywords['en'])
        found_keywords = [kw for kw in keywords if kw in message_lower]

        if found_keywords:
            analysis['is_emergency'] = True
            analysis['urgency'] = min(0.9, len(found_keywords) * 0.2)

            # Determine severity and category
            if any(kw in ['attack', 'нападение', 'danger', 'опасность'] for kw in found_keywords):
                analysis['severity'] = 'critical'
                analysis['category'] = 'security'
                analysis['urgency'] = 1.0
            elif any(kw in ['medical', 'injured', 'медицина', 'ранен'] for kw in found_keywords):
                analysis['severity'] = 'high'
                analysis['category'] = 'medical'
                analysis['urgency'] = 0.9
            elif any(kw in ['fire', 'пожар'] for kw in found_keywords):
                analysis['severity'] = 'high'
                analysis['category'] = 'fire'
                analysis['urgency'] = 0.9
            elif any(kw in ['lost', 'stuck', 'потерялся', 'застрял'] for kw in found_keywords):
                analysis['severity'] = 'medium'
                analysis['category'] = 'navigation'
                analysis['urgency'] = 0.7

            # Determine required actions
            if analysis['severity'] in ['high', 'critical']:
                analysis['required_actions'] = [
                    'notify_administrators',
                    'alert_nearby_users',
                    'prepare_emergency_response'
                ]
                analysis['notification_targets'] = ['administrators', 'nearby_users', 'emergency_services']
            else:
                analysis['required_actions'] = [
                    'provide_immediate_assistance',
                    'monitor_situation'
                ]
                analysis['notification_targets'] = ['user', 'nearby_users']

        return analysis

    def generate_emergency_response(self, message: str, user_id: str,
                                  emergency_analysis: Dict[str, Any],
                                  location_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate appropriate emergency response."""
        try:
            # Get user context for personalized response
            user_context = self.llm_session._get_user_context(user_id)

            # Generate contextual emergency response
            response_content = self.llm_session.generate_contextual_response(
                message=f"EMERGENCY: {message}",
                user_id=user_id,
                trigger_context={
                    'emergency_analysis': emergency_analysis,
                    'location_data': location_data
                },
                language=user_context.get('language', 'en')
            )

            # Create emergency alert
            alert_title = f"Emergency: {emergency_analysis['category'].title()}"
            alert_message = f"User {user_context.get('name', 'Unknown')} reported: {message}"

            if location_data:
                alert_message += f"\nLocation: {location_data.get('lat', 0):.4f}, {location_data.get('lon', 0):.4f}"

            # Create alert in database
            database.create_alert(
                user_id=user_id,
                zone_id=user_context.get('zone', {}).get('id'),
                alert_type='emergency',
                title=alert_title,
                message=alert_message,
                severity=emergency_analysis['severity'],
                location_latitude=location_data.get('lat') if location_data else None,
                location_longitude=location_data.get('lon') if location_data else None
            )

            return {
                'response': response_content,
                'alert_created': True,
                'escalation_required': emergency_analysis['severity'] in ['high', 'critical'],
                'notification_targets': emergency_analysis['notification_targets']
            }

        except Exception as e:
            print(f"Error generating emergency response: {e}")
            return {
                'response': {
                    'content': 'Emergency assistance is on the way. Please stay safe and try to provide your location if possible.',
                    'language': 'en',
                    'confidence': 1.0
                },
                'alert_created': False,
                'escalation_required': True,
                'notification_targets': ['administrators']
            }

# Global bot LLM session instance
bot_llm_session = BotLLMSession()