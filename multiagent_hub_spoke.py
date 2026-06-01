import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, AssistantMessage, TextBlock, ThinkingBlock, ToolUseBlock
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import sys
import os

def get_anthropic_key():
    credential = DefaultAzureCredential()
    vault_client = SecretClient(
        vault_url="https://claude-demo-vault.vault.azure.net/", credential=credential
    )
    try:
        api_key = vault_client.get_secret("ANTHROPIC-API-KEY").value
        if not api_key or "..." in api_key:
            print("Error: Retrieved API key is empty or still a placeholder string!")
            sys.exit(1)
        return api_key
    except Exception as e:
        print(f"Failed to fetch secret key: {e}")
        sys.exit(1)

async def main():
    secret_key = get_anthropic_key()
    print("[Azure] Key successfully retrieved.")
    
    # 1. Create the Spoke blueprints
    market_researcher = AgentDefinition(
        description="Researches market trends and infrastructure statistics.",
        prompt="You are an expert market researcher. Provide a short breakdown based on your knowledge base.",
        tools=[] 
    )
    
    tech_analyst = AgentDefinition(
        description="Audits software configurations and architectural code patterns.",
        prompt="You are a technical analyst. Review code configurations based on your knowledge base.",
        tools=[] 
    )

    # 2. Create the Hub Coordinator Options
    hub_options = ClaudeAgentOptions(
        system_prompt="""You are the Coordinator. Break down user requests and delegate tasks. 
        You MUST pass the subagents ONLY the context relevant to their task to avoid context pollution.""",
        allowed_tools=["Agent"], 
        agents={
            "market_researcher": market_researcher,
            "tech_analyst": tech_analyst
        }
    )

    print("--- Starting Hub-Spoke Orchestration ---")
    
    try:
        # 3. EPHEMERAL INJECTION
        os.environ["ANTHROPIC_API_KEY"] = secret_key
        
        async for message in query(
            prompt="""Evaluate the AI infrastructure market using the market researcher. 
                    Then, pass those infrastructure findings to the tech analyst to audit standard 
                    architectural software code patterns used for hosting them.""",
            options=hub_options
        ):
            # FIX: Use isinstance checks to process the official strongly-typed SDK messages
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)
                    elif isinstance(block, ThinkingBlock):
                        # Claude's internal thoughts are streaming, we can skip printing or label them
                        pass
                    elif isinstance(block, ToolUseBlock):
                        if block.name == "Agent":
                            sub_type = block.input.get("subagent_type", "Specialist")
                            print(f"\n[Hub -> Spoke Hand-off]: Spinning up {sub_type}...")
                            
            elif hasattr(message, 'result'):
                # Handle the final completion metadata object
                print(f"\n\n=== FINAL SYNTHESIZED REPORT ===\n{message.result}")
                
    except Exception as e:
        print(f"\n[Execution Error]: {e}")
                
    finally:
        # 4. MEMORY CLEANUP
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
            print("\n[Security] ANTHROPIC_API_KEY successfully purged from memory.")

if __name__ == "__main__":
    asyncio.run(main())