from supabase import create_client, Client
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

# 1. Configure your Azure Key Vault Details
KEY_VAULT_URL = "https://claude-demo-vault.vault.azure.net/"
SECRET_NAME = "SUPABASE-API-KEY"  # The name given to your Supabase service role key in Azure

# 2. Configure your Supabase Project Base URL 
# (You can also move this into Azure Key Vault if you prefer)
SUPABASE_URL = "https://sonkurtihxvlbpubrhpm.supabase.co" 


def get_supabase_client() -> Client:
    """
    Initializes a Supabase client by securely fetching the 
    Service Role API token from Azure Key Vault at runtime.
    """
    try:
        # DefaultAzureCredential automatically looks for active cloud identities or local logins
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
        
        # Fetch the token securely
        retrieved_secret = secret_client.get_secret(SECRET_NAME)
        SUPABASE_TOKEN = retrieved_secret.value
        
        # --- DIAGNOSTIC LOGS ---
        print("--- SUPABASE TOKEN DIAGNOSTIC ---")
        print(f"Total Character Length: {len(SUPABASE_TOKEN)}")
        print(f"Starts with: {repr(SUPABASE_TOKEN[:10])}")
        print(f"Ends with: {repr(SUPABASE_TOKEN[-10:])}")
        print("---------------------------------")

        # Clean the token string automatically to remove any stray quotes or line breaks
        cleaned_token = SUPABASE_TOKEN.strip().strip('"').strip("'")
        
        # Return initialized client instance
        return create_client(SUPABASE_URL, cleaned_token)

    except Exception as e:
        print(f"Failed to retrieve secret or initialize Supabase Client: {e}")
        raise SystemExit(e)


def lookup_customer_orders(customer_id: str) -> list:
    """
    Queries the 'orders' table using the Supabase client filtering 
    by the custom column 'external_customer_id'.
    """
    client = get_supabase_client()
    print(f"Querying Supabase orders table for: {customer_id}")
    
    try:
        # Querying the 'orders' table matching rows where external_customer_id equals customer_id
        response = client.table("orders").select("*").eq("external_customer_id", customer_id).execute()
        
        # The .execute() method returns a response object. The data array sits inside '.data'
        orders = response.data
        
        if orders:
            print(f"Successfully retrieved {len(orders)} order(s). Order details: {orders}")
            return orders
        else:
            print(f"No orders found for customer: {customer_id}")
            return []
            
    except Exception as e:
        print(f"Exception when querying orders table from Supabase: {e}")
        return {"error": str(e)}

#lookup_customer_orders("bh@hubspot.com")
# --- Example Execution Usage ---
# if __name__ == "__main__":
#     orders_list = lookup_customer_orders("bh@hubspot.com")
#     print(orders_list)