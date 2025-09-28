from model.llm_chat_session import LLMChatSession
from model.llm_openrouter_session import LLMOpenRouterSession
from model.llm_agent0_session import LLMAgent0Session
import yaml

# Load configuration
with open('./config.yaml', 'r') as file:
        config = yaml.safe_load(file)

llm_provider_name = config.get("llm_provider")

if llm_provider_name == "openrouter":
    LLMSession = LLMOpenRouterSession
elif llm_provider_name == "agent0":
    LLMSession = LLMAgent0Session
else:
    LLMSession = LLMChatSession

LLMSession.model_name = config["model"][llm_provider_name]["name"]

if config["model"][llm_provider_name].get("tool_use", False) and config.get("tools"):
    LLMSession.model_tools = [{"type": "function", "function": tool } for tool in config['tools']]