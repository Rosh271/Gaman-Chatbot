
import pytest
import os
import json
from assistant import create_assistant, get_assistant_instructions
import openai

@pytest.fixture
def mock_client(monkeypatch):
    class MockAssistant:
        def __init__(self):
            self.id = "test_assistant_id"
    
    class MockBeta:
        class MockAssistants:
            def create(self, **kwargs):
                return MockAssistant()
                
            def update(self, **kwargs):
                return MockAssistant()
        assistants = MockAssistants()
    
    class MockOpenAI:
        beta = MockBeta()
        
    return MockOpenAI()

def test_create_assistant_new(mock_client):
    # Remove existing assistant file if it exists
    if os.path.exists('.storage/assistant.json'):
        os.rename('.storage/assistant.json', '.storage/assistant.json.bak')
    
    tool_data = {
        "tool_configs": [],
        "function_map": {}
    }
    
    assistant_id = create_assistant(mock_client, tool_data)
    assert assistant_id == "test_assistant_id"
    
    # Restore original assistant file if it existed
    if os.path.exists('.storage/assistant.json.bak'):
        os.rename('.storage/assistant.json.bak', '.storage/assistant.json')

def test_get_assistant_instructions():
    instructions = get_assistant_instructions()
    assert isinstance(instructions, str)
    assert len(instructions) > 0
