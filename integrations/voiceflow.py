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

            # Force initial message to avoid default greeting
            initial_message = client.beta.threads.messages.create(
                thread_id=thread_id,
                role="assistant",
                content="Welcome to Domar Painting! I'm here to help with your painting needs. Are you interested in interior painting, exterior painting, or would you like to learn about our process?"
            )

            return jsonify({
                "thread_id": thread_id,
                "status": "success",
                "message": "Thread created successfully",
                "initial_message": initial_message.content[0].text.value
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

            # Track conversation state
            conversation_state = client.beta.threads.messages.list(thread_id=thread_id)
            message_count = len(conversation_state.data)

            # Enhanced loop detection with common variations
            GREETING_VARIATIONS = [
                "¿cómo te puedo ayudar?",
                "como te puedo ayudar",
                "how can i help you",
                "how may i help you",
                "how can i assist you"
            ]

            FORCED_RESPONSES = [
                "Let's discuss your painting project. Are you interested in interior or exterior painting?",
                "What type of painting service are you looking for today? We offer both residential and commercial services.",
                "Would you like to learn about our interior painting, exterior painting, or our professional painting process?",
                "I can help you with specific painting services. Are you looking for residential or commercial painting?",
                "Let me tell you about our services. We specialize in interior and exterior painting. Which interests you?"
            ]

            # Prevent loops by checking recent messages with enhanced detection
            if message_count >= 2:
                last_messages = conversation_state.data[:3]  # Check last 3 messages
                greeting_count = sum(
                    1 for msg in last_messages
                    if any(greeting in msg.content[0].text.value.strip().lower() 
                           for greeting in GREETING_VARIATIONS)
                )

                if greeting_count >= 2:  # If we see 2 or more greetings in last 3 messages
                    # Get the last non-greeting message from user if exists
                    user_context = next(
                        (msg.content[0].text.value
                         for msg in conversation_state.data
                         if msg.role == "user" and
                         not any(greeting in msg.content[0].text.value.strip().lower()
                               for greeting in GREETING_VARIATIONS)),
                        None
                    )

                    if user_context:
                        response = f"I understand you're asking about {user_context}. Could you please specify what exactly you'd like to know about this topic?"
                    else:
                        response = "I notice we might be stuck. Let me help you with our painting services. Are you interested in interior painting, exterior painting, or would you like to know about our process?"

                    return jsonify({
                        "text": response,
                        "status": "success",
                        "thread_id": thread_id
                    })

            # Additional check for repeated patterns
            if message_count >= 3:
                last_three = [msg.content[0].text.value.strip().lower() for msg in conversation_state.data[-3:]]
                if len(set(last_three)) <= 1:  # If last three messages are the same
                    return jsonify({
                        "text": "Let's focus on your painting needs. What specific painting service can I help you with today?",
                        "status": "success",
                        "thread_id": thread_id
                    })

            try:
                thread = client.beta.threads.retrieve(thread_id=thread_id)
                if not thread or not thread.id:
                    raise ValueError("Thread not found")

                logging.info(f"Thread validated successfully: {thread_id}")

            except Exception as e:
                logging.error(f"Thread validation failed: {str(e)}")
                # Instead of creating new thread, return error
                return handle_error("Invalid thread ID. Please start a new conversation.", 400)

            try:
                # Create message in thread
                message = client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=user_input
                )

                # Create and process run with retry mechanism
                max_retries = 3
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        run = client.beta.threads.runs.create(
                            thread_id=thread_id,
                            assistant_id=assistant_id
                        )
                        core_functions.process_tool_calls(client, thread_id, run.id, tool_data)

                # Wait for run to complete
                while True:
                    run_status = client.beta.threads.runs.retrieve(
                        thread_id=thread_id,
                        run_id=run.id
                    )
                    if run_status.status == 'completed':
                        break
                    elif run_status.status == 'failed':
                        raise Exception("Run failed")
                    time.sleep(1)

                        break
                    except Exception as e:
                        retry_count += 1
                        if retry_count == max_retries:
                            raise e
                        time.sleep(1)  # Wait before retry

                # Retrieve response - get the latest assistant message
                messages = client.beta.threads.messages.list(
                    thread_id=thread_id,
                    order="desc",
                    limit=1
                )

                if not messages.data:
                    return handle_error("No response received from assistant")

                message = messages.data[0]

                # Verify this is an assistant message
                if message.role != "assistant":
                    return handle_error("Invalid response from assistant")

                formatted_response = {
                    "text": "",
                    "media": [],
                    "status": "success",
                    "thread_id": thread_id,
                    "response_id": message.id
                }

                if message.content and len(message.content) > 0:
                    content = message.content[0]
                    if hasattr(content, 'text'):
                        response_text = content.text.value
                        # Enhanced response handling with better context management
                        response_lower = response_text.strip().lower()

                        if response_lower in ["¿cómo te puedo ayudar?", "como te puedo ayudar", "how can i help you?"]:
                            # Get conversation context
                            prev_messages = client.beta.threads.messages.list(
                                thread_id=thread_id,
                                limit=5  # Look at last 5 messages for better context
                            ).data

                            # Try to find the last meaningful user input
                            user_context = None
                            for msg in prev_messages:
                                if msg.role == "user":
                                    user_text = msg.content[0].text.value.strip().lower()
                                    # Skip greetings or very short inputs
                                    if len(user_text) > 10 and not any(greeting in user_text for greeting in ["hello", "hi", "hey", "hola"]):
                                        user_context = msg.content[0].text.value
                                        break

                            if user_context:
                                formatted_response["text"] = f"Regarding your interest in {user_context}, what specific details would you like to know about our painting services?"
                            elif message_count == 1:  # First message
                                formatted_response["text"] = "Welcome! I'm here to help with your painting needs. Are you interested in interior painting, exterior painting, or would you like to learn about our process?"
                            else:
                                formatted_response["text"] = "Let me help you with our painting services. What type of painting project are you interested in?"
                        else:
                            formatted_response["text"] = response_text
                    if hasattr(content, 'image_file'):
                        formatted_response["media"].append({
                            "type": "image",
                            "url": content.image_file.file_id
                        })

                logging.info(f"Response prepared: {formatted_response}")
                return jsonify(formatted_response)

            except Exception as e:
                return handle_error(f"Error processing message: {str(e)}")

        except Exception as e:
            return handle_error(f"Invalid request: {str(e)}")