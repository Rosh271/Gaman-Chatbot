
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

AIRTABLE_API_KEY = os.environ['AIRTABLE_API_KEY']
AIRTABLE_BASE_ID = os.environ['AIRTABLE_BASE_ID']

# Configure retry strategy
retry_strategy = Retry(
    total=3,  # number of retries
    backoff_factor=1,  # wait 1, 2, 4 seconds between retries
    status_forcelist=[429, 500, 502, 503, 504]  # HTTP status codes to retry on
)

# Create session with retry strategy
session = requests.Session()
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)

# The tool configuration
tool_config = {
    "type": "function",
    "function": {
        "name": "store_lead",
        "description": "Collects and stores leads in Airtable.",
        "parameters": {
            "type": "object",
            "properties": {
                "Name": {
                    "type": "string",
                    "description": "Name of the lead."
                },
                "Phone": {
                    "type": "string",
                    "description": "Phone number of the lead."
                },
                "Email": {
                    "type": "string",
                    "description": "Email address of the lead."
                },
                "City": {
                    "type": "string",
                    "description": "City of the lead."
                }
            },
            "required": ["Name", "Phone", "Email", "City"]
        }
    }
}

def validate_lead_data(name, phone, email, city):
    """Validate lead data before submission"""
    if not all([name, phone, email, city]):
        return False, "Missing required information. Please provide Name, Phone, Email, and City."
    if not '@' in email:
        return False, "Invalid email format"
    if len(phone) < 10:
        return False, "Phone number seems too short"
    return True, None

def store_lead(arguments):
    """
    Collects and stores leads in Airtable with retry logic and validation.

    :param arguments: dict, Contains the information for storing a lead.
                      Expected keys: Name, Phone, Email, City.
    :return: dict or str, Response from the API or error message.
    """
    try:
        # Extract and validate data
        name = arguments.get('Name', '').strip()
        phone = arguments.get('Phone', '').strip()
        email = arguments.get('Email', '').strip()
        city = arguments.get('City', '').strip()

        # Validate data
        is_valid, error_message = validate_lead_data(name, phone, email, city)
        if not is_valid:
            return error_message

        # Airtable API URL and headers
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Leads"
        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        # Data payload
        data = {
            "records": [{
                "fields": {
                    "Name": name,
                    "Phone": phone,
                    "Email": email,
                    "City": city,
                    "Created": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }]
        }

        # Make request with retry logic
        response = session.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": "Lead stored successfully",
            "data": response.json()
        }

    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to store lead: {str(e)}",
            "error_details": str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": "An unexpected error occurred",
            "error_details": str(e)
        }
