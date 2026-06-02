import json
import requests
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

# 1. Configure your Azure Key Vault Details
KEY_VAULT_URL = "https://claude-demo-vault.vault.azure.net/"
SECRET_NAME = "SQUARE-SANDBOX-TOKEN"  # Make sure this matches your secret name in Azure

# 2. Square Base Endpoint Configuration
BASE_URL = "https://connect.squareupsandbox.com/v2"
MASTER_DISCOUNT_CATALOG_ID = "HHU3B63IT44H5RK5CBT77IIR"


def get_square_headers() -> dict:
    """
    Securely fetches the Square Access Token from Azure Key Vault 
    at runtime and returns the standardized header structure.
    """
    try:
        # DefaultAzureCredential handles authentication
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
        
        # Fetch the token securely
        retrieved_secret = secret_client.get_secret(SECRET_NAME)
        raw_token = retrieved_secret.value
        
        # Clean the token string automatically to remove any stray quotes or line breaks
        cleaned_token = raw_token.strip().strip('"').strip("'")
        
        return {
            "Authorization": f"Bearer {cleaned_token}",
            "Content-Type": "application/json",
            "Square-Version": "2024-03-20"
        }
    except Exception as e:
        print(f"❌ Failed to retrieve secret from Azure Key Vault: {e}")
        raise SystemExit(e)


def get_discount_code(order_id: str) -> str:
    """
    Validates infrastructure with Square using credentials from Azure Key Vault
    and returns a unique customer-facing coupon code.
    Designed to be cleanly called inside a Claude tool execution loop.
    """
    # Dynamically fetch authenticated headers
    headers = get_square_headers()
    url = f"{BASE_URL}/catalog/object/{MASTER_DISCOUNT_CATALOG_ID}"
    
    try:
        print(f"Verifying master rule with Square for order: {order_id}...")
        response = requests.get(url, headers=headers)
        
        # Check if the blueprint rule is alive and well in Square's system
        if response.status_code == 200:
            catalog_data = response.json().get("object", {})
            discount_name = catalog_data.get("discount_data", {}).get("name", "Delayed Order Compensation")
            
            # Generate the unique dynamic coupon string the customer will check out with
            generated_coupon = f"SQ-COMP-{order_id}"
            
            # Return a clean JSON data dump for the Claude Agent to parse
            return json.dumps({
                "status": "success",
                "discount_code": generated_coupon,
                "value": "£4.00",
                "currency": "GBP",
                "rule_verified_by_square": True,
                "message": f"Successfully mapped transaction reference to master rule: '{discount_name}'"
            })
            
        else:
            return json.dumps({
                "status": "error",
                "error_code": "SQUARE_API_FAILURE",
                "details": f"Square returned code {response.status_code}: {response.text}"
            })
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_code": "CONNECTION_EXCEPTION",
            "details": str(e)
        })


# --- Local Verification Test Block ---
#if __name__ == "__main__":
#    # Test call mimicking Claude invoking the tool for an order
#    tool_output = get_discount_code(order_id="1002")
#    print(tool_output)