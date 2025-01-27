import os
import logging
from flask import Flask, render_template
import openai
import core_functions
import assistant

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Check OpenAI version compatibility
core_functions.check_openai_version()

# Create Flask app
app = Flask(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger.error("No OpenAI API key found in environment variables!")
    raise ValueError("No OpenAI API key found in environment variables")

logger.info("OpenAI API key found")
openai.api_key = OPENAI_API_KEY
client = openai

# Configure OpenAI API for v2 Assistants
openai.default_headers = {"OpenAI-Beta": "assistants=v2"}

# Initialize all available tools
logger.info("Loading tools from directory...")
tool_data = core_functions.load_tools_from_directory('tools')
logger.info(f"Loaded {len(tool_data['tool_configs'])} tools")

# Create or load assistant
logger.info("Creating/loading assistant...")
assistant_id = assistant.create_assistant(client, tool_data)
logger.info(f"Assistant ID: {assistant_id}")

if not assistant_id:
    logger.error("Failed to create/load assistant!")
    raise ValueError(f"No assistant found by id: {assistant_id}")

# Import integrations
available_integrations = core_functions.import_integrations()

requires_db = False

# Dynamically set up routes for active integrations
for integration_name in available_integrations:
    integration_module = available_integrations[integration_name]
    integration_module.setup_routes(app, client, tool_data, assistant_id)

    #Checks whether or not a DB mapping is required
    if integration_module.requires_mapping():
        requires_db = True

# Maybe initialize the SQLite DB structure
if requires_db:
    core_functions.initialize_mapping_db()

#Display a simple web page for simplicity
@app.route('/')
def home():
    return render_template('index.html')

# start the app
if __name__ == '__main__':
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=8080)
