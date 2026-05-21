import sys

import anthropic

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
vault_client = SecretClient(vault_url="https://claude-demo-vault.vault.azure.net/", credential=credential)

try:
    api_key = vault_client.get_secret("ANTHROPIC-API-KEY").value

    if not api_key or "..." in api_key:
            print(f"Error: Retrieved API key is empty or still a placeholder string!")
            sys.exit(1)

    print(f"api key: {api_key}")
except Exception as e:
     print(f"failed to fetch secret key {e}")
     sys.exit(1)
     
client = anthropic.Anthropic(api_key=api_key)

MODELS = [
    "claude-sonnet-4-6",
    "claude-opus-4-7",
    "claude-haiku-4-5-20251001",
]

PROMPT = "hello world!"
for model in MODELS:
    response = client.messages.create(
    model =  model,
    max_tokens=256,
    messages = [{
        "role":"user","content":PROMPT
    }]
    )

    print(f"\n-- {model} ---")
    print(f"Response: {response.content[0].text}")
    print(f"token IN/OUT: {response.usage.input_tokens}/{response.usage.output_tokens}")
    print(f"stop reason {response.stop_reason}")