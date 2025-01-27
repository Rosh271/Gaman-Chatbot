
"""
Using Voiceflow Endpoints with Authentication

To interact with the Voiceflow endpoints, you need to ensure proper authentication. 
This involves setting the X-API-KEY in the request header and using a secret CUSTOM_API_KEY 
within your Replit template. Follow these steps for successful authorization:

1. Set CUSTOM_API_KEY:
   - In your Replit template's Secrets tool, add a new secret with key 'CUSTOM_API_KEY'
   - Use a strong, randomly generated value for enhanced security

2. Include Authentication:
   - Add 'X-API-KEY' header to all requests matching your CUSTOM_API_KEY value
"""

import logging
from flask import request, jsonify, abort
import core_functions
import os
import hmac
import hashlib
import time

# Configure logging for this module
logging.basicConfig(level=logging.INFO)

def requires_mapping():
    return False

def validate_api_key():
    """Validate API key with timing-attack safe comparison"""
    api_key = request.headers.get('X-API-KEY')
    stored_key = os.environ.get('CUSTOM_API_KEY')
    
    if not api_key or not stored_key:
        return False
        
    return hmac.compare_digest(api_key.encode(), stored_key.encode())

def setup_routes(app, client, tool_data, assistant_id):
    @app.before_request
    def authenticate():
        if request.path.startswith('/voiceflow'):
            if not validate_api_key():
                logging.warning(f"Invalid API key attempt from {request.remote_addr}")
                abort(401, description="Invalid API key")

    @app.route('/voiceflow/start', methods=['GET'])
    def start_conversation():
        logging.info("Starting a new conversation...")
        thread = client.beta.threads.create()
        logging.info(f"New thread created with ID: {thread.id}")
        return jsonify({"thread_id": thread.id})

    @app.route('/voiceflow/chat', methods=['POST'])
    def chat():
        logging.info("Entered chat function")
        data = request.json
        thread_id = data.get('thread_id')
        user_input = data.get('message', '')

        if not thread_id:
            logging.error("Error: Missing thread_id")
            return jsonify({"error": "Missing thread_id"}), 400

        logging.info(f"Received message: {user_input} for thread ID: {thread_id}")
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_input
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        
        core_functions.process_tool_calls(client, thread_id, run.id, tool_data)

        messages = client.beta.threads.messages.list(thread_id=thread_id)
        response = messages.data[0].content[0].text.value
        logging.info(f"Assistant response: {response}")
        return jsonify({"response": response})
