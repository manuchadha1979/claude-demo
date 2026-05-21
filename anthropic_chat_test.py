import anthropic

client = anthropic.Anthropic()

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