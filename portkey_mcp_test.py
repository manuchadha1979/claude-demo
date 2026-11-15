import asyncio
import httpx
from portkey_ai import Portkey
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# =========================================================
# CONFIGURATION BLOCK
# =========================================================
ALLOWED_WORKSPACE_KEY = "muzp3pggs9GFMaw6XTmF6bGhqcKK"
BLOCKED_WORKSPACE_KEY = "YOUR_BLOCKED_WORKSPACE_API_KEY"

# Scenario 1: Configure Your Sanctioned vs. Unsanctioned Models
SANCTIONED_MODEL = "claude-sonnet-4-6"          # Provisioned in Model Catalog
SANCTIONED_MODEL_GUARDRAIL_BLOCK = "claude-sonnet-5"
UNSANCTIONED_MODEL = "gpt-4o"                  # Blocked/Disabled in Model Catalog

# Scenario 2: Configure Your MCP Server Slug
MCP_SERVER_SLUG = "deepwiki-test-mcp-server" 


# =========================================================
# TEST 1: MODEL GOVERNANCE (Direct Gateway Method)
# =========================================================
def test_model_governance(api_key, provider_name, model_name, scenario_title):
    print(f"\n🤖 Running Model Test: {scenario_title} using [{model_name}]")
    try:
        # FIXED: Pass the provider string so Portkey knows how to route the request headers
        client = Portkey(api_key=api_key, provider=provider_name)
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Ping"}]
        )
        print(f"✅ SUCCESS: Gateway allowed the request for model: {model_name}")
        print(f"   Response output: {response.choices[0].message.content}")
    except Exception as error:
        print(f"❌ BLOCKED BY GATEWAY: Portkey successfully rejected model: {model_name}")
        print(f"   Reason: {error}")


# =========================================================
# TEST 2: MCP SERVER GOVERNANCE (Protocol Handshake Method)
# =========================================================
async def test_mcp_governance(api_key, server_slug, scenario_title):
    print(f"\n🔌 Running MCP Test: {scenario_title} for server slug [{server_slug}]")
    
    portkey_mcp_url = f"https://mcp.portkey.ai/{server_slug}/mcp"
    headers = {"x-portkey-api-key": api_key}
    
    try:
        async with streamablehttp_client(portkey_mcp_url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_response = await session.list_tools()
                
                print(f"✅ SUCCESS: Portkey verified workspace key and allowed MCP access!")
                print(f"   Discovered Tools Count: {len(tools_response.tools)}")
    except Exception as error:
        print(f"❌ BLOCKED BY MCP GATEWAY: Portkey rejected the tool handshake.")
        print(f"   Reason: {error}")


# =========================================================
# EXECUTION LAYER
# =========================================================
if __name__ == "__main__":
    # --- Scenario 1 Tests (Model Catalog Enforcement) ---
    
    # 1A. Sanctioned Path: Allowed key + Allowed Anthropic model string
    test_model_governance(ALLOWED_WORKSPACE_KEY, "anthropic", SANCTIONED_MODEL, "Sanctioned Model Request")
    
    # 1B. Unsanctioned Path: Allowed key + Forbidden OpenAI model string
    test_model_governance(ALLOWED_WORKSPACE_KEY, "openai", UNSANCTIONED_MODEL, "Unsanctioned Model Request")

    # --- Scenario 2 Tests (MCP Registry Enforcement) ---
    print("\n--- Transitioning to Asynchronous MCP Handshake Tests ---")
    
    # 2A. Key from a workspace that IS provisioned to use the server slug
    asyncio.run(test_mcp_governance(ALLOWED_WORKSPACE_KEY, MCP_SERVER_SLUG, "Sanctioned MCP Request"))