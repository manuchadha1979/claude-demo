import json
from pydantic import BaseModel
from anthropic_chat import get_anthropic_client
from hubspot_client import lookup_crm_contact
from jsm_client import get_ticket

class ToolResult(BaseModel):
    output: str  # Or Any, if your tool returns dicts/lists sometimes


def execute_tool(name: str, input_data: dict) -> ToolResult:
    """
    Dummy execution layer matching all defined tools.
    """
    if name == "get_ticket":
        ticket_id = input_data.get("id", "")
        if ticket_id:
            ticket_details = get_ticket(ticket_id)
            if ticket_details:
                result = ticket_details.get("result")
                output_text = f"Fetched JSM ticket {ticket_id}: 'Issue: {result}"
        else:
            output_text = "Error: ticket id parameter was missing or empty. Please provide a valid ticket id."
        return ToolResult(
                    output=output_text
            )    

    elif name == "lookup_crm_contact":
        # 1. Extract the email from Claude's input data
        email = input_data.get("emailid", "")

        if email:
            # 2. Call the function and store the resulting dictionary
            contact_data = lookup_crm_contact(email)

            # 3. Parse the result dynamically
            if contact_data:
                # Safely pull out values using .get() to avoid KeyErrors if a property is missing
                contact_id = contact_data.get("id")
                first_name = contact_data.get("firstname", "")
                last_name = contact_data.get("lastname", "")
                full_name = f"{first_name} {last_name}".strip() or "Unknown Name"
                
                output_text = f"Found HubSpot CRM contact: {full_name}, ID: {contact_id}, email: {email}"
            else:
                # Handle the fallback case where return {} was hit
                output_text = f"No HubSpot CRM contact found matching email: {email}"
        # ... inside the final else block ...
        else:
            output_text = "Error: 'emailid' parameter was missing or empty. Please provide a valid email address."

        # 4. Return the populated ToolResult model
        return ToolResult(output=output_text)

    elif name == "query_order_history":
        return ToolResult(
            output="Supabase DB Query: Found 2 past orders. Order #9081 (Shipped), Order #4321 (Delivered)"
        )

    elif name == "send_email":
        return ToolResult(
            output="SendGrid success: Resolution email sent successfully."
        )

    elif name == "post_slack_message":
        return ToolResult(
            output="Slack notification sent successfully to #escalations channel."
        )

    elif name == "close_ticket":
        return ToolResult(output="Freshdesk API success: Ticket marked as resolved.")

    return ToolResult(output=f"Tool '{name}' not found")


PROMPT = """Hey, can you look into JSM ticket SUP-1? 
Find the customer's email from that ticket so you can pull up their contact profile in HubSpot.
Once you have their details, check their full order history in our Supabase DB to see why
 they are complaining about a missing shipment. If you find the issue, go ahead and send them a
 resolution update via SendGrid. Also, please ping the #operations team on Slack
 to let them know we are escalating a shipping delay for this customer. 
 Finally, once all of that is done, go ahead and mark the Freshdesk ticket as resolved."""


tools = [
    {
        "name": "get_ticket",
        "description": "Fetch ticket from Freshdesk by ID",
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "customers ID"}},
            "required": ["id"],
        },
    },
    {
        "name": "lookup_crm_contact",
        "description": "Find customer in HubSpot by email",
        "input_schema": {
            "type": "object",
            "properties": {
                "emailid": {"type": "string", "description": "customer email ID"}
            },
        },
    },
    {
        "name": "query_order_history",
        "description": "Fetch orders from Supabase DB",
        "input_schema": {
            "type": "object",
            "properties": {"orderid": {"type": "string", "description": "Order ID"}},
        },
    },
    {
        "name": "send_email",
        "description": "Send resolution email via SendGrid",
        "input_schema": {
            "type": "object",
            "properties": {
                "emailid": {"type": "string", "description": "customer email ID"}
            },
        },
    },
    {
        "name": "post_slack_message",
        "description": "Post escalation to Slack channel",
        "input_schema": {
            "type": "object",
            "properties": {
                "channelid": {"type": "string", "description": "slack channel ID"}
            },
        },
    },
    {
        "name": "close_ticket",
        "description": "Mark Freshdesk ticket resolved",
        "input_schema": {
            "type": "object",
            "properties": {"ticketID": {"type": "string", "description": "ticket ID"}},
        },
    },
]

messages = [{"role": "user", "content": PROMPT}]


def run_agentic_workflow():
    client = get_anthropic_client()
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=4096, tools=tools, messages=messages
        )

        print(f"response: {json.dumps(response.model_dump(), indent=2)}")

        if response.stop_reason == "end_turn":
            print("Final response:", response.content[0].text)
            break

        if response.stop_reason == "tool_use":
            # Dynamic response generation setup
            tool_results_content = []

            # Iterate over all content blocks in case Claude requests multiple parallel tools
            for block in response.content:
                if block.type == "tool_use":
                    print(f"Claude wants to call: {block.name} with {block.input}")

                    # Execute the dummy tool
                    result = execute_tool(block.name, block.input)
                    print(f"Tool returned: {json.dumps(result.model_dump(), indent=2)}")

                    # Append tool results in the format Anthropic expects
                    tool_results_content.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result.output,
                        }
                    )

            # Keep conversation state accurate
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results_content})


if __name__ == "__main__":
    run_agentic_workflow()
