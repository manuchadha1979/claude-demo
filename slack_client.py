from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

# 1. Configure your Azure Key Vault Details
KEY_VAULT_URL = "https://claude-demo-vault.vault.azure.net/"
SECRET_NAME = "SLACK-BOT-TOKEN"  # The name given to your Slack Bot User OAuth Token in Azure

def get_slack_client() -> WebClient:
    """
    Initializes a Slack WebClient by securely fetching the 
    Bot OAuth Token from Azure Key Vault at runtime.
    """
    try:
        # DefaultAzureCredential automatically looks for active cloud identities or local logins
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
        
        # Fetch the token securely
        retrieved_secret = secret_client.get_secret(SECRET_NAME)
        SLACK_TOKEN = retrieved_secret.value
        
        # Clean the token string automatically to remove any stray quotes or line breaks
        cleaned_token = SLACK_TOKEN.strip().strip('"').strip("'")
        
        # Return initialized client instance
        return WebClient(token=cleaned_token)

    except Exception as e:
        print(f"Failed to retrieve secret or initialize Slack Client: {e}")
        raise SystemExit(e)


def post_message_to_channel(channel_id: str, message_text: str) -> dict:
    """
    Posts a string message to a specific Slack channel using the WebClient.
    """
    client = get_slack_client()
    print(f"Attempting to post message {message_text} to channel: {channel_id}")
    
    try:
        # Call the chat.postMessage method using the WebClient
        response = client.chat_postMessage(
            channel=channel_id,
            text=message_text
        )
        
        # The response is a SlackResponse object containing metadata about the sent message
        if response["ok"]:
            print(f"Successfully posted message to channel {channel_id} at TS: {response['ts']}")
            return response.data
            
    except SlackApiError as e:
        # Slack API-specific errors (e.g., 'invalid_auth', 'channel_not_found')
        print(f"Slack API error occurred: {e.response['error']}")
        return {"error": e.response['error']}
    except Exception as e:
        # Catch-all for generic network or code execution exceptions
        print(f"Generic exception when posting message to Slack: {e}")
        return {"error": str(e)}

# post_message_to_channel("escalations","hi")
# --- Example Execution Usage ---
# if __name__ == "__main__":
#     # Note: channel_id can be a human-readable name like "#general" 
#     # or a specific ID like "C0123456789" (IDs are highly recommended)
#     result = post_message_to_channel(channel_id="C0123456789", message_text="Hello from Python and Azure Vault!")
#     print(result)