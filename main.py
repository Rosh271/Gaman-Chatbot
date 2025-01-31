# import os
# import logging
# from flask import Flask, render_template
# from openai import OpenAI  # Import using the new client method
# import core_functions
# import assistant

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )

# # Check OpenAI version
# core_functions.check_openai_version()

# # Initialize Flask
# app = Flask(__name__)

# # Initialize OpenAI client (correct method)
# OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
# if not OPENAI_API_KEY:
#     raise ValueError("No OpenAI API key found in environment variables")

# client = OpenAI(
#     api_key=OPENAI_API_KEY,
#     default_headers={"OpenAI-Beta": "assistants=v2"}  # Key fix point
# )

# # Load tools and create assistant
# tool_data = core_functions.load_tools_from_directory('tools')
# assistant_id = assistant.create_assistant(client, tool_data)

# if not assistant_id:
#   raise ValueError(f"No assistant found by id: {assistant_id}")

# # Other code remains unchanged...

# # Import integrations
# available_integrations = core_functions.import_integrations()

# requires_db = False

# # Dynamically set up routes for active integrations
# for integration_name in available_integrations:
#   integration_module = available_integrations[integration_name]
#   integration_module.setup_routes(app, client, tool_data, assistant_id)

#   # Checks whether or not a DB mapping is required
#   if integration_module.requires_mapping():
#     requires_db = True

# # Maybe initialize the SQLite DB structure
# if requires_db:
#   core_functions.initialize_mapping_db()

# # Display a simple web page for simplicity
# @app.route('/')
# def home():
#   return render_template('index.html')

# # Start the app
# if __name__ == '__main__':
#   app.run(host='0.0.0.0', port=8080)



# import os
# import logging
# from flask import Flask, render_template
# from openai import OpenAI  # Import using the new client method
# from supabase import create_client, Client
# import core_functions
# import assistant

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )

# # Check OpenAI version
# core_functions.check_openai_version()

# # Initialize Supabase client
# SUPABASE_URL = os.environ.get('SUPABASE_URL')
# SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

# if not SUPABASE_URL or not SUPABASE_KEY:
#     raise ValueError("No Supabase credentials found in environment variables")

# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# # Initialize Flask
# app = Flask(__name__)
# app.config['supabase'] = supabase

# # Initialize OpenAI client (correct method)
# OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
# if not OPENAI_API_KEY:
#     raise ValueError("No OpenAI API key found in environment variables")

# client = OpenAI(
#     api_key=OPENAI_API_KEY,
#     default_headers={"OpenAI-Beta": "assistants=v2"}  # Key fix point
# )

# # Load tools and create assistant
# tool_data = core_functions.load_tools_from_directory('tools')
# assistant_id = assistant.create_assistant(client, tool_data)

# if not assistant_id:
#   raise ValueError(f"No assistant found by id: {assistant_id}")

# # Other code remains unchanged...

# # Import integrations
# available_integrations = core_functions.import_integrations()

# requires_db = False

# # Dynamically set up routes for active integrations
# for integration_name in available_integrations:
#   integration_module = available_integrations[integration_name]
#   integration_module.setup_routes(app, client, tool_data, assistant_id)

#   # Checks whether or not a DB mapping is required
#   if integration_module.requires_mapping():
#     requires_db = True

# # Maybe initialize the SQLite DB structure
# if requires_db:AI
#   core_functions.initialize_mapping_db()

# # Display a simple web page for simplicity
# @app.route('/')
# def home():
#   return render_template('index.html')

# # Start the app
# if __name__ == '__main__':
#   app.run(host='0.0.0.0', port=8080)

import os
import logging
from flask import Flask, render_template
from openai import OpenAI  # Import using the new client method
from supabase import create_client, Client
import core_functions
import assistant

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Check OpenAI version
core_functions.check_openai_version()

# Initialize Supabase client
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("No Supabase credentials found in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize Flask
app = Flask(__name__)
app.config['supabase'] = supabase

# Initialize OpenAI client (correct method)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("No OpenAI API key found in environment variables")

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.openai.com/v1",
    default_headers={"OpenAI-Beta": "assistants=v2"}
)

# Load tools and create assistant
tool_data = core_functions.load_tools_from_directory('tools')
assistant_id = assistant.create_assistant(client, tool_data)

if not assistant_id:
  raise ValueError(f"No assistant found by id: {assistant_id}")

# Other code remains unchanged...

# Import integrations
available_integrations = core_functions.import_integrations()

requires_db = False

# Dynamically set up routes for active integrations
for integration_name in available_integrations:
  integration_module = available_integrations[integration_name]
  integration_module.setup_routes(app, client, tool_data, assistant_id)

  # Checks whether or not a DB mapping is required
  if integration_module.requires_mapping():
    requires_db = True

# Maybe initialize the SQLite DB structure
if requires_db:
  core_functions.initialize_mapping_db()

# Display a simple web page for simplicity
@app.route('/')
def home():
  return render_template('index.html')

# Test route for Supabase connection
@app.route('/test-supabase')
def test_supabase():
    try:
        # Test the connection
        response = supabase.table('chat_mappings').select("*").limit(1).execute()
        return {
            "status": "success",
            "message": "Supabase connection successful",
            "data": response.data,
            "url": SUPABASE_URL
        }
    except Exception as e:
        logging.error(f"Supabase test failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "type": type(e).__name__
        }, 500

# Start the app
if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080)