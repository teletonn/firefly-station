import requests
import json
import yaml
import os
from .tool_registry import tool_handlers

# Load config.yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Get Agent0 API URL
AGENT0_API_URL = 'http://localhost:50001/api_message'

# Get Agent0 MCP server URL from config for API key extraction
AGENT0_CONFIG_URL = config.get('mcpServers', {}).get('agent-zero-http', {}).get('url', 'http://localhost:8080')

class LLMAgent0Session:
    # Static System Prompt For A LLM Chat Session
    system_prompt = """
    Ты работаешь как LLM узел в сети Светлячок. Твое имя Крастик. Ты находишься в Краснодаре и помогаешь новым пользователям подключаться к нашей сети. Учитывай ограничения сети:

    - Сообщения должны быть короткими и понятными из-за низкой пропускной способности сети.
    - Избегай лишних данных и длинных формулировок.

    При составлении сообщений:
    - Используй только русский язык.
    - Пиши короткими предложениями.
    - Используй аббревиатуры и сокращения, если они остаются понятными.
    - Передавай только самую важную информацию.
    
    Для подключения к нашей сети нужно (отвечать при запросе пользователя):
    - Установить приложение.
    - Зайти в настройки LoRa.
    - Режим модема (Modem Preset): LONG_FAST
    - Установить регион Russia (Россия).
    - Слот частоты: 2
    - Частота: 869.075
    - Зайти в настройки каналов и добавить канал KRASNODAR с ключем KQ==
    На этом настройка завершена, заходите в чат канала и общайтесь.
    Так же можно зайти в наш телеграм канал и группу @ffmesh

    Используй прямой и ясный стиль для быстрой передачи сообщения.
    """

    # Static Model Name
    model_name = config.get('model', {}).get('agent0', {}).get('name', 'agent0-model')

    # Static Model Tools (empty since Agent0 provides final answers without reasoning)
    model_tools = []

    def __init__(self, user_id, user_data):
        self.message_history = []
        self.context_id = None
        self.first_response = True

        user_information = f"Вы общаетесь с пользователем с ID: {user_id}."
        node_information = f"Информация о ноде пользователя: <node_data> {str(user_data)} </node_data>."

        self.message_history.append({"role": "system", "content": LLMAgent0Session.system_prompt})
        self.message_history.append({"role": "system", "content": user_information})
        self.message_history.append({"role": "system", "content": node_information})
        self.initial_history = self.message_history.copy()

    def _extract_api_key(self):
        """Extract API key from the MCP server URL path after 't-'."""
        if 't-' in AGENT0_CONFIG_URL:
            return AGENT0_CONFIG_URL.split('t-')[1].split('/')[0]
        return ''

    def _send_request(self, message, use_tools=False):
        """Send HTTP POST request to Agent0 API and receive response."""
        try:
            api_key = self._extract_api_key()
            headers = {
                "Content-Type": "application/json",
                "X-API-KEY": api_key
            }
            # Build conversation history as string
            conversation = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.message_history])
            data = {
                "message": conversation,
                "lifetime_hours": 24
            }

            response = requests.post(AGENT0_API_URL, headers=headers, json=data)
            response.raise_for_status()

            resp_json = response.json()
            response_content = resp_json.get('response', '')
            self.context_id = resp_json.get('context_id')

            return response_content
        except requests.RequestException as e:
            return f"Error communicating with Agent0 API: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def chat_with_tools(self, message):
        # Check for reset command
        if message.strip().lower() == "новый":
            self.message_history = self.initial_history.copy()
            self.first_response = True

        # Log the user message to chat history
        self.message_history.append({"role": "user", "content": message})

        # Send request to Agent0 MCP server
        response_content = self._send_request(message, use_tools=True)

        # Include instructions if first response
        if self.first_response:
            response_content += "\n\nЧтобы сбросить контекст, скажите 'Новый'."
            self.first_response = False

        # Since Agent0 provides final answers without reasoning, no tool handling needed
        # Append the response to history
        self.message_history.append({"role": "assistant", "content": response_content})

        return response_content

    def chat_without_tools(self, message):
        # Check for reset command
        if message.strip().lower() == "новый":
            self.message_history = self.initial_history.copy()
            self.first_response = True

        # Log the user message to chat history
        self.message_history.append({"role": "user", "content": message})

        # Send request to Agent0 MCP server
        response_content = self._send_request(message, use_tools=False)

        # Include instructions if first response
        if self.first_response:
            response_content += "\n\nЧтобы сбросить контекст, скажите 'Новый'."
            self.first_response = False

        # Append the response to history
        self.message_history.append({"role": "assistant", "content": response_content})

        return response_content