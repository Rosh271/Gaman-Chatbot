import os
import core_functions
import json
import logging

logger = logging.getLogger(__name__)

def ensure_required_directories():
    """Ensure all required directories exist"""
    required_dirs = ['.storage', 'tools', 'resources', 'assistant']
    for directory in required_dirs:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")
        except Exception as e:
            logger.warning(f"Could not create directory {directory}: {str(e)}")

# Ensure required directories exist
ensure_required_directories()

# This is the storage path for the new assistant.json file
assistant_file_path = '.storage/assistant.json'
assistant_name = "Sofia"
assistant_instructions_path = 'assistant/instructions.txt'

# Create default instructions if they don't exist
if not os.path.exists(assistant_instructions_path):
    logger.info("Creating default instructions file...")
    try:
        with open(assistant_instructions_path, 'w') as f:
            f.write("I am Sofia, a helpful AI assistant.")
        logger.info("Created default instructions file")
    except Exception as e:
        logger.warning(f"Could not create default instructions: {str(e)}")

# Get the instructions for the assistant
def get_assistant_instructions():
    logger.info(f"Reading assistant instructions from {assistant_instructions_path}")
    try:
        # Open the file and read its contents
        with open(assistant_instructions_path, 'r') as file:
            instructions = file.read()
            logger.debug(f"Successfully read instructions ({len(instructions)} characters)")
            return instructions
    except Exception as e:
        logger.error(f"Failed to read instructions: {str(e)}")
        raise


# Create or load assistant
def create_assistant(client, tool_data):
    logger.info("Starting assistant creation/loading process")

    # If there is an assistant.json file, load the assistant
    if os.path.exists(assistant_file_path):
        logger.info(f"Found existing assistant file at {assistant_file_path}")

        try:
            with open(assistant_file_path, 'r') as file:
                assistant_data = json.load(file)
                logger.debug(f"Loaded assistant data: {json.dumps(assistant_data, indent=2)}")

                assistant_id = assistant_data.get('assistant_id')

                # If assistant_id is empty, create a new assistant instead of updating
                if not assistant_id:
                    logger.warning("Empty assistant_id in file, creating new assistant")
                    return create_new_assistant(client, tool_data)

                logger.info(f"Attempting to use existing assistant ID: {assistant_id}")

                # Generate current hash sums
                current_tool_hashsum = core_functions.generate_hashsum('tools')
                current_resource_hashsum = core_functions.generate_hashsum('resources')
                current_assistant_hashsum = core_functions.generate_hashsum(
                    'assistant.py')

                current_assistant_data = {
                    'tools_sum': core_functions.generate_hashsum('tools'),
                    'resources_sum': core_functions.generate_hashsum('resources'),
                    'assistant_sum': core_functions.generate_hashsum('assistant.py')
                }

                # Assuming assistant_data is loaded from a JSON file
                if compare_assistant_data_hashes(current_assistant_data, assistant_data):

                    print("Assistant is up-to-date. Loaded existing assistant ID.")

                    return assistant_id
                else:
                    print("Changes detected. Updating assistant...")

                    # Find and validate all given files
                    file_ids = core_functions.get_resource_file_ids(client)

                    try:
                        # Update the assistant
                        # Update assistant properties
                        assistant = client.beta.assistants.update(
                            assistant_id=assistant_id,
                            name=assistant_name,
                            instructions=get_assistant_instructions(),
                            model="gpt-4-1106-preview",
                            tools=[{
                                "type": "file_search"
                            }] + tool_data["tool_configs"])

                        # Update file attachments if there are any
                        if file_ids:
                            assistant = client.beta.assistants.update(
                                assistant_id=assistant_id,
                                file_ids=file_ids,
                                instructions=get_assistant_instructions(),
                                name=assistant_name,
                                model="gpt-4-1106-preview",
                                tools=[{"type": "file_search"}] + tool_data["tool_configs"])

                        # Build the JSON
                        assistant_data = {
                            'assistant_id': assistant.id,
                            'tools_sum': current_tool_hashsum,
                            'resources_sum': current_resource_hashsum,
                            'assistant_sum': current_assistant_hashsum,
                        }

                        save_assistant_data(assistant_data, assistant_file_path)

                        print(f"Assistant (ID: {assistant_id}) updated successfully.")

                    except Exception as e:
                        print(f"Error updating assistant: {e}")
        except Exception as e:
            logger.error(f"Error loading assistant data: {str(e)}")
            raise
    else:
        # Create a new assistant

        # Find and validate all given files
        file_ids = core_functions.get_resource_file_ids(client)

        # Create the assistant
        assistant = client.beta.assistants.create(
            instructions=get_assistant_instructions(),
            name=assistant_name,
            model="gpt-4-1106-preview",
            tools=[{
                "type": "file_search"
            }] + tool_data["tool_configs"])

        if file_ids:
            assistant = client.beta.assistants.update(
                assistant_id=assistant.id,
                tools=[{"type": "file_search"}] + tool_data["tool_configs"],
                file_ids=file_ids,
                instructions=get_assistant_instructions(),
                name=assistant_name,
                model="gpt-4-1106-preview")

        # Print the assistant ID or any other details you need
        print(f"Assistant ID: {assistant.id}")

        #Generate the hashsums for tools, resources, and the assistant.json file
        tool_hashsum = core_functions.generate_hashsum('tools')
        resource_hashsum = core_functions.generate_hashsum('resources')
        assistant_hashsum = core_functions.generate_hashsum('assistant.py')

        # Build the JSON
        assistant_data = {
            'assistant_id': assistant.id,
            'tools_sum': tool_hashsum,
            'resources_sum': resource_hashsum,
            'assistant_sum': assistant_hashsum,
        }

        save_assistant_data(assistant_data, assistant_file_path)

        print(f"Assistant has been created with ID: {assistant.id}")

        assistant_id = assistant.id

    return assistant_id


# Save the assistant to a file
def save_assistant_data(assistant_data, file_path):
  """
  Save assistant data into a JSON file.

  :param assistant_data: Dictionary containing assistant's data.
  :param file_path: Path where the JSON file will be saved.
  """
  try:
    # Ensure the .storage directory exists
    storage_dir = os.path.dirname(file_path)
    os.makedirs(storage_dir, exist_ok=True)
    logging.info(f"Storage directory ensured: {storage_dir}")

    # Save the data
    with open(file_path, 'w') as file:
      json.dump(assistant_data, file, indent=2)
      logging.info(f"Assistant data saved successfully to {file_path}")

  except Exception as e:
    logging.error(f"Error saving assistant data to {file_path}: {str(e)}")
    raise FileNotFoundError(f"Failed to save assistant data: {str(e)}")


# Checks if the Assistant JSON has all required fields
def is_valid_assistant_data(assistant_data):
  """
  Check if the assistant data contains valid values for all required keys.

  :param assistant_data: Dictionary containing assistant's data.
  :return: Boolean indicating whether the data is valid.
  """
  required_keys = [
      'assistant_id', 'tools_sum', 'resources_sum', 'assistant_sum'
  ]
  return all(key in assistant_data and assistant_data[key]
             for key in required_keys)


#Compares if all of the fields match with the current hashes
def create_new_assistant(client, tool_data):
    """Create a new assistant and return its ID"""
    logger.info("Creating new assistant...")
    try:
        # Try to get file IDs first
        try:
            file_ids = core_functions.get_resource_file_ids(client)
            logger.info(f"Found {len(file_ids)} resource files to attach")
        except Exception as file_error:
            logger.warning(f"Could not get resource files: {str(file_error)}")
            file_ids = []

        # Create the assistant with all configuration at once
        assistant = client.beta.assistants.create(
            instructions=get_assistant_instructions(),
            name=assistant_name,
            model="gpt-4-1106-preview",
            tools=[{
                "type": "file_search"
            }] + tool_data["tool_configs"],
            files=file_ids if file_ids else None)

        logger.info(f"Assistant created with ID: {assistant.id}")

        # Generate the hashsums
        tool_hashsum = core_functions.generate_hashsum('tools')
        resource_hashsum = core_functions.generate_hashsum('resources')
        assistant_hashsum = core_functions.generate_hashsum('assistant.py')

        # Build and save the JSON
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

def compare_assistant_data_hashes(current_data, saved_data):
  """
  Compare current assistant data with saved data.

  :param current_data: Current assistant data.
  :param saved_data: Saved assistant data from JSON file.
  :return: Boolean indicating whether the data matches.
  """
  if not is_valid_assistant_data(saved_data):
    return False

  return (current_data['tools_sum'] == saved_data['tools_sum']
          and current_data['resources_sum'] == saved_data['resources_sum']
          and current_data['assistant_sum'] == saved_data['assistant_sum'])