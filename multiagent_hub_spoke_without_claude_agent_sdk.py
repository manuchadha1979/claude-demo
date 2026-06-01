import os
import sys
from anthropic import Anthropic
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from anthropic_chat import get_anthropic_client, MODELS

# =====================================================================
# 1. AUTOMATED TOOL LOOP HANDLER (The Engine)
# =====================================================================

def execute_agent_with_tools(system_prompt: str, initial_user_message: str, tools_schema: list, agent_name: str) -> str:
    """
    An elastic execution loop. It intercepts ALL tool requests made by Claude 
    (including parallel tool calls), executes them, and feeds them back properly.
    """
    client = get_anthropic_client() # Grabs key automatically from os.environ
    
    
    # Initialize conversation tracking
    messages = [{"role": "user", "content": initial_user_message}]
    
    while True:
        # Request a response from the API
        response = client.messages.create(
            model= MODELS[0],
            max_tokens=1500,
            system=system_prompt,
            messages=messages,
            tools=tools_schema if tools_schema else None
        )
        
        # Scenario A: Claude is done running tools and provides its text conclusion
        if response.stop_reason != "tool_use":
            return response.content[0].text
            
        # Scenario B: Claude wants to use tools. We MUST track its intent in history first.
        messages.append({"role": "assistant", "content": response.content})
        
        # Gather ALL tool results required for this turn to avoid the 400 error
        tool_results_list = []
        
        for block in response.content:
            if block.type == "tool_use":
                print(f"  [{agent_name}] Executing Tool: {block.name}({block.input})")
                
                # Mock Tool Execution Logic
                if block.name == "web_search":
                    result_content = f"Mocked Web Search Result for '{block.input.get('query')}': AI Infrastructure infrastructure valuation hits $180B in 2026 with a 28% CAGR."
                elif block.name == "grep_code":
                    result_content = f"Mocked Grep Result for '{block.input.get('keyword')}': Found dependency matching CUDA 12.1 in configuration profiles."
                else:
                    result_content = "Tool executed with empty string confirmation."
                
                # Package it matching Anthropic's schema rules
                tool_results_list.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_content
                })
        
        # Append the complete batch of results right back to history as a user role
        messages.append({
            "role": "user",
            "content": tool_results_list
        })

# =====================================================================
# 2. THE SPOKES (Subagent System Envelopes)
# =====================================================================

def run_market_researcher(subtask_context: str) -> str:
    system_prompt = "You are a professional Market Researcher. Use your web_search tool to find accurate metrics."
    tools = [{
        "name": "web_search",
        "description": "Searches the web for market financial statistics and data.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    }]
    return execute_agent_with_tools(system_prompt, subtask_context, tools, "Market Researcher")


def run_tech_analyst(subtask_context: str) -> str:
    system_prompt = "You are a technical analyst code reviewer. Scan patterns using grep_code."
    tools = [{
        "name": "grep_code",
        "description": "Searches code bases for architectural strings or hardware markers.",
        "input_schema": {
            "type": "object",
            "properties": {"keyword": {"type": "string"}},
            "required": ["keyword"]
        }
    }]
    return execute_agent_with_tools(system_prompt, subtask_context, tools, "Tech Analyst")

# =====================================================================
# 3. THE HUB (Orchestration Routing Layer)
# =====================================================================

def run_coordinator_hub(user_prompt: str):
    print("\n[Hub -> Coordinator] Analyzing master requirements...")
    client = get_anthropic_client()
    
    # Define subagents to the Hub as functional tool descriptions
    hub_tools = [
        {
            "name": "delegate_to_market_researcher",
            "description": "Routes macro financial and infrastructure growth queries to the Market Researcher Spoke.",
            "input_schema": {
                "type": "object",
                "properties": {"subtask_prompt": {"type": "string"}},
                "required": ["subtask_prompt"]
            }
        },
        {
            "name": "delegate_to_tech_analyst",
            "description": "Routes hardware configurations, file structures, and code architecture issues to the Tech Analyst Spoke.",
            "input_schema": {
                "type": "object",
                "properties": {"subtask_prompt": {"type": "string"}},
                "required": ["subtask_prompt"]
            }
        }
    ]
    
    coordinator_messages = [{"role": "user", "content": user_prompt}]
    
    while True:
        response = client.messages.create(
            model=MODELS[0],
            max_tokens=2500,
            system="You are the Hub Coordinator. Delegate work efficiently to specialists. Synthesize final summaries.",
            messages=coordinator_messages,
            tools=hub_tools
        )
        
        if response.stop_reason != "tool_use":
            print("\n================ FINAL HUB REPORT ================")
            print(response.content[0].text)
            break
            
        # Log coordinator step
        coordinator_messages.append({"role": "assistant", "content": response.content})
        
        tool_results_batch = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\n[Hub Control] Delegating task via tool: {block.name}")
                
                # Context Delegation Hand-off
                if block.name == "delegate_to_market_researcher":
                    subagent_output = run_market_researcher(block.input["subtask_prompt"])
                elif block.name == "delegate_to_tech_analyst":
                    subagent_output = run_tech_analyst(block.input["subtask_prompt"])
                else:
                    subagent_output = "Unknown delegation branch."
                
                tool_results_batch.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": subagent_output
                })
                
        coordinator_messages.append({
            "role": "user",
            "content": tool_results_batch
        })

# =====================================================================
# KEY VAULT LOADER & ENTRY
# =====================================================================
def get_anthropic_key():
    print("[Azure] Accessing Key Vault secret entries...")
    credential = DefaultAzureCredential()
    vault_client = SecretClient(
        vault_url="https://claude-demo-vault.vault.azure.net/", credential=credential
    )
    return vault_client.get_secret("ANTHROPIC-API-KEY").value

if __name__ == "__main__":
#    secret_key = get_anthropic_key()
    
#    try:
#        os.environ["ANTHROPIC_API_KEY"] = secret_key
        
    master_prompt = """
    Evaluate our current AI architecture setup. 
    1. Ask the market researcher for overall infrastructure valuation trends.
    2. Ask the tech analyst for structural configuration dependencies.
    Then, pull it together.
    """
    run_coordinator_hub(master_prompt)
        
#    finally:
#        if "ANTHROPIC_API_KEY" in os.environ:
#            del os.environ["ANTHROPIC_API_KEY"]
#            print("\n[Security] ANTHROPIC_API_KEY safely cleared from environment memory.")