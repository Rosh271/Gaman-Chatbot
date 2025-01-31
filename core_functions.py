# import json
# import hashlib
# from datetime import datetime
# import importlib.util
# from flask import request, abort
# import time
# import logging
# import openai
# import os
# import sqlite3
# from packaging import version

# CUSTOM_API_KEY = os.environ.get('CUSTOM_API_KEY')
# mappings_db_path = '.storage/chat_mappings.db'


# # Initialize a mapping db for chat mappings
# def initialize_mapping_db():
#   conn = sqlite3.connect(mappings_db_path)
#   cursor = conn.cursor()
#   cursor.execute('''
#       CREATE TABLE IF NOT EXISTS chat_mappings (
#           integration TEXT,
#           assistant_id TEXT,
#           chat_id TEXT,
#           thread_id TEXT,
#           date_of_creation TIMESTAMP,
#           PRIMARY KEY (integration, chat_id)
#       )
#   ''')
#   conn.commit()
#   conn.close()


# # Save chat mapping to the db
# def get_chat_mapping(integration, chat_id=None, assistant_id=None):
#   conn = sqlite3.connect(mappings_db_path)
#   cursor = conn.cursor()

#   query = "SELECT * FROM chat_mappings WHERE integration = ?"
#   params = [integration]

#   if chat_id:
#     query += " AND chat_id = ?"
#     params.append(chat_id)
#   elif assistant_id:
#     query += " AND assistant_id = ?"
#     params.append(assistant_id)

#   cursor.execute(query, params)
#   rows = cursor.fetchall()

#   conn.close()

#   return [
#       dict(
#           zip([
#               "integration", "assistant_id", "chat_id", "thread_id",
#               "date_of_creation"
#           ], row)) for row in rows
#   ]


# # Gets a specific value from the db result
# def get_value_from_mapping(data, key):
#   if data and isinstance(data, list) and isinstance(data[0], dict):
#     return data[0].get(key)
#   return None


# # Adds or updates a chat mapping
# def update_chat_mapping(integration, chat_id, assistant_id, thread_id):
#   conn = sqlite3.connect(mappings_db_path)
#   cursor = conn.cursor()

#   date_of_creation = datetime.now()

#   cursor.execute(
#       '''
#       INSERT OR REPLACE INTO chat_mappings (integration, chat_id, assistant_id, thread_id, date_of_creation)
#       VALUES (?, ?, ?, ?, ?)
#   ''', (integration, chat_id, assistant_id, thread_id, date_of_creation))

#   conn.commit()
#   conn.close()


# def delete_chat_mapping(integration, chat_id):
#   conn = sqlite3.connect(mappings_db_path)
#   cursor = conn.cursor()

#   cursor.execute(
#       'DELETE FROM chat_mappings WHERE integration = ? AND chat_id = ?',
#       (integration, chat_id))

#   conn.commit()
#   conn.close()


# # Function to check API key
# def check_api_key():
#   api_key = request.headers.get('X-API-KEY')
#   if api_key != CUSTOM_API_KEY:
#     abort(401)  # Unauthorized access


# # Check the current OpenAI version
# def check_openai_version():
#   required_version = version.parse("1.1.1")
#   current_version = version.parse(openai.__version__)
#   if current_version < required_version:
#     raise ValueError(
#         f"Error: OpenAI version {openai.__version__} is less than the required version 1.1.1"
#     )
#   else:
#     logging.info("OpenAI version is compatible.")


# # Process the actions that are initiated by the assistants API
# def process_tool_calls(client, thread_id, run_id, tool_data):
#   while True:
#     run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
#                                                    run_id=run_id)
#     if run_status.status == 'completed':
#       break
#     elif run_status.status == 'requires_action':
#       for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
#         function_name = tool_call.function.name

#         try:
#           arguments = json.loads(tool_call.function.arguments)
#         except json.JSONDecodeError as e:
#           logging.error(
#               f"JSON decoding failed: {e.msg}. Input: {tool_call.function.arguments}"
#           )
#           arguments = {}  # Set to default value

#         # Use the function map from tool_data
#         if function_name in tool_data["function_map"]:
#           function_to_call = tool_data["function_map"][function_name]
#           output = function_to_call(arguments)
#           client.beta.threads.runs.submit_tool_outputs(thread_id=thread_id,
#                                                        run_id=run_id,
#                                                        tool_outputs=[{
#                                                            "tool_call_id":
#                                                            tool_call.id,
#                                                            "output":
#                                                            json.dumps(output)
#                                                        }])
#         else:
#           logging.warning(f"Function {function_name} not found in tool data.")
#       time.sleep(2)


# # Constants for file handling
# MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
# ALLOWED_FILE_TYPES = {'.txt', '.pdf', '.doc', '.docx', '.json', '.csv'}
# TEMP_UPLOAD_DIR = '.temp_uploads'
# FILE_METADATA_PATH = '.storage/file_metadata.json'

# class FileHandlingError(Exception):
#     """Custom exception for file handling errors"""
#     pass

# def validate_file(file_path):
#     """Validate file size and type"""
#     if not os.path.exists(file_path):
#         raise FileHandlingError(f"File not found: {file_path}")
        
#     file_size = os.path.getsize(file_path)
#     if file_size > MAX_FILE_SIZE:
#         raise FileHandlingError(f"File exceeds maximum size of {MAX_FILE_SIZE/1024/1024}MB")
        
#     file_ext = os.path.splitext(file_path)[1].lower()
#     if file_ext not in ALLOWED_FILE_TYPES:
#         raise FileHandlingError(f"File type {file_ext} not allowed")

# def load_file_metadata():
#     """Load stored file metadata"""
#     if os.path.exists(FILE_METADATA_PATH):
#         try:
#             with open(FILE_METADATA_PATH, 'r') as f:
#                 return json.load(f)
#         except json.JSONDecodeError:
#             return {}
#     return {}

# def save_file_metadata(metadata):
#     """Save file metadata to storage"""
#     os.makedirs(os.path.dirname(FILE_METADATA_PATH), exist_ok=True)
#     with open(FILE_METADATA_PATH, 'w') as f:
#         json.dump(metadata, f, indent=2)

# def cleanup_temp_files():
#     """Clean up temporary upload files"""
#     if os.path.exists(TEMP_UPLOAD_DIR):
#         for filename in os.listdir(TEMP_UPLOAD_DIR):
#             file_path = os.path.join(TEMP_UPLOAD_DIR, filename)
#             try:
#                 if os.path.isfile(file_path):
#                     os.remove(file_path)
#             except Exception as e:
#                 logging.error(f"Error cleaning up file {file_path}: {str(e)}")

# def upload_file_to_assistant(client, file_path):
#     """Upload a file to the Assistant API with validation"""
#     try:
#         validate_file(file_path)
#         with open(file_path, 'rb') as file:
#             response = client.files.create(file=file, purpose='assistants')
#             return response.id
#     except Exception as e:
#         raise FileHandlingError(f"Error uploading file: {str(e)}")

# # Get all of the available resources
# def get_resource_file_ids(client):
#     """Get or create file IDs for resources with persistence"""
#     file_ids = []
#     metadata = load_file_metadata()
#     resources_folder = 'resources'
    
#     if not os.path.exists(resources_folder):
#         return file_ids

#     # Create temp directory if needed
#     os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
    
#     try:
#         for filename in os.listdir(resources_folder):
#             file_path = os.path.join(resources_folder, filename)
#             if not os.path.isfile(file_path):
#                 continue
                
#             file_hash = generate_hashsum(file_path)
            
#             # Check if file already has an ID and hasn't changed
#             if filename in metadata and metadata[filename]['hash'] == file_hash:
#                 file_ids.append(metadata[filename]['file_id'])
#                 continue
                
#             # Upload new or modified file
#             file_id = upload_file_to_assistant(client, file_path)
#             file_ids.append(file_id)
            
#             # Update metadata
#             metadata[filename] = {
#                 'file_id': file_id,
#                 'hash': file_hash,
#                 'uploaded_at': datetime.now().isoformat()
#             }
            
#         save_file_metadata(metadata)
#         cleanup_temp_files()
#         return file_ids
        
#     except Exception as e:
#         logging.error(f"Error in get_resource_file_ids: {str(e)}")
#         cleanup_temp_files()
#         return []


# # Function to load tools from a file
# def load_tools_from_directory(directory):
#   tool_data = {"tool_configs": [], "function_map": {}}

#   for filename in os.listdir(directory):
#     if filename.endswith('.py'):
#       module_name = filename[:-3]
#       module_path = os.path.join(directory, filename)
#       spec = importlib.util.spec_from_file_location(module_name, module_path)
#       module = importlib.util.module_from_spec(spec)
#       spec.loader.exec_module(module)

#       # Load tool configuration
#       if hasattr(module, 'tool_config'):
#         tool_data["tool_configs"].append(module.tool_config)

#       # Map functions
#       for attr in dir(module):
#         attribute = getattr(module, attr)
#         if callable(attribute) and not attr.startswith("__"):
#           tool_data["function_map"][attr] = attribute

#   return tool_data


# # Function to dynamically import modules from a folder
# def import_integrations():
#   directory = 'integrations'
#   modules = {}
#   for filename in os.listdir(directory):
#     if filename.endswith('.py') and not filename.startswith('__'):
#       module_name = filename[:-3]
#       module_path = os.path.join(directory, filename)
#       spec = importlib.util.spec_from_file_location(module_name, module_path)
#       module = importlib.util.module_from_spec(spec)
#       spec.loader.exec_module(module)

#       # Setup routes for each integration
#       if hasattr(module, 'setup_routes'):
#         modules[module_name] = module
#       logging.info(f"Imported integrations: {list(modules.keys())}")
#   return modules


# # Creates a hashsum based on a given folder
# def generate_hashsum(path, hash_func=hashlib.sha256):
#   """
#   Generates a hashsum for a file or all the files in a directory.
  
#   :param path: Path to the file or folder.
#   :param hash_func: Hash function to use, default is sha256.
#   :return: Hexadecimal hashsum.
#   """
#   if not os.path.exists(path):
#     raise ValueError("Path does not exist.")

#   hashsum = hash_func()

#   if os.path.isfile(path):
#     # If it's a file, read and hash the file content
#     with open(path, 'rb') as f:
#       while chunk := f.read(8192):
#         hashsum.update(chunk)
#   elif os.path.isdir(path):
#     # If it's a folder, iterate through all files and update hash
#     for subdir, dirs, files in os.walk(path):
#       for file in sorted(files):
#         filepath = os.path.join(subdir, file)

#         # Read file in binary mode and update hash
#         with open(filepath, 'rb') as f:
#           while chunk := f.read(8192):
#             hashsum.update(chunk)
#   else:
#     raise ValueError("Path is not a file or directory.")

#   return hashsum.hexdigest()


# # Compares two given checksums
# def compare_checksums(checksum1, checksum2):
#   """
#     Compares two checksums.

#     :param checksum1: First checksum to compare.
#     :param checksum2: Second checksum to compare.
#     :return: Boolean indicating if checksums are identical.
#     """
#   return checksum1 == checksum2

import json
import hashlib
from datetime import datetime
import importlib.util
from flask import request, abort, current_app
import time
import logging
import openai
import os
from packaging import version

CUSTOM_API_KEY = os.environ.get('CUSTOM_API_KEY')

# Initialize a mapping table in Supabase
def initialize_mapping_db():
    try:
        supabase = current_app.config['supabase']
        # Create table if it doesn't exist (Supabase handles this automatically)
        logging.info("Supabase chat_mappings table is ready")
    except Exception as e:
        logging.error(f"Failed to initialize Supabase table: {str(e)}")
        raise

# Get chat mapping from Supabase
def get_chat_mapping(integration, chat_id=None, assistant_id=None):
    try:
        supabase = current_app.config['supabase']
        query = supabase.table('chat_mappings').select('*').eq('integration', integration)

        if chat_id:
            query = query.eq('chat_id', chat_id)
        elif assistant_id:
            query = query.eq('assistant_id', assistant_id)

        response = query.execute()
        return response.data
    except Exception as e:
        logging.error(f"Failed to get chat mapping: {str(e)}")
        return []

# Gets a specific value from the db result
def get_value_from_mapping(data, key):
    if data and isinstance(data, list) and len(data) > 0:
        return data[0].get(key)
    return None

# Adds or updates a chat mapping in Supabase
def update_chat_mapping(integration, chat_id, assistant_id, thread_id):
    try:
        supabase = current_app.config['supabase']
        date_of_creation = datetime.now().isoformat()

        data = {
            'integration': integration,
            'chat_id': chat_id,
            'assistant_id': assistant_id,
            'thread_id': thread_id,
            'date_of_creation': date_of_creation
        }

        response = supabase.table('chat_mappings').upsert(data).execute()
        return response.data
    except Exception as e:
        logging.error(f"Failed to update chat mapping: {str(e)}")
        raise

def delete_chat_mapping(integration, chat_id):
    try:
        supabase = current_app.config['supabase']
        response = supabase.table('chat_mappings')\
            .delete()\
            .eq('integration', integration)\
            .eq('chat_id', chat_id)\
            .execute()
        return response.data
    except Exception as e:
        logging.error(f"Failed to delete chat mapping: {str(e)}")
        raise

# Function to check API key
def check_api_key():
  api_key = request.headers.get('X-API-KEY')
  if api_key != CUSTOM_API_KEY:
    abort(401)  # Unauthorized access


# Check the current OpenAI version
def check_openai_version():
  required_version = version.parse("1.1.1")
  current_version = version.parse(openai.__version__)
  if current_version < required_version:
    raise ValueError(
        f"Error: OpenAI version {openai.__version__} is less than the required version 1.1.1"
    )
  else:
    logging.info("OpenAI version is compatible.")


# Process the actions that are initiated by the assistants API
def process_tool_calls(client, thread_id, run_id, tool_data):
  while True:
    run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                   run_id=run_id)
    if run_status.status == 'completed':
      break
    elif run_status.status == 'requires_action':
      for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name

        try:
          arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
          logging.error(
              f"JSON decoding failed: {e.msg}. Input: {tool_call.function.arguments}"
          )
          arguments = {}  # Set to default value

        # Use the function map from tool_data
        if function_name in tool_data["function_map"]:
          function_to_call = tool_data["function_map"][function_name]
          output = function_to_call(arguments)
          client.beta.threads.runs.submit_tool_outputs(thread_id=thread_id,
                                                       run_id=run_id,
                                                       tool_outputs=[{
                                                           "tool_call_id":
                                                           tool_call.id,
                                                           "output":
                                                           json.dumps(output)
                                                       }])
        else:
          logging.warning(f"Function {function_name} not found in tool data.")
      time.sleep(2)


# Constants for file handling
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_FILE_TYPES = {'.txt', '.pdf', '.doc', '.docx', '.json', '.csv'}
TEMP_UPLOAD_DIR = '.temp_uploads'
FILE_METADATA_PATH = '.storage/file_metadata.json'

class FileHandlingError(Exception):
    """Custom exception for file handling errors"""
    pass

def validate_file(file_path):
    """Validate file size and type"""
    if not os.path.exists(file_path):
        raise FileHandlingError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise FileHandlingError(f"File exceeds maximum size of {MAX_FILE_SIZE/1024/1024}MB")

    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in ALLOWED_FILE_TYPES:
        raise FileHandlingError(f"File type {file_ext} not allowed")

def load_file_metadata():
    """Load stored file metadata"""
    if os.path.exists(FILE_METADATA_PATH):
        try:
            with open(FILE_METADATA_PATH, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_file_metadata(metadata):
    """Save file metadata to storage"""
    os.makedirs(os.path.dirname(FILE_METADATA_PATH), exist_ok=True)
    with open(FILE_METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)

def cleanup_temp_files():
    """Clean up temporary upload files"""
    if os.path.exists(TEMP_UPLOAD_DIR):
        for filename in os.listdir(TEMP_UPLOAD_DIR):
            file_path = os.path.join(TEMP_UPLOAD_DIR, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                logging.error(f"Error cleaning up file {file_path}: {str(e)}")

def upload_file_to_assistant(client, file_path):
    """Upload a file to the Assistant API with validation"""
    try:
        validate_file(file_path)
        with open(file_path, 'rb') as file:
            response = client.files.create(file=file, purpose='assistants')
            return response.id
    except Exception as e:
        raise FileHandlingError(f"Error uploading file: {str(e)}")

# Get all of the available resources
def get_resource_file_ids(client):
    """Get or create file IDs for resources with persistence"""
    file_ids = []
    metadata = load_file_metadata()
    resources_folder = 'resources'

    if not os.path.exists(resources_folder):
        return file_ids

    # Create temp directory if needed
    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

    try:
        for filename in os.listdir(resources_folder):
            file_path = os.path.join(resources_folder, filename)
            if not os.path.isfile(file_path):
                continue

            file_hash = generate_hashsum(file_path)

            # Check if file already has an ID and hasn't changed
            if filename in metadata and metadata[filename]['hash'] == file_hash:
                file_ids.append(metadata[filename]['file_id'])
                continue

            # Upload new or modified file
            file_id = upload_file_to_assistant(client, file_path)
            file_ids.append(file_id)

            # Update metadata
            metadata[filename] = {
                'file_id': file_id,
                'hash': file_hash,
                'uploaded_at': datetime.now().isoformat()
            }

        save_file_metadata(metadata)
        cleanup_temp_files()
        return file_ids

    except Exception as e:
        logging.error(f"Error in get_resource_file_ids: {str(e)}")
        cleanup_temp_files()
        return []


# Function to load tools from a file
def load_tools_from_directory(directory):
  tool_data = {"tool_configs": [], "function_map": {}}

  for filename in os.listdir(directory):
    if filename.endswith('.py'):
      module_name = filename[:-3]
      module_path = os.path.join(directory, filename)
      spec = importlib.util.spec_from_file_location(module_name, module_path)
      module = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(module)

      # Load tool configuration
      if hasattr(module, 'tool_config'):
        tool_data["tool_configs"].append(module.tool_config)

      # Map functions
      for attr in dir(module):
        attribute = getattr(module, attr)
        if callable(attribute) and not attr.startswith("__"):
          tool_data["function_map"][attr] = attribute

  return tool_data


# Function to dynamically import modules from a folder
def import_integrations():
  directory = 'integrations'
  modules = {}
  for filename in os.listdir(directory):
    if filename.endswith('.py') and not filename.startswith('__'):
      module_name = filename[:-3]
      module_path = os.path.join(directory, filename)
      spec = importlib.util.spec_from_file_location(module_name, module_path)
      module = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(module)

      # Setup routes for each integration
      if hasattr(module, 'setup_routes'):
        modules[module_name] = module
      logging.info(f"Imported integrations: {list(modules.keys())}")
  return modules


# Creates a hashsum based on a given folder
def generate_hashsum(path, hash_func=hashlib.sha256):
  """
  Generates a hashsum for a file or all the files in a directory.

  :param path: Path to the file or folder.
  :param hash_func: Hash function to use, default is sha256.
  :return: Hexadecimal hashsum.
  """
  if not os.path.exists(path):
    raise ValueError("Path does not exist.")

  hashsum = hash_func()

  if os.path.isfile(path):
    # If it's a file, read and hash the file content
    with open(path, 'rb') as f:
      while chunk := f.read(8192):
        hashsum.update(chunk)
  elif os.path.isdir(path):
    # If it's a folder, iterate through all files and update hash
    for subdir, dirs, files in os.walk(path):
      for file in sorted(files):
        filepath = os.path.join(subdir, file)

        # Read file in binary mode and update hash
        with open(filepath, 'rb') as f:
          while chunk := f.read(8192):
            hashsum.update(chunk)
  else:
    raise ValueError("Path is not a file or directory.")

  return hashsum.hexdigest()


# Compares two given checksums
def compare_checksums(checksum1, checksum2):
  """
    Compares two checksums.

    :param checksum1: First checksum to compare.
    :param checksum2: Second checksum to compare.
    :return: Boolean indicating if checksums are identical.
    """
  return checksum1 == checksum2
