from enum import Enum

class UserState(Enum):
    NEW_CHAT = 0
    NORMAL_CHAT = 1
    CHAT_WITH_LLM = 2
    ECHO = 3
    PRIVATE_CHAT = 4
    MENU_MAIN = 5
    MENU_INFO = 6
    MENU_CHAT = 7
    MENU_SETTINGS = 8