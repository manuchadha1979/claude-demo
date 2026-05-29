import json
from pydantic import BaseModel
from anthropic_chat import get_anthropic_client
from hubspot_client import lookup_crm_contact
from jsm_client import get_ticket,get_available_transitions,apply_ticket_transition
from supabase_client import lookup_customer_orders
from slack_client import post_message_to_channel
from gmail_client import send_gmail_email

class ToolResult(BaseModel):
    output: str  # Or Any, if your tool returns dicts/lists sometimes


def execute_tool(name: str, input_data: dict) -> ToolResult:
    print(f"executing tool {name} with input {input_data}")
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
        # 1. Extract the email from Claude's input data
        email = input_data.get("emailid", "")

        if email:
            # 2. Call the Supabase function and store the resulting list of orders
            order_data = lookup_customer_orders(email)

            # 3. Parse the result dynamically
            # Since Supabase returns a list (or an error dict), we handle both
            if isinstance(order_data, list) and len(order_data) > 0:
                order_lines = []
                
                # Loop through each order found for this customer
                for order in order_data:
                    order_id = order.get("id")
                    total_amount = order.get("total_amount", 0.0)
                    status = order.get("status", "unknown")
                    created_at = order.get("created_at", "")
                    
                    # Format a clean string line for this specific order
                    order_lines.append(
                        f"- Order ID: {order_id} | Amount: ${total_amount:.2f} | Status: {status} | Date: {created_at}"
                    )
                
                # Combine all the order lines into one final message
                all_orders_text = "\n".join(order_lines)
                output_text = f"Found the following order history for {email}:\n{all_orders_text}"
                
            elif isinstance(order_data, dict) and "error" in order_data:
                # Handle database execution errors safely
                output_text = f"An error occurred while fetching orders: {order_data['error']}"
            else:
                # Handle the fallback case where the list was empty []
                output_text = f"No order history found matching customer email: {email}"
                
        else:
            output_text = "Error: 'emailid' parameter was missing or empty. Please provide a valid email address."

            # 4. Return the populated ToolResult model
        return ToolResult(output=output_text)
    elif name == "send_email":
        # 1. Extract parameters from the agent's input data
        to_email = input_data.get("to_email", "").strip() or input_data.get("recipient", "").strip()
        subject = input_data.get("subject", "").strip()
        body_content = input_data.get("body", "").strip() or input_data.get("body_content", "").strip()

        # 2. Ensure all required parameters are present
        if to_email and subject and body_content:
            try:
                # 3. Call the Gmail function (which pulls credentials from Azure Vault)
                send_gmail_email(to_email=to_email, subject=subject, body_content=body_content)
                output_text = f"Successfully sent email to '{to_email}' with subject: '{subject}'."
            except Exception as e:
                # Handle execution or SMTP login errors safely
                output_text = f"Failed to send email to '{to_email}'. Error details: {str(e)}"
                
        else:
            # 4. Handle missing parameters gracefully
            missing_params = []
            if not to_email: 
                missing_params.append("'to_email'")
            if not subject: 
                missing_params.append("'subject'")
            if not body_content: 
                missing_params.append("'body'")
            
            output_text = f"Error: Missing required parameter(s): {', '.join(missing_params)}. To dispatch an email, please provide the recipient's address, a subject line, and the message body."
        
        return ToolResult(output=output_text)
    elif name == "change_ticket_status":
        # 1. Extract parameters from Claude's input data
        ticket_id = input_data.get("ticketID", "").strip() or input_data.get("ticket_id", "").strip()
        transition_choice = input_data.get("transition", "").strip() or input_data.get("transition_name_or_id", "").strip()
        reason = input_data.get("reason", "").strip()

        # 2. Ensure all required parameters are present
        if ticket_id and transition_choice and reason:
            # 3. Execute the status change and update the ticket with the comment
            execution_result = apply_ticket_transition(
                ticket_id=ticket_id, 
                transition_name_or_id=transition_choice, 
                reason=reason
            )

            # 4. Check the dictionary result returned by your function
            if "Error" in execution_result.get("result", ""):
                output_text = f"Failed to update ticket '{ticket_id}'. {execution_result['result']}"
            else:
                output_text = f"Successfully updated ticket '{ticket_id}'. Details: {execution_result['result']}"
                
        else:
            # 5. Handle missing parameters gracefully
            missing_params = []
            if not ticket_id: 
                missing_params.append("'id'")
            if not transition_choice: 
                missing_params.append("'transition'")
            if not reason: 
                missing_params.append("'reason'")
            output_text = f"Error: Missing required parameter(s): {', '.join(missing_params)}. To change a ticket status, please provide the ticket ID, the target transition, and a reason/comment."
        return ToolResult(output=output_text)
    elif name == "get_ticket_transitions":
        # 1. Extract the ticket ID from the agent's input data
        ticket_id = input_data.get("ticketID", "").strip() or input_data.get("ticket_id", "").strip()

        if ticket_id:
            # 2. Call our tool function to pull transitions from Jira
            transitions_list = get_available_transitions(ticket_id=ticket_id)

            # 3. Parse the result dynamically based on what our function returns
            if not transitions_list:
                # Handle cases where no transitions are returned or an API error occurred
                output_text = f"Failed to retrieve transitions for ticket '{ticket_id}', or there are no valid transitions available for its current status."
            else:
                # Handle successful data retrieval and format it into a readable string for the agent
                formatted_transitions = [f"Name: '{t['name']}' (ID: {t['id']})" for t in transitions_list]
                output_text = f"Successfully retrieved available transitions for ticket '{ticket_id}':\n" + "\n".join(formatted_transitions)
                
        else:
            # Handle missing parameters gracefully
            output_text = "Error: Missing required parameter: 'id' (ticket ID). Please provide a valid Jira ticket identifier."
        return ToolResult(output=output_text)
    elif name == "post_slack_message":
        # 1. Extract the channel ID and message content from Claude's input data
        channel_id = input_data.get("channelid", "").strip()
        message_text = input_data.get("message", "").strip()

        if channel_id and message_text:
            # 2. Call the Slack client function to post the message
            slack_response = post_message_to_channel(channel_id=channel_id, message_text=message_text)

            # 3. Parse the result dynamically based on what our function returns
            if "error" in slack_response:
                # Handle Slack API or execution errors safely
                output_text = f"Failed to send Slack message to channel '{channel_id}'. Error: {slack_response['error']}"
            else:
                # Handle successful message delivery
                timestamp = slack_response.get("ts", "unknown")
                output_text = f"Successfully posted message to Slack channel '{channel_id}' at timestamp {timestamp}."
                
        else:
            # Handle missing parameters gracefully
            missing_params = []
            if not channel_id: 
                missing_params.append("'channel'")
            if not message_text: 
                missing_params.append("'message'")
            
            output_text = f"Error: Missing required parameter(s): {', '.join(missing_params)}. Please provide both a valid channel ID and a message."

        # 4. Return the populated ToolResult model back to the AI agent
        return ToolResult(output=output_text)
    else:
        return ToolResult(output=f"Tool '{name}' not found")


PROMPT = """Hey, can you look into JSM ticket SUP-1? 
Find the customer's email from that ticket so you can pull up their contact profile in HubSpot.
Once you have their details, check their full order history in our Supabase DB to see why
 they are complaining about a missing shipment. If you find the issue, go ahead and send them a
 resolution update via SendGrid. Also, please ping the #escalations team on Slack
 to let them know we are escalating a shipping delay for this customer. 
 Finally, once all of that is done, go ahead and change the status of the ticket in jsm"""


tools = [
    {
        "name": "get_ticket",
        "description": "Fetch ticket from JSM by ID",
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "customers ID"}
            },
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
            "required": ["emailid"]
        },
    },
    {
        "name": "query_order_history",
        "description": "Fetch orders from Supabase DB",
        "input_schema": {
            "type": "object",
            "properties": {"emailid": {"type": "string", "description": "email ID"}
            },
            "required": ["emailid"]
        },
    },
    {
        "name": "send_email",
        "description": "Send resolution email via SendGrid",
        "input_schema": {
            "type": "object",
            "properties": {
                "to_email": {"type": "string", "description": "customer email ID"},
                "subject": {"type": "string", "description": "subject of the email"},
                "body_content": {"type": "string", "description": "body of the email"},
            },
            "required": ["emailid","subject","body_content"]
        },
    },
    {
        "name": "post_slack_message",
        "description": "Post escalation to Slack channel",
        "input_schema": {
            "type": "object",
            "properties": {
                "channelid": {"type": "string", "description": "slack channel ID"},
                "message": {"type": "string", "description": "message to send on the slack channel"}
            },
            "required": ["channelid","message"]
        },
    },
    {
        "name": "change_ticket_status",
        "description": "Change the status of the ticket depending on the update on its progress.",
        "input_schema": {
            "type": "object",
            "properties": {"ticketID": {"type": "string", "description": "ticket ID"},
                           "transition_name_or_id": {"type": "string", "description": "next transition name or id"},
                           "reason": {"type": "string", "description": "reason for the transition"}

            },
            "required": ["ticketID","transition_name_or_id","reason"]
        },
    },
    {
        "name": "get_ticket_transitions",
        "description": "Get possition values of transitions of status of the ticket based on current status. Next possible transition states depend on current state",
        "input_schema": {
            "type": "object",
            "properties": {"ticketID": {"type": "string", "description": "ticket ID"}
            },
            "required": ["ticketID"]
        },
    }
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
