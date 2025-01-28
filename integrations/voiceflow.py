import logging
from flask import request, jsonify, abort
import core_functions
import os
import hmac
import time
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)

def requires_mapping():
    return False

def validate_api_key():
    api_key = request.headers.get('X-API-KEY')
    stored_key = os.environ.get('CUSTOM_API_KEY')

    if not api_key or not stored_key:
        return False
    return hmac.compare_digest(api_key.encode(), stored_key.encode())

def handle_error(error_msg: str, status_code: int = 400) -> tuple[Dict[str, str], int]:
    logging.error(error_msg)
    return jsonify({"error": error_msg}), status_code

def setup_routes(app, client, tool_data, assistant_id):
    @app.before_request
    def authenticate():
        if request.path.startswith('/voiceflow'):
            if not validate_api_key():
                return handle_error("Invalid API key", 401)

    @app.route('/voiceflow/start', methods=['GET'])
    def start_conversation():
        try:
            logging.info("Starting a new conversation...")
            thread = client.beta.threads.create()
            thread_id = thread.id
            logging.info(f"New thread created with ID: {thread_id}")
            return jsonify({
                "thread_id": thread_id,
                "status": "success",
                "message": "Thread created successfully"
            })
        except Exception as e:
            return handle_error(f"Failed to start conversation: {str(e)}")

    @app.route('/voiceflow/chat', methods=['POST'])
    def chat():
        try:
            logging.info("Processing chat request")
            if not request.is_json:
                return handle_error("Request must include 'Content-Type: application/json' header")

            data = request.get_json()
            if not data:
                return handle_error("No JSON data provided")

            thread_id = data.get('thread_id')
            user_input = data.get('message', '').strip()

            if not thread_id:
                return handle_error("Missing thread_id. Please call /voiceflow/start first")

            if not user_input:
                return handle_error("Message cannot be empty")

            # Verify thread exists and wait for completion
            try:
                thread = client.beta.threads.retrieve(thread_id=thread_id)
                if not thread or not thread.id:
                    raise ValueError("Thread not found")

                logging.info(f"Thread validated successfully: {thread_id}")
                logging.info(f"Processing message: {user_input} for thread ID: {thread_id}")

            except Exception as e:
                logging.error(f"Thread validation failed: {str(e)}")
                # Create new thread if validation fails
                thread = client.beta.threads.create()
                thread_id = thread.id
                logging.info(f"Created new thread with ID: {thread_id}")
                return jsonify({
                    "error": "Invalid thread. New thread created.",
                    "thread_id": thread_id,
                    "status": "new_thread"
                })

            try:
                # Create message in thread
                message = client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=user_input
                )

                # Create and process run
                run = client.beta.threads.runs.create(
                    thread_id=thread_id,
                    assistant_id=assistant_id
                )

                core_functions.process_tool_calls(client, thread_id, run.id, tool_data)

                # Retrieve response
                messages = client.beta.threads.messages.list(thread_id=thread_id)
                message = messages.data[0]

                # Process response content
                formatted_response = {
                    "text": "",
                    "media": [],
                    "status": "success",
                    "thread_id": thread_id
                }

                formatted_response["text"] = message.content[0].text.value if hasattr(message.content[0], 'text') else ""
                if hasattr(message.content[0], 'image_file'):
                    formatted_response["media"].append({
                        "type": "image",
                        "url": message.content[0].image_file.file_id
                    })

                logging.info(f"Response prepared: {formatted_response}")
                return jsonify(formatted_response)

            except Exception as e:
                return handle_error(f"Error processing message: {str(e)}")

        except Exception as e:
            return handle_error(f"Invalid request: {str(e)}")