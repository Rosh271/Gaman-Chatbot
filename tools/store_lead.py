import os
import requests

AIRTABLE_API_KEY = os.environ['AIRTABLE_API_KEY']
AIRTABLE_BASE_ID = os.environ['AIRTABLE_BASE_ID']

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

# The callback function (Adds lead to Airtable)
def store_lead(arguments):
    """
    Collects and stores leads in Airtable.

    :param arguments: dict, Contains the information for storing a lead.
                      Expected keys: Name, Phone, Email, City.
    :return: dict or str, Response from the API or error message.
    """
    # Extracting information from arguments
    name = arguments.get('Name')
    phone = arguments.get('Phone')
    email = arguments.get('Email')
    city = arguments.get('City')

    # Validating the presence of all required information
    if not all([name, phone, email, city]):
        return "Missing required information. Please provide Name, Phone, Email, and City."

    # Airtable API URL and headers
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Leads"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }

    # Data payload for the API request
    data = {
        "records": [{
            "fields": {
                "Name": name,
                "Phone": phone,
                "Email": email,
                "City": city
            }
        }]
    }

    # Making the API request with error handling
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # This will raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Failed to store lead: {str(e)}"

