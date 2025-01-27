import os
import core_functions
import json
import logging
from typing import Optional, Dict, Any

# Storage paths
assistant_file_path = '.storage/assistant.json'
assistant_name = "Sofia"
assistant_instructions_path = 'assistant/instructions.txt'


class AssistantError(Exception):
    """Custom exception for Assistant-related errors"""
    pass


def get_assistant_instructions() -> str:
    """Get the instructions for the assistant from file"""
    try:
        with open(assistant_instructions_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        raise AssistantError(
            f"Instructions file not found at {assistant_instructions_path}")
    except Exception as e:
        raise AssistantError(f"Error reading instructions: {str(e)}")


def save_assistant_data(assistant_data: Dict[str, Any],
                        file_path: str) -> None:
    """Save assistant data into a JSON file with error handling"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            json.dump(assistant_data, file, indent=2)
    except Exception as e:
        raise AssistantError(f"Error saving assistant data: {str(e)}")


def is_valid_assistant_data(assistant_data: Dict[str, Any]) -> bool:
    """Validate assistant data structure"""
    required_keys = [
        'assistant_id', 'tools_sum', 'resources_sum', 'assistant_sum'
    ]
    return all(key in assistant_data and assistant_data[key]
               for key in required_keys)


def compare_assistant_data_hashes(current_data: Dict[str, str],
                                  saved_data: Dict[str, str]) -> bool:
    """Compare assistant data hashes"""
    if not is_valid_assistant_data(saved_data):
        return False

    return all(current_data[key] == saved_data[key]
               for key in ['tools_sum', 'resources_sum', 'assistant_sum'])


def create_assistant(client, tool_data: Dict[str, Any]) -> Optional[str]:
    """Create or load an OpenAI assistant with v2 API support"""
    try:
        if os.path.exists(assistant_file_path):
            return _update_existing_assistant(client, tool_data)
        else:
            return _create_new_assistant(client, tool_data)
    except Exception as e:
        logging.error(f"Assistant creation/update failed: {str(e)}")
        raise AssistantError(f"Assistant operation failed: {str(e)}")


def _create_new_assistant(client, tool_data: Dict[str, Any]) -> str:
    """Create a new assistant with v2 API"""
    try:
        # Get file IDs for resources
        file_ids = core_functions.get_resource_file_ids(client)

        # Create assistant with v2 API
        assistant = client.beta.assistants.create(
            name=assistant_name,
            instructions=get_assistant_instructions(),
            model="gpt-4-1106-preview",
            tools=[{
                "type": "retrieval"
            }] + tool_data["tool_configs"],
            file_ids=file_ids)

        # Generate hash sums
        assistant_data = {
            'assistant_id': assistant.id,
            'tools_sum': core_functions.generate_hashsum('tools'),
            'resources_sum': core_functions.generate_hashsum('resources'),
            'assistant_sum': core_functions.generate_hashsum('assistant.py')
        }

        save_assistant_data(assistant_data, assistant_file_path)
        logging.info(f"New assistant created with ID: {assistant.id}")
        return assistant.id

    except Exception as e:
        raise AssistantError(f"Failed to create new assistant: {str(e)}")


def _update_existing_assistant(client, tool_data: Dict[str, Any]) -> str:
    """Update existing assistant with v2 API"""
    try:
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)

        assistant_id = assistant_data['assistant_id']

        # Generate current hashes
        current_data = {
            'tools_sum': core_functions.generate_hashsum('tools'),
            'resources_sum': core_functions.generate_hashsum('resources'),
            'assistant_sum': core_functions.generate_hashsum('assistant.py')
        }

        if compare_assistant_data_hashes(current_data, assistant_data):
            logging.info("Assistant is up-to-date")
            return assistant_id

        # Update needed - get new file IDs
        file_ids = core_functions.get_resource_file_ids(client)

        # Update assistant with v2 API
        assistant = client.beta.assistants.update(
            assistant_id=assistant_id,
            name=assistant_name,
            instructions=get_assistant_instructions(),
            model="gpt-4-1106-preview",
            tools=[{
                "type": "retrieval"
            }] + tool_data["tool_configs"],
            file_ids=file_ids)

        # Update stored data
        assistant_data.update({
            'tools_sum': current_data['tools_sum'],
            'resources_sum': current_data['resources_sum'],
            'assistant_sum': current_data['assistant_sum']
        })

        save_assistant_data(assistant_data, assistant_file_path)
        logging.info(f"Assistant updated successfully: {assistant_id}")
        return assistant_id

    except Exception as e:
        raise AssistantError(f"Failed to update existing assistant: {str(e)}")