import re
from ollama import chat
from ollama import ChatResponse
from .tool_registry import tool_handlers

class LLMChatSession():
    # Static System Prompt For A LLM Chat Session
    system_prompt = """
    Ты работаешь как LLM узел в сети Светлячок. Твое имя Крастик. Ты находишься в Краснодаре и помогаешь новым пользователям подключаться к нашей сети. Учитывай ограничения сети:

    - Длина сообщения ограничена. (<200 символов, иначе сообщение будет отброшено)
    - Сообщения должны быть короткими и понятными из-за низкой пропускной способности сети.
    - Избегай лишних данных и длинных формулировок.

    При составлении сообщений:
    - Используй только русский язык.
    - Пиши короткими предложениями.
    - Используй аббревиатуры и сокращения, если они остаются понятными.
    - Передавай только самую важную информацию.

    Используй прямой и ясный стиль для быстрой передачи сообщения.
    """

    # Static Model Name
    model_name = "gemma3:latest"

    # Static Model Tools
    model_tools = []

    def __init__(self, user_id, user_data):
        self.message_history = []

        user_information = f"Вы общаетесь с пользователем с ID: {user_id}."
        node_information = f"Информация о ноде пользователя: <node_data> {str(user_data)} </node_data>."

        self.message_history.append({"role": "system", "content": LLMChatSession.system_prompt})
        self.message_history.append({"role": "system", "content": user_information})
        self.message_history.append({"role": "system", "content": node_information})

    def _parse_response_content(self, content: str) -> str:
        """
        Parses the LLM response content to remove <think> tags and their content,
        extracting only the final answer.

        Handles edge cases: missing tags (no change), malformed/unclosed tags (removes from <think> to end),
        multiple think blocks (removes all).

        :param content: Raw response content string
        :return: Cleaned content with think blocks removed
        """
        if not content:
            return content
        try:
            # Regex to remove <think> blocks, including unclosed ones
            cleaned = re.sub(r'<think>.*?(</think>|$)', '', content, flags=re.DOTALL | re.IGNORECASE)
            return cleaned.strip()
        except Exception as e:
            # In case of regex error, return original content
            print(f"Error parsing response content: {e}")
            return content

    def chat_with_tools(self, message):
        # Log the user message to chat history
        self.message_history.append({"role": "user", "content": message})

        # Pass only the user's message history to the chat function.
        response: ChatResponse = chat(model=LLMChatSession.model_name, messages=self.message_history, tools=LLMChatSession.model_tools)

        self.message_history.append(response.message)

        # If no tool call is used, return early
        if not response.message.tool_calls:
            return self._parse_response_content(response.message.content)
        
        # If tool call is used
        for tool in response.message.tool_calls:
            # Ensure the function is available, and then call it
            if function_to_call := tool_handlers.get(tool.function.name):
                print('Вызов функции:', tool.function.name)
                print('Аргументы:', tool.function.arguments)

                output = function_to_call(**tool.function.arguments)
            else:
                output = f"Инстурмент {tool.function.name} не найден"
                
            print('Ответ:', output)
            self.message_history.append({'role': 'tool', 'content': str(output), 'name': tool.function.name})

        # Pass only the user's message history to the chat function.
        response: ChatResponse = chat(model=LLMChatSession.model_name, messages=self.message_history, tools=LLMChatSession.model_tools)
        print('Финальный ответ:', response.message.content)

        return self._parse_response_content(response.message.content)


    def chat_without_tools(self, message):

        # Log the user message to chat history
        self.message_history.append({"role": "user", "content": message})

        # Pass only the user's message history to the chat function.
        response: ChatResponse = chat(model=LLMChatSession.model_name, messages=self.message_history)

        self.message_history.append(response.message)

        return self._parse_response_content(response.message.content)