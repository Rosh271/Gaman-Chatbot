
import pytest
import json
import os
import openai
from main import app

@pytest.fixture(autouse=True)
def mock_openai_client(monkeypatch):
    class MockThread:
        def __init__(self):
            self.id = "mock_thread_id"
    
    class MockMessage:
        def __init__(self):
            self.content = [type('obj', (object,), {'text': {'value': 'Test response'}})]
            self.data = [self]
    
    class MockRun:
        def __init__(self):
            self.id = "mock_run_id"
            self.status = "completed"
    
    class MockThreads:
        def create(self):
            return MockThread()
        def retrieve(self, thread_id):
            return MockThread()
        
        class Messages:
            def create(self, thread_id, role, content):
                return MockMessage()
            def list(self, thread_id):
                return MockMessage()
        messages = Messages()
        
        class Runs:
            def create(self, thread_id, assistant_id):
                return MockRun()
            def retrieve(self, thread_id, run_id):
                return MockRun()
        runs = Runs()
    
    class MockBeta:
        threads = MockThreads()
    
    class MockClient:
        def __init__(self, api_key, default_headers=None):
            self.beta = MockBeta()
    
    monkeypatch.setattr(openai, "Client", MockClient)

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_voiceflow_start_endpoint_unauthorized(client):
    response = client.get('/voiceflow/start')
    assert response.status_code == 401

def test_voiceflow_start_endpoint_authorized(client):
    # Set test API key
    os.environ['CUSTOM_API_KEY'] = 'test_key'
    headers = {'X-API-KEY': 'test_key'}
    
    response = client.get('/voiceflow/start', headers=headers)
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'thread_id' in data
    assert 'status' in data
    assert data['status'] == 'success'

def test_voiceflow_chat_endpoint(client):
    os.environ['CUSTOM_API_KEY'] = 'test_key'
    headers = {
        'X-API-KEY': 'test_key',
        'Content-Type': 'application/json'
    }
    
    # First create a thread
    response = client.get('/voiceflow/start', headers=headers)
    data = json.loads(response.data)
    thread_id = data['thread_id']
    
    # Test chat endpoint
    chat_data = {
        'thread_id': thread_id,
        'message': 'Hello'
    }
    
    response = client.post('/voiceflow/chat', 
                          headers=headers,
                          data=json.dumps(chat_data))
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'text' in data
    assert 'status' in data
    assert data['status'] == 'success'
