import os
import core_functions
import json
import logging

# Ensure the storage directory exists
os.makedirs('.storage', exist_ok=True)
assistant_file_path = '.storage/assistant.json'
assistant_name = "Sofia"
assistant_instructions_path = 'assistant/instructions.txt'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_assistant_instructions():
    """Load assistant instructions from file"""
    try:
        with open(assistant_instructions_path, 'r') as file:
            return file.read()
    except Exception as e:
        logging.error(f"Unable to read instruction file: {str(e)}")
        raise

def validate_tool_config(tool):
    """Validate tool configuration format (fix hierarchy issues)"""
    # Check if the 'function' key exists
    if 'function' not in tool:
        raise ValueError("Tool configuration is missing the 'function' key")

    # Extract the function object
    func = tool['function']

    # Check required fields inside the function object
    required_fields = ['name', 'description', 'parameters']
    missing = [field for field in required_fields if field not in func]

    if missing:
        raise ValueError(f"Missing fields in the 'function' object of tool configuration: {missing}")

    return tool

def generate_tools_config(tool_data):
    """Generate tool configurations compliant with v2 API requirements"""
    tools = [{"type": "file_search"}]

    if "tool_configs" in tool_data:
        for tool in tool_data["tool_configs"]:
            try:
                validated_tool = validate_tool_config(tool)
                tools.append({
                    "type": "function",
                    "function": {
                        "name": validated_tool["function"]["name"],
                        "description": validated_tool["function"].get("description", ""),
                        "parameters": validated_tool["function"]["parameters"]
                    }
                })
            except Exception as e:
                logging.error(f"Invalid tool configuration: {str(e)}")
                continue
    return tools

def create_vector_store(client, file_ids):
    """Create a vector store and upload files"""
    if not file_ids:
        return None

    try:
        vector_store = client.beta.vector_stores.create(
            name="Assistant Resource Files",
            file_ids=file_ids
        )
        logging.info(f"Vector store created successfully, ID: {vector_store.id}")
        return vector_store.id
    except Exception as e:
        logging.error(f"Failed to create vector store: {str(e)}")
        return None

def create_assistant(client, tool_data):
    """Create or update assistant (compatible with v2 API)"""
    tools = generate_tools_config(tool_data)

    if os.path.exists(assistant_file_path):
        try:
            with open(assistant_file_path, 'r') as file:
                assistant_data = json.load(file)
                assistant_id = assistant_data.get('assistant_id')

                if not assistant_id:
                    logging.info("Invalid assistant ID detected, creating a new assistant...")
                    return create_new_assistant(client, tool_data, tools)

                current_hashes = {
                    'tools_sum': core_functions.generate_hashsum('tools'),
                    'resources_sum': core_functions.generate_hashsum('resources'),
                    'assistant_sum': core_functions.generate_hashsum('assistant.py')
                }

                if compare_assistant_data_hashes(current_hashes, assistant_data):
                    logging.info("Assistant is up to date, using existing ID")
                    return assistant_id
                else:
                    return update_existing_assistant(client, assistant_id, tools)

        except Exception as e:
            logging.error(f"Failed to load assistant data: {str(e)}")
            return create_new_assistant(client, tool_data, tools)
    else:
        return create_new_assistant(client, tool_data, tools)

def update_existing_assistant(client, assistant_id, tools):
    """Update an existing assistant"""
    try:
        logging.info("Configuration changes detected, updating assistant...")
        file_ids = core_functions.get_resource_file_ids(client)
        vector_store_id = create_vector_store(client, file_ids)

        updated_assistant = client.beta.assistants.update(
            assistant_id=assistant_id,
            name=assistant_name,
            instructions=get_assistant_instructions(),
            model="gpt-4o-mini",
            tools=tools,
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                } if vector_store_id else None
            }
        )

        save_assistant_data({
            'assistant_id': updated_assistant.id,
            'tools_sum': core_functions.generate_hashsum('tools'),
            'resources_sum': core_functions.generate_hashsum('resources'),
            'assistant_sum': core_functions.generate_hashsum('assistant.py')
        }, assistant_file_path)

        logging.info(f"Assistant updated successfully, ID: {updated_assistant.id}")
        return updated_assistant.id

    except Exception as e:
        logging.error(f"Failed to update assistant: {str(e)}")
        return create_new_assistant(client, tool_data, tools)

def create_new_assistant(client, tool_data, tools):
    """Create a new assistant"""
    try:
        file_ids = core_functions.get_resource_file_ids(client)
        vector_store_id = create_vector_store(client, file_ids)

        assistant = client.beta.assistants.create(
            name=assistant_name,
            instructions=get_assistant_instructions(),
            model="gpt-4o-mini",
            tools=tools,
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                } if vector_store_id else None
            }
        )

        save_assistant_data({
            'assistant_id': assistant.id,
            'tools_sum': core_functions.generate_hashsum('tools'),
            'resources_sum': core_functions.generate_hashsum('resources'),
            'assistant_sum': core_functions.generate_hashsum('assistant.py')
        }, assistant_file_path)

        logging.info(f"New assistant created successfully, ID: {assistant.id}")
        return assistant.id

    except Exception as e:
        logging.error(f"Failed to create assistant: {str(e)}")
        raise

def save_assistant_data(data, path):
    """Save assistant data to a file"""
    try:
        with open(path, 'w') as file:
            json.dump(data, file, indent=2)
        logging.info(f"Assistant data saved to {path}")
    except Exception as e:
        logging.error(f"Failed to save data: {str(e)}")
        raise

def is_valid_assistant_data(data):
    """Validate assistant data integrity"""
    required_keys = ['assistant_id', 'tools_sum', 'resources_sum', 'assistant_sum']
    return all(data.get(key) for key in required_keys)

def compare_assistant_data_hashes(current, saved):
    """Compare hash values to determine if an update is needed"""
    if not is_valid_assistant_data(saved):
        return False
    return all(current[key] == saved[key] for key in 
               ['tools_sum', 'resources_sum', 'assistant_sum'])
