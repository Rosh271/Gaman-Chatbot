import os
import core_functions
import json
import logging

# Ensure storage directory exists
os.makedirs('.storage', exist_ok=True)
assistant_file_path = '.storage/assistant.json'
assistant_name = "Sofia"
assistant_instructions_path = 'assistant/instructions.txt'

def get_assistant_instructions():
    with open(assistant_instructions_path, 'r') as file:
        return file.read()

def create_assistant(client, tool_data):
    if os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            assistant_id = assistant_data.get('assistant_id')

            if not assistant_id:
                return create_new_assistant(client, tool_data)

            current_tool_hashsum = core_functions.generate_hashsum('tools')
            current_resource_hashsum = core_functions.generate_hashsum('resources')
            current_assistant_hashsum = core_functions.generate_hashsum('assistant.py')

            current_assistant_data = {
                'tools_sum': current_tool_hashsum,
                'resources_sum': current_resource_hashsum,
                'assistant_sum': current_assistant_hashsum,
            }

            if compare_assistant_data_hashes(current_assistant_data, assistant_data):
                print("Assistant is up-to-date. Loaded existing assistant ID.")
                return assistant_id

            print("Changes detected. Updating assistant...")
            # Get file IDs and prepare tool_resources
            file_ids = core_functions.get_resource_file_ids(client)
            tool_resources = {}

            if file_ids:
                tool_resources = {
                    "code_interpreter": {"file_ids": file_ids},
                    "file_search": {"vector_store_ids": []}
                }

            try:
                assistant = client.assistants.update(
                    assistant_id=assistant_id,
                    name=assistant_name,
                    instructions=get_assistant_instructions(),
                    model="gpt-4-turbo-preview",
                    tools=[{"type": "file_search"}, {"type": "code_interpreter"}] + tool_data["tool_configs"]
                )

                assistant_data = {
                    'assistant_id': assistant.id,
                    'tools_sum': current_tool_hashsum,
                    'resources_sum': current_resource_hashsum,
                    'assistant_sum': current_assistant_hashsum,
                }

                save_assistant_data(assistant_data, assistant_file_path)
                print(f"Assistant updated successfully.")
                return assistant.id

            except Exception as e:
                print(f"Error updating assistant: {e}")
                return None

    return create_new_assistant(client, tool_data)

def create_new_assistant(client, tool_data):
    file_ids = core_functions.get_resource_file_ids(client)
    tool_resources = {}

    if file_ids:
        tool_resources = {
            "code_interpreter": {"file_ids": file_ids},
            "file_search": {"vector_store_ids": []}
        }

    try:
        assistant = client.assistants.create(
            instructions=get_assistant_instructions(),
            name=assistant_name,
            model="gpt-4-turbo-preview",
            tools=[{"type": "file_search"}, {"type": "code_interpreter"}] + tool_data["tool_configs"]
        )

        tool_hashsum = core_functions.generate_hashsum('tools')
        resource_hashsum = core_functions.generate_hashsum('resources')
        assistant_hashsum = core_functions.generate_hashsum('assistant.py')

        assistant_data = {
            'assistant_id': assistant.id,
            'tools_sum': tool_hashsum,
            'resources_sum': resource_hashsum,
            'assistant_sum': assistant_hashsum,
        }

        save_assistant_data(assistant_data, assistant_file_path)
        print(f"New assistant created with ID: {assistant.id}")
        return assistant.id

    except Exception as e:
        print(f"Error creating assistant: {e}")
        return None

def save_assistant_data(assistant_data, file_path):
    try:
        storage_dir = os.path.dirname(file_path)
        os.makedirs(storage_dir, exist_ok=True)
        with open(file_path, 'w') as file:
            json.dump(assistant_data, file, indent=2)
    except Exception as e:
        logging.error(f"Error saving assistant data: {str(e)}")
        raise FileNotFoundError(f"Failed to save assistant data: {str(e)}")

def is_valid_assistant_data(assistant_data):
    required_keys = ['assistant_id', 'tools_sum', 'resources_sum', 'assistant_sum']
    return all(key in assistant_data and assistant_data[key] for key in required_keys)

def compare_assistant_data_hashes(current_data, saved_data):
    if not is_valid_assistant_data(saved_data):
        return False
    return (current_data['tools_sum'] == saved_data['tools_sum']
            and current_data['resources_sum'] == saved_data['resources_sum']
            and current_data['assistant_sum'] == saved_data['assistant_sum'])