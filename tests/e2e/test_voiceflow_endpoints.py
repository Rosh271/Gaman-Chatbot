import pytest
from main import app
import json
import os

@pytest.fixture
def client():
    app.config['TESTING'] = True
    os.environ['CUSTOM_API_KEY'] = 'test-token'
    with app.test_client() as client:
        yield client

def test_voiceflow_start_endpoint_unauthorized(client):
    # Test without headers first
    response = client.get('/voiceflow/start')
    assert response.status_code == 401

    # Define headers for authorized request
    headers = {
        'X-API-KEY': 'test-token',
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
