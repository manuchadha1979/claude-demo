import json
import anthropic
from anthropic_chat_test import get_anthropic_client
from pydantic import BaseModel

class ToolResult(BaseModel):
    output: str  # Or Any, if your tool returns dicts/lists sometimes


client = get_anthropic_client()

def execute_tool(name, input_data):
    # Fake implementation so the loop can complete
    if name == "lookup_customer":
        return ToolResult(output="Found customer: John Smith, ID 123, email john@example.com")
    return ToolResult(output="Tool not found")

tools = [
    {
        "name": "lookup_customer",
        "description": "Looks up a customer by name and returns their details",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The customer's full name"}
            },
            "required": ["name"]
        }
    }
]

messages = [{"role": "user", "content": "Find customer John Smith"}]

while True:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        tools=tools,
        messages=messages
    )

    print(f"response: {json.dumps(response.model_dump(), indent=2)}")

    if response.stop_reason == "end_turn":
        print("Final response:", response.content[0].text)
        break

    if response.stop_reason == "tool_use":
        tool_block = next(b for b in response.content if b.type == "tool_use")
        print(f"tool block {json.dumps(tool_block.model_dump(), indent=2)}")
        print(f"Claude wants to call: {tool_block.name} with {tool_block.input}")

        result = execute_tool(tool_block.name, tool_block.input)
        print(f"Tool returned: {json.dumps(result.model_dump(), indent=2)}")

        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{"type": "tool_result",
                         "tool_use_id": tool_block.id,
                         "content": result.output}]
        })