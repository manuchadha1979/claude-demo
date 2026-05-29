import requests
from requests.auth import HTTPBasicAuth
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
import json

# --- CONFIGURATION (Shared Constants) ---
BASE_URL = "https://manusworkspacepersonal-44573730.atlassian.net"
USER_EMAIL = "manu.chadha@hotmail.com"
SECRET_NAME = "JSM-API-KEY"  
KEY_VAULT_URL = "https://claude-demo-vault.vault.azure.net/"


def extract_raw_text_from_adf(node):
    """
    Recursively extracts and flattens all text fragments from 
    Atlassian Document Format (ADF) into a single plain-text string.
    """
    if not node:
        return ""
    
    # Base case: If this specific node contains a text fragment, return it
    if "text" in node:
        return node["text"]
    
    # Recursive case: If it has children elements, extract from all of them
    text_fragments = []
    if "content" in node:
        for child_node in node["content"]:
            text_fragments.append(extract_raw_text_from_adf(child_node))
            
    # Join all inner pieces together with a space to prevent words from sticking
    return " ".join([frag for frag in text_fragments if frag.strip()])



def get_ticket(id):
    print(f"getting ticket {id}")
    # --- CONFIGURATION ---
    # 1. Your exact workspace URL base
    #BASE_URL = "https://manusworkspacepersonal-44573730.atlassian.net"

    # 2. The Ticket Key you want to fetch (e.g., "SUP-1", "SUP-2")
    TICKET_KEY = id 

    # 3. Your Atlassian Account Credentials
    #USER_EMAIL = "manu.chadha@hotmail.com"
    # Generate a token here: https://id.atlassian.com/manage-profile/security/api-tokens
    #SECRET_NAME = "JSM-API-KEY"  # The name you gave the secret in Azure
    #KEY_VAULT_URL = "https://claude-demo-vault.vault.azure.net/"

    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
    
    # Fetch the token securely at runtime
    retrieved_secret = secret_client.get_secret(SECRET_NAME)
    JSM_TOKEN = retrieved_secret.value
    
    # --- DIAGNOSTIC LOGS ---
    print("--- JSM TOKEN DIAGNOSTIC ---")
    print(f"Total Character Length: {len(JSM_TOKEN)}")
    print(f"Starts with: {repr(JSM_TOKEN[:10])}")
    print(f"Ends with: {repr(JSM_TOKEN[-10:])}")
    print("-------------------------------")
     
    # --- EXECUTION ---
    # Construct the endpoint URL for a specific issue
    url = f"{BASE_URL}/rest/api/3/issue/{TICKET_KEY}"

    headers = {
        "Accept": "application/json"
    }

    auth = HTTPBasicAuth(USER_EMAIL, JSM_TOKEN)

    print(f"Connecting to Jira Service Management to fetch {TICKET_KEY}...")

    # Make the GET request
    response = requests.request(
        "GET",
        url,
        headers=headers,
        auth=auth
    )

    # Check if the connection was successful
    if response.status_code == 200:
        ticket_data = response.json()
        print("Successfully retrieved ticket data!\n" + "="*40)
        
        # Extract data from the JSON response safely
        fields = ticket_data.get("fields", {})
        
        summary = fields.get("summary", "No Summary Provided")
        description_data = fields.get("description", {})
        status = fields.get("status", {}).get("name", "Unknown")
        reporter = fields.get("reporter", {}).get("displayName", "Anonymous")
        created_date = fields.get("created", "Unknown Date")
        
        # Print out the core details
        print(f"Ticket Key:  {ticket_data.get('key')}")
        print(f"Summary:     {summary}")
        print(f"Description:     {description_data}")
        print(f"Status:      {status}")
        print(f"Reporter:    {reporter}")
        print(f"Created On:  {created_date}")
        print("="*40)

        # Grab the description object
        description_adf = ticket_data.get("fields", {}).get("description", {})
        
        # Flatten it entirely for the LLM
        llm_ready_text = extract_raw_text_from_adf(description_adf)
        
        # Clean up any accidental double spaces caused by the flattening process
        llm_ready_text = " ".join(llm_ready_text.split())
        
        print("--- TEXT FOR LLM ---")
        print(llm_ready_text)
        result = llm_ready_text
        # Output: I didn’t receive order no 123456. Contact me on bh@hubspot.com
        
        # Optional: If you want to see the entire massive block of data Jira sends back, 
        # uncomment the line below:
        # print(json.dumps(ticket_data, indent=4))

    elif response.status_code == 404:
        print(f"Error: Ticket '{TICKET_KEY}' was not found. Double-check your ticket number.")
        result = f"Error: Ticket '{TICKET_KEY}' was not found. Double-check your ticket number."
    elif response.status_code == 401:
        print("Error: Authentication failed. Check your Email Address and API Token.")
        result = "Error: Authentication failed. Check your Email Address and API Token."
    else:
        print(f"Failed to fetch data. HTTP Status Code: {response.status_code}")
        print(response.text)
        result = f"Failed to fetch data. HTTP Status Code: {response.status_code}"
    
    return {
        "result" : result
    }

def _get_auth_headers() -> tuple:
    """Helper function to fetch Azure credentials and return headers/auth."""
    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
    retrieved_secret = secret_client.get_secret(SECRET_NAME)
    jsm_token = retrieved_secret.value.strip()
    
    auth = HTTPBasicAuth(USER_EMAIL, jsm_token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    return auth, headers


## 1. FUNCTION TO GET POSSIBLE TRANSITIONS
def get_available_transitions(ticket_id: str) -> list:
    """
    Fetches all valid, available transitions for a given Jira ticket.
    Returns a list of dictionaries containing transition names and integer IDs.
    """
    print(f"Fetching available transitions for ticket {ticket_id}...")
    auth, headers = _get_auth_headers()
    url = f"{BASE_URL}/rest/api/3/issue/{ticket_id}/transitions"
    
    response = requests.get(url, headers=headers, auth=auth)
    
    if response.status_code != 200:
        print(f"Error fetching transitions: {response.status_code} - {response.text}")
        return []
        
    transitions_data = response.json().get("transitions", [])
    
    # Format cleanly for easy extraction or logging
    return [{"id": int(t["id"]), "name": t["name"]} for t in transitions_data]


## 2. FUNCTION TO EXECUTE THE TRANSITION
def apply_ticket_transition(ticket_id: str, transition_name_or_id: str, reason: str) -> dict:
    """
    Validates the transition choice, adds a reason as an ADF comment, 
    and updates the ticket status.
    """
    # Step 1: Use our first function to check valid options
    available_steps = get_available_transitions(ticket_id)
    
    target_id = None
    matched_name = ""
    
    # Match user input to available API options
    for t in available_steps:
        if transition_name_or_id.lower() in [t["name"].lower(), str(t["id"])]:
            target_id = t["id"]  # Already an int from function 1
            matched_name = t["name"]
            break
            
    if not target_id:
        valid_options_str = ", ".join([f"'{t['name']}' (ID: {t['id']})" for t in available_steps])
        print(f"Error: Transition '{transition_name_or_id}' is invalid for current status.")
        print(f"Available options: {valid_options_str}")
        return {"result": f"Error: '{transition_name_or_id}' unavailable.", "valid_options": available_steps}

    print(f"Executing step: '{matched_name}' (ID: {target_id})")

    # Step 2: Build ADF Comment & Payload
    comment_adf = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": reason}]
            }
        ]
    }

    payload = {
        "transition": {
            "id": target_id 
        },
        "update": {
            "comment": [
                {
                    "add": {
                        "body": comment_adf
                    }
                }
            ]
        }
    }

    # Step 3: Dispatch API Request
    auth, headers = _get_auth_headers()
    url = f"{BASE_URL}/rest/api/3/issue/{ticket_id}/transitions"
    
    response = requests.post(url, data=json.dumps(payload), headers=headers, auth=auth)

    if response.status_code == 204:
        print(f"Success! Ticket {ticket_id} moved to '{matched_name}'.")
        return {"result": f"Success: Updated ticket to '{matched_name}' with comment."}
    else:
        print(f"Failed. HTTP Status: {response.status_code}. Detail: {response.text}")
        return {"result": f"Failed with status code {response.status_code}."}