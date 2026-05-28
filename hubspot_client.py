from hubspot import HubSpot
from hubspot.crm.contacts import PublicObjectSearchRequest
from hubspot.crm.contacts.exceptions import ApiException
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

# 1. Configure your Azure Key Vault Details
# Replace with your actual Key Vault URL (e.g., https://my-vault.vault.azure.net/)
KEY_VAULT_URL = "https://claude-demo-vault.vault.azure.net/"
SECRET_NAME = "HUBSPOT-API-KEY"  # The name you gave the secret in Azure


def get_hubspot_client():
    try:
        # DefaultAzureCredential automatically looks for Azure CLI credentials, 
        # environment variables, or Managed Identities to authenticate.
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
        
        # Fetch the token securely at runtime
        retrieved_secret = secret_client.get_secret(SECRET_NAME)
        HUBSPOT_TOKEN = retrieved_secret.value
        
        # --- DIAGNOSTIC LOGS ---
        print("--- HUBSPOT TOKEN DIAGNOSTIC ---")
        print(f"Total Character Length: {len(HUBSPOT_TOKEN)}")
        print(f"Starts with: {repr(HUBSPOT_TOKEN[:10])}")
        print(f"Ends with: {repr(HUBSPOT_TOKEN[-10:])}")
        print("--------------------------------")

        # Let's clean the token string automatically just in case
        cleaned_token = HUBSPOT_TOKEN.strip().strip('"').strip("'")
        
        return HubSpot(access_token=cleaned_token)

    except Exception as e:
        print(f"Failed to retrieve secret from Azure Key Vault: {e}")
        raise SystemExit(e)

def lookup_crm_contact(emailid: str) -> dict:
    """
    Finds a customer in HubSpot by email using the official SDK.
    Aligned with Claude's tool schema input argument: 'emailid'.
    """
    # Build the search request payload
    client = get_hubspot_client()
    print(f"looking for {emailid}")
    print(f"got client {client}")
    search_request = PublicObjectSearchRequest(
        filter_groups=[
            {
                "filters": [
                    {
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": emailid
                    }
                ]
            }
        ],
        # Optional: Specify which properties you want Claude to receive
        properties=["firstname", "lastname", "email", "phone", "hs_object_id"]
    )

    try:
        # Perform the search using the SDK's search_api
        search_results = client.crm.contacts.search_api.do_search(
            public_object_search_request=search_request
        )
        
        # Check if any contact was found
        if search_results.results:
            contact = search_results.results[0]
            # Convert the SDK object to a standard dictionary for Claude's execution handler
            return {
                "id": contact.id,
                **contact.properties
            }
        else:
            print(f"client {emailid} not found.")
            return {}
        
    except ApiException as e:
        print(f"Exception when calling search_api->do_search: {e}")
        return {"error": str(e)}

#get_hubspot_client()
#lookup_crm_contact("bh@hubspot.com")