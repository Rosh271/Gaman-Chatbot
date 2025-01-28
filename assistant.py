import core_functions

def create_new_assistant(client, tool_data):
    """Create a new assistant with all properties set at once"""
    logger.info("Creating new assistant...")
    try:
        # Get file IDs first
        file_ids = core_functions.get_resource_file_ids(client)

        # Create the assistant with the correct parameter name for file_ids
        create_params = {
            "name": assistant_name,
            "instructions": get_assistant_instructions(),
            "model": "gpt-4-1106-preview",
            "tools": [{"type": "file_search"}] + tool_data["tool_configs"]
        }

        # Only add file_ids if we have any
        if file_ids:
            create_params["file_ids"] = file_ids

        # Create the assistant with all properties at once
        assistant = client.beta.assistants.create(**create_params)

        logger.info(f"New assistant created with ID: {assistant.id}")

        # Generate hashsums
        tool_hashsum = core_functions.generate_hashsum('tools')
        resource_hashsum = core_functions.generate_hashsum('resources')
        assistant_hashsum = core_functions.generate_hashsum('assistant.py')

        # Build and save assistant data
        assistant_data = {
            'assistant_id': assistant.id,
            'tools_sum': tool_hashsum,
            'resources_sum': resource_hashsum,
            'assistant_sum': assistant_hashsum,
        }

        save_assistant_data(assistant_data, assistant_file_path)
        logger.info(f"Assistant data saved successfully")

        return assistant.id

    except Exception as e:
        logger.error(f"Failed to create new assistant: {str(e)}")
        raise

# Also update the update section in create_assistant function
import logging

logger = logging.getLogger(__name__)

def create_assistant(client, tool_data):
    try:
        # First create a new assistant
        assistant = create_new_assistant(client, tool_data)
        update_params = {
            "assistant_id": assistant.id,
            "name": assistant_name,
            "instructions": get_assistant_instructions(),
            "model": "gpt-4-1106-preview",
            "tools": [{"type": "file_search"}] + tool_data["tool_configs"]
        }

        if file_ids:
            update_params["file_ids"] = file_ids

        assistant = client.beta.assistants.update(**update_params)
        return assistant.id
    except Exception as e:
        logger.error(f"Failed to update assistant: {str(e)}")
        raise