#!/usr/bin/env python3
"""Test script for LLMAgent0Session functionality."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from model.llm_agent0_session import LLMAgent0Session
from unittest.mock import patch, MagicMock

def test_api_key_extraction():
    """Test API key extraction from URL."""
    # Create a dummy session to test the method
    session = LLMAgent0Session("test_user", {"node": "test"})

    # Test the _extract_api_key method
    api_key = session._extract_api_key()
    print(f"Extracted API key: '{api_key}'")

    # Expected from config: XcRviocDg-egRUxt
    expected = "XcRviocDg-egRUxt"
    if api_key == expected:
        print("API key extraction: PASSED")
        return True
    else:
        print(f"API key extraction: FAILED - Expected '{expected}', got '{api_key}'")
        return False

def test_request_structure():
    """Test the HTTP request structure by inspecting the _send_request method."""
    session = LLMAgent0Session("test_user", {"node": "test"})

    # We can't actually send the request without the server running,
    # but we can verify the structure is correct by checking the method exists
    # and the headers/data are properly formed

    # Check if _send_request method exists
    if hasattr(session, '_send_request'):
        print("_send_request method: EXISTS")
    else:
        print("_send_request method: MISSING")
        return False

    # Check API URL
    from model.llm_agent0_session import AGENT0_API_URL
    print(f"API URL: {AGENT0_API_URL}")
    if AGENT0_API_URL == 'http://localhost:50001/api_message':
        print("API URL: CORRECT")
    else:
        print("API URL: INCORRECT")
        return False

    # Check config URL
    from model.llm_agent0_session import AGENT0_CONFIG_URL
    print(f"Config URL: {AGENT0_CONFIG_URL}")
    expected_config_url = "http://localhost:50001/mcp/t-XcRviocDg-egRUxt/http"
    if AGENT0_CONFIG_URL == expected_config_url:
        print("Config URL: CORRECT")
    else:
        print("Config URL: INCORRECT")
        return False

    print("Request structure: PASSED")
    return True

@patch('model.llm_agent0_session.requests.post')
def test_message_history_maintenance(mock_post):
    """Test that message history is maintained across multiple calls."""
    # Mock the API response
    mock_response = MagicMock()
    mock_response.json.return_value = {'response': 'Test response', 'context_id': '123'}
    mock_post.return_value = mock_response

    session = LLMAgent0Session("test_user", {"node": "test"})

    # First message
    response1 = session.chat_without_tools("Hello")
    assert "Test response" in response1
    assert "Чтобы сбросить контекст" in response1  # First response includes instructions

    # Check history has user and assistant messages
    assert len(session.message_history) == 5  # system, system, system, user, assistant
    assert session.message_history[-2]['role'] == 'user'
    assert session.message_history[-2]['content'] == "Hello"
    assert session.message_history[-1]['role'] == 'assistant'

    # Second message
    response2 = session.chat_without_tools("How are you?")
    assert "Test response" in response2
    assert "Чтобы сбросить контекст" not in response2  # Not first response

    # Check history now has more messages
    assert len(session.message_history) == 7  # previous + user + assistant
    assert session.message_history[-2]['content'] == "How are you?"

    print("Message history maintenance: PASSED")
    return True

@patch('model.llm_agent0_session.requests.post')
def test_context_reset(mock_post):
    """Test that context resets when 'Новый' is sent."""
    mock_response = MagicMock()
    mock_response.json.return_value = {'response': 'Reset response', 'context_id': '456'}
    mock_post.return_value = mock_response

    session = LLMAgent0Session("test_user", {"node": "test"})

    # Add some history
    session.chat_without_tools("First message")
    assert len(session.message_history) > 3

    # Send reset command
    response = session.chat_without_tools("Новый")
    assert "Reset response" in response

    # Check history is reset to initial
    assert len(session.message_history) == len(session.initial_history) + 2  # initial + user + assistant
    assert session.first_response == False  # Should be False after reset

    print("Context reset: PASSED")
    return True

@patch('model.llm_agent0_session.requests.post')
def test_reset_instructions_in_first_response(mock_post):
    """Test that reset instructions are included in the first response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {'response': 'First response', 'context_id': '789'}
    mock_post.return_value = mock_response

    session = LLMAgent0Session("test_user", {"node": "test"})

    response = session.chat_without_tools("Test message")
    assert "First response" in response
    assert "Чтобы сбросить контекст, скажите 'Новый'." in response

    # Second response should not have instructions
    response2 = session.chat_without_tools("Another message")
    assert "Чтобы сбросить контекст" not in response2

    print("Reset instructions in first response: PASSED")
    return True

@patch('model.llm_agent0_session.requests.post')
def test_history_formatting(mock_post):
    """Test the history formatting for API requests."""
    mock_response = MagicMock()
    mock_response.json.return_value = {'response': 'Formatted response', 'context_id': '101'}
    mock_post.return_value = mock_response

    session = LLMAgent0Session("test_user", {"node": "test"})

    # Add a message
    session.chat_without_tools("Format test")

    # Check the conversation string format
    # The _send_request builds conversation as "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.message_history])
    expected_format = "System: " + LLMAgent0Session.system_prompt.strip() + "\n" + \
                      "System: Вы общаетесь с пользователем с ID: test_user.\n" + \
                      "System: Информация о ноде пользователя: <node_data> {'node': 'test'} </node_data>.\n" + \
                      "User: Format test"

    # Verify the call was made with correct format
    call_args = mock_post.call_args
    data = call_args[1]['json']  # json parameter
    conversation = data['message']

    # Check that conversation contains expected parts
    assert "System:" in conversation
    assert "User: Format test" in conversation
    assert "Assistant:" not in conversation  # Assistant not yet added when sending

    print("History formatting: PASSED")
    return True

def main():
    print("Testing LLMAgent0Session...")

    # Test API key extraction
    api_key_test = test_api_key_extraction()

    # Test request structure
    request_test = test_request_structure()

    # Test message history maintenance
    history_test = test_message_history_maintenance()

    # Test context reset
    reset_test = test_context_reset()

    # Test reset instructions
    instructions_test = test_reset_instructions_in_first_response()

    # Test history formatting
    format_test = test_history_formatting()

    if api_key_test and request_test and history_test and reset_test and instructions_test and format_test:
        print("\nAll tests PASSED!")
    else:
        print("\nSome tests FAILED!")

if __name__ == "__main__":
    main()