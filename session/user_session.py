from session.user_state import UserState
from model import LLMSession
from backend import database

class UserSession:
    def __init__(self, user_id: str, user_data):
        self.current_state = UserState.NEW_CHAT
        self.user_id = user_id
        self.user_data = user_data
        self.llm_chat_session = None
        self.session_id = database.insert_session(self.user_id, self.current_state.name)
        self.menu_stack = []  # For navigation history

    def chat_with_llm(self, message, tools_enabled = False):
        if self.llm_chat_session == None:
            self.llm_chat_session = LLMSession(self.user_id, self.user_data)
        
        if tools_enabled:
            return self.llm_chat_session.chat_with_tools(message)
        
        return self.llm_chat_session.chat_without_tools(message)

    def process_command(self, command: str, message: str) -> str:

        if command == "register":
            user_data = database.get_user(self.user_id)
            if user_data and user_data.get('registration_status') == 'registered':
                return "Вы уже зарегистрированы."
            if not message.strip():
                return "Укажите никнейм: /register никнейм"
            nickname = message.strip()
            public_key = database.register_user(self.user_id, nickname)
            if public_key:
                return f"Регистрация успешна как {nickname}. Ваш публичный ключ: {public_key}"
            else:
                return "Регистрация не удалась."
        elif command == "tool":
            return self.chat_with_llm(message, tools_enabled=True)
        elif command == "enable_llm":
            self.current_state = UserState.CHAT_WITH_LLM
            database.update_session(self.session_id, state=self.current_state.name)
            return "Чат с Крастиком"
        elif command == "enable_echo":
            self.current_state = UserState.ECHO
            database.update_session(self.session_id, state=self.current_state.name)
            return "Режим эхо"
        elif command == "private":
            user_data = database.get_user(self.user_id)
            if user_data and user_data.get('registration_status') == 'registered':
                self.current_state = UserState.PRIVATE_CHAT
                database.update_session(self.session_id, state=self.current_state.name)
                return "Переключено в режим приватного чата."
            else:
                return "Вы должны быть зарегистрированы для использования приватного чата."
        elif command == "mail":
            user_data = database.get_user(self.user_id)
            if user_data and user_data.get('registration_status') == 'registered':
                pending = database.get_pending_messages_for_user(self.user_id)
                if not pending:
                    return "У вас нет новых сообщений."
                messages = []
                for msg in pending:
                    messages.append(f"От {msg['sender_id']}: {msg['text']}")
                    database.mark_pending_message_delivered(msg['id'])
                return "\n".join(messages)
            else:
                return "Вы должны быть зарегистрированы для просмотра почты."
        elif command == "disable_echo" or command == "disable_llm" or command == "go_to_normal":
            self.current_state = UserState.NORMAL_CHAT
            database.update_session(self.session_id, state=self.current_state.name)
            return "Режим простого чата."

        return f"Команда /{command} не распознана."

    def get_main_menu(self) -> str:
        return (
            "Главное меню:\n"
            "1. Инфо (info)\n"
            "2. Чат (chat)\n"
            "3. Настройки (settings)\n"
            "0. Выход (exit)\n"
            "Выберите опцию или введите команду."
        )

    def get_info_menu(self) -> str:
        return (
            "Инфо:\n"
            "1. Инфо ноды (node)\n"
            "2. Моя регистрация (reg)\n"
            "0. Назад (back)\n"
            "Выберите опцию."
        )

    def get_chat_menu(self) -> str:
        return (
            "Чат:\n"
            "1. Включить LLM (llm)\n"
            "2. Приватный чат (private)\n"
            "3. Почта (mail)\n"
            "0. Назад (back)\n"
            "Выберите опцию."
        )

    def get_settings_menu(self) -> str:
        return (
            "Настройки:\n"
            "1. Эхо режим (echo)\n"
            "0. Назад (back)\n"
            "Выберите опцию."
        )

    def handle_menu_input(self, message: str) -> str:
        msg = message.lower().strip()
        if self.current_state == UserState.MENU_MAIN:
            if msg in ['1', 'info']:
                self.menu_stack.append(UserState.MENU_MAIN)
                self.current_state = UserState.MENU_INFO
                database.update_session(self.session_id, state=self.current_state.name)
                return self.get_info_menu()
            elif msg in ['2', 'chat']:
                self.menu_stack.append(UserState.MENU_MAIN)
                self.current_state = UserState.MENU_CHAT
                database.update_session(self.session_id, state=self.current_state.name)
                return self.get_chat_menu()
            elif msg in ['3', 'settings']:
                self.menu_stack.append(UserState.MENU_MAIN)
                self.current_state = UserState.MENU_SETTINGS
                database.update_session(self.session_id, state=self.current_state.name)
                return self.get_settings_menu()
            elif msg in ['0', 'exit']:
                self.current_state = UserState.NORMAL_CHAT
                database.update_session(self.session_id, state=self.current_state.name)
                return "Выход из меню."
            else:
                return "Неверный выбор. " + self.get_main_menu()
        elif self.current_state == UserState.MENU_INFO:
            if msg in ['1', 'node']:
                return self.user_data
            elif msg in ['2', 'reg']:
                user_data = database.get_user(self.user_id)
                if user_data and user_data.get('registration_status') == 'registered':
                    return f"Зарегистрирован как {user_data.get('nickname', 'Unknown')}"
                else:
                    return "Не зарегистрирован."
            elif msg in ['0', 'back']:
                if self.menu_stack:
                    self.current_state = self.menu_stack.pop()
                    database.update_session(self.session_id, state=self.current_state.name)
                    return self.get_main_menu()
                else:
                    self.current_state = UserState.NORMAL_CHAT
                    database.update_session(self.session_id, state=self.current_state.name)
                    return "Выход из меню."
            else:
                return "Неверный выбор. " + self.get_info_menu()
        elif self.current_state == UserState.MENU_CHAT:
            if msg in ['1', 'llm']:
                self.current_state = UserState.CHAT_WITH_LLM
                database.update_session(self.session_id, state=self.current_state.name)
                return "Чат с LLM включен."
            elif msg in ['2', 'private']:
                user_data = database.get_user(self.user_id)
                if user_data and user_data.get('registration_status') == 'registered':
                    self.current_state = UserState.PRIVATE_CHAT
                    database.update_session(self.session_id, state=self.current_state.name)
                    return "Приватный чат включен."
                else:
                    return "Регистрация требуется."
            elif msg in ['3', 'mail']:
                user_data = database.get_user(self.user_id)
                if user_data and user_data.get('registration_status') == 'registered':
                    pending = database.get_pending_messages_for_user(self.user_id)
                    if not pending:
                        return "Нет новых сообщений."
                    messages = []
                    for msg in pending:
                        messages.append(f"От {msg['sender_id']}: {msg['text']}")
                        database.mark_pending_message_delivered(msg['id'])
                    return "\n".join(messages)
                else:
                    return "Регистрация требуется."
            elif msg in ['0', 'back']:
                if self.menu_stack:
                    self.current_state = self.menu_stack.pop()
                    database.update_session(self.session_id, state=self.current_state.name)
                    return self.get_main_menu()
                else:
                    self.current_state = UserState.NORMAL_CHAT
                    database.update_session(self.session_id, state=self.current_state.name)
                    return "Выход из меню."
            else:
                return "Неверный выбор. " + self.get_chat_menu()
        elif self.current_state == UserState.MENU_SETTINGS:
            if msg in ['1', 'echo']:
                self.current_state = UserState.ECHO
                database.update_session(self.session_id, state=self.current_state.name)
                return "Эхо режим включен."
            elif msg in ['0', 'back']:
                if self.menu_stack:
                    self.current_state = self.menu_stack.pop()
                    database.update_session(self.session_id, state=self.current_state.name)
                    return self.get_main_menu()
                else:
                    self.current_state = UserState.NORMAL_CHAT
                    database.update_session(self.session_id, state=self.current_state.name)
                    return "Выход из меню."
            else:
                return "Неверный выбор. " + self.get_settings_menu()
        return ""

    def chat(self, message: str) -> str:
        message = message.strip()

        if len(message) == 0:
            return ""

        if message[0] == "/":
            if " " in message:
                command, message = message.split(" ", 1)
            else:
                command, message = message, ""

            cmd = command[1:]
            if cmd == "menu":
                self.current_state = UserState.MENU_MAIN
                database.update_session(self.session_id, state=self.current_state.name)
                return self.get_main_menu()
            else:
                return self.process_command(cmd, message)

        # Handle menu states
        if self.current_state in [UserState.MENU_MAIN, UserState.MENU_INFO, UserState.MENU_CHAT, UserState.MENU_SETTINGS]:
            return self.handle_menu_input(message)

        if self.current_state == UserState.ECHO:
            return message
        elif self.current_state == UserState.NEW_CHAT:
            self.current_state = UserState.NORMAL_CHAT
            database.update_session(self.session_id, state=self.current_state.name)
            return "Добро пожаловать! Новичок? Заходи в ТГ: https://t.me/Светлячок_KRD"
        elif self.current_state == UserState.NORMAL_CHAT:
            return ""
        elif self.current_state == UserState.CHAT_WITH_LLM:
            return self.chat_with_llm(message)