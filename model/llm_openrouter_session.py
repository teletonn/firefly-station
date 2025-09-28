import requests
import os
import yaml
from .tool_registry import tool_handlers

# Load config.yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Get web_search_enabled setting for Openrouter
OPENROUTER_WEB_SEARCH_ENABLED = config.get('model', {}).get('openrouter', {}).get('web_search_enabled', False)

# OpenRouter API Key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "YOUR_API_KEY") # Consider using environment variables for production

class LLMOpenRouterSession():
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

    # Get active LLM provider
    LLM_PROVIDER = config.get('llm_provider', 'ollama')

    # Static Model Name
    model_name = "mistralai/mistral-7b-instruct:free" # Configurable for OpenRouter

    # Static Model Tools
    model_tools = []

    def __init__(self, user_id, user_data):
        self.message_history = []

        user_information = f"Вы общаетесь с пользователем с ID: {user_id}."
        node_information = f"Информация о ноде пользователя: <node_data> {str(user_data)} </node_data>."

        self.message_history.append({"role": "system", "content": LLMOpenRouterSession.system_prompt})
        self.message_history.append({"role": "system", "content": user_information})
        self.message_history.append({"role": "system", "content": node_information})

    def _should_enable_web_search(self, message: str) -> bool:
        """
        Determines if web search should be enabled based on keywords in the message
        and the global OPENROUTER_WEB_SEARCH_ENABLED setting.
        """
        if not OPENROUTER_WEB_SEARCH_ENABLED or LLMOpenRouterSession.LLM_PROVIDER != 'openrouter':
            return False

        keywords = ["погода", "новости", "актуальные", "обновления", "что сейчас", "инструкция", "когда", "кто такая", "кто такой", "найди", "объясни"]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in keywords)

    def chat_with_tools(self, message):
        # Log the user message to chat history
        self.message_history.append({"role": "user", "content": message})

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": LLMOpenRouterSession.model_name,
            "messages": self.message_history,
            "tools": LLMOpenRouterSession.model_tools
        }
        if self._should_enable_web_search(message):
            data["web_search"] = True

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            proxies={}
        )
        response.raise_for_status() # Raise an exception for HTTP errors
        response_json = response.json()
        
        # Assuming OpenRouter's response structure is similar to OpenAI's chat completions
        # and the message object is directly under choices[0].message
        openrouter_message = response_json['choices'][0]['message']
        self.message_history.append(openrouter_message)

        # If no tool call is used, return early
        if not openrouter_message.get('tool_calls'):
            return openrouter_message.get('content')
        
        # If tool call is used
        for tool in openrouter_message['tool_calls']:
            # Ensure the function is available, and then call it
            if function_to_call := tool_handlers.get(tool['function']['name']):
                print('Вызов функции:', tool['function']['name'])
                print('Аргументы:', tool['function']['arguments'])

                output = function_to_call(**tool['function']['arguments'])
            else:
                output = f"Инстурмент {tool['function']['name']} не найден"
                
            print('Ответ:', output)
            self.message_history.append({'role': 'tool', 'content': str(output), 'name': tool['function']['name']})

        # Second call to OpenRouter after tool execution
        data["messages"] = self.message_history # Update messages with tool output
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            proxies={}
        )
        response.raise_for_status()
        response_json = response.json()
        final_response_message = response_json['choices'][0]['message']
        print('Финальный ответ:', final_response_message.get('content'))

        return final_response_message.get('content')


    def chat_without_tools(self, message):
        # Log the user message to chat history
        self.message_history.append({"role": "user", "content": message})

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": LLMOpenRouterSession.model_name,
            "messages": self.message_history
        }
        if self._should_enable_web_search(message):
            data["web_search"] = True

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            proxies={}
        )
        response.raise_for_status()
        response_json = response.json()

        openrouter_message = response_json['choices'][0]['message']
        self.message_history.append(openrouter_message)

        return openrouter_message.get('content')