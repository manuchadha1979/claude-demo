import json
import logging

from anthropic_chat import get_anthropic_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# STEP 6 (safety cap): upper bound on loop iterations.
# WHY: this is only a backstop against a runaway loop (e.g. a tool that keeps
# failing and the model keeps retrying). It must NOT be the way the loop
# normally ends -- stop_reason == "end_turn" is. Using a cap as the primary
# stopping mechanism is an anti-pattern: it would cut off legitimate multi-step
# work or force extra useless calls. Normal queries finish well under 20.
MAX_ITERATIONS = 20

# STEP 1: tool definitions.
# WHY: Claude only knows what tools exist from these definitions. Each needs a
# name, a description (Claude uses it to decide WHICH tool fits the request --
# this is the model-driven tool selection that makes the loop "agentic"), and an
# input_schema in JSON Schema format that describes the arguments.
tools = [
    # Gateway-specific: the guardrail rejects requests (error 446) unless a tool
    # search tool is present and tools are deferred. This is not part of the
    # exercise itself. The search tool must NOT be deferred.
    {"type": "tool_search_tool_regex_20251119", "name": "tool_search_tool_regex"},
    {
        "name": "calculator",
        "defer_loading": True,  # gateway requirement, see above
        "description": "a calculator tool that accepts expression, returns result",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "The mathematical expression to evaluate"}
            },
            "required": ["expression"],
        },
    },
    {
        "name": "web_search",
        "defer_loading": True,  # gateway requirement, see above
        "description": "Looks up information on the web",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"],
        },
    },
]


def execute_tool(tool_name, tool_input):
    """Run the tool Claude asked for. Returns (result_dict, is_error)."""
    print(f"Executing tool: {tool_name} with input: {tool_input}")
    if tool_name == "calculator":
        expression = tool_input.get("expression")
        try:
            # Builtins stripped so the model can't call open(), __import__(), etc.
            # Fine for a demo; use a real expression parser in production.
            return {"result": eval(expression, {"__builtins__": {}}, {})}, False
        except Exception as e:
            return {"error": str(e)}, True
    elif tool_name == "web_search":
        query = tool_input.get("query", "")
        # STEP 1 (web search stub): returns mock results.
        # WHY it contains a concrete number: the multi-step test (STEP 5) needs
        # Claude to search FIRST, then feed the found value into the calculator.
        # An echo-only stub gives it nothing to calculate with.
        return {
            "results": [
                {
                    "title": f"Mock result for: {query}",
                    "snippet": "The population of Paris is about 2,100,000 and "
                               "the population of Berlin is about 3,700,000.",
                }
            ]
        }, False
    # Unknown tool: report it back instead of returning None / crashing, so
    # Claude can see the failure and recover.
    return {"error": f"Unknown tool: {tool_name}"}, True


def log_request_response(request, response):
    print(f"Request: {json.dumps(request, indent=2)}")
    print(f"Response: {json.dumps(response.model_dump(), indent=2)}")


def run_agentic_loop(user_input):
    """
    Do not build own client from anthropic.Client(). That client authenticates with an API key, and your gateway
    has API keys turned off. It will return 401: x-api-key auth disabled; authenticate via Okta JWT.
    Instead, use get_anthropic_client() from anthropic_chat.py. It uses ANTHROPIC_BASE_URL which is pointed to the gateway

    Returns the final text answer (or None if the loop stopped abnormally).
    """

    client = get_anthropic_client()
    print(f"[debug] base_url: {client.base_url}")

    # The conversation history. The API is stateless: Claude only "remembers"
    # earlier turns and tool results because we resend this whole list each call.
    messages = [{"role": "user", "content": user_input}]

    # STEP 2: the agentic loop.
    # WHY a loop: one request/response is not enough when Claude needs tools. It
    # asks for a tool, we run it, we send the result back, and Claude may then
    # ask for another tool or finish. We repeat until Claude says it is done.
    # The iteration counter feeds the STEP 6 safety cap.
    for iteration in range(1, MAX_ITERATIONS + 1):
        # (The exercise says client.messages.create; the gateway needs the beta
        # endpoint because of the tool search / defer_loading feature.)
        response = client.beta.messages.create(
            model="claude-sonnet-5-5",
            max_tokens=4096,
            tools=tools,
            messages=messages,
            betas=["advanced-tool-use-2025-11-20"],
        )

        print(f"[iteration {iteration}] stop_reason={response.stop_reason}")
        print(f"response: {json.dumps(response.model_dump(), indent=2)}")

        # STEP 2: branch on stop_reason.
        # WHY stop_reason: it is the API's own, deterministic signal of why
        # generation stopped. Alternatives are unreliable: checking whether the
        # content "looks like" a final answer, parsing the text for phrases like
        # "I'm done", or checking only for text blocks (Claude often writes text
        # AND requests a tool in the same turn).

        # STEP 4: end_turn = Claude finished the task.
        # WHY: this is the normal exit. Extract all text blocks (content is a
        # list of blocks; it may not start with text) and return the answer.
        if response.stop_reason == "end_turn":
            final_text = "".join(b.text for b in response.content if b.type == "text")
            print("Final response:", final_text)
            return final_text

        # STEP 3: tool_use = Claude wants us to run one or more tools.
        if response.stop_reason == "tool_use":
            # WHY a for loop: Claude can request several tools in ONE turn
            # (parallel tool calls). The API requires a tool_result for EVERY
            # tool_use block in the next user message, or it returns a 400
            # ("tool_use ids were found without tool_result blocks").
            tool_results = []
            for tool_block in (b for b in response.content if b.type == "tool_use"):
                print(f"Claude wants to call: {tool_block.name} with {tool_block.input}")
                result, is_error = execute_tool(tool_block.name, tool_block.input)
                print(f"Tool returned: {json.dumps(result, indent=2, default=str)}")
                tool_results.append(
                    {
                        "type": "tool_result",
                        # WHY the id: ties this result to the exact tool_use
                        # block it answers, which matters with parallel calls.
                        "tool_use_id": tool_block.id,
                        "content": json.dumps(result, default=str),
                        # WHY is_error: tells Claude the tool failed so it can
                        # fix its input or try another approach.
                        "is_error": is_error,
                    }
                )

            # WHY both appends, in this order: Claude's turn (including its
            # tool_use blocks) must be in the history before the results that
            # answer it, and tool results are sent with role "user". Without the
            # assistant message, the results would reference ids Claude never
            # issued. Without the results, Claude can't continue reasoning.
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue  # STEP 5: go around again so Claude can use the results.

        # Any other stop reason (max_tokens, refusal, ...): not something we can
        # fix by looping, so stop instead of resending the same request.
        logger.warning("Stopped with unexpected stop_reason=%s", response.stop_reason)
        return None

    # STEP 6: only reached if the for loop used all iterations without
    # returning, i.e. the safety cap triggered. Should never happen normally.
    logger.warning(
        "Safety cap hit: agentic loop reached MAX_ITERATIONS=%d without end_turn. "
        "Stopping to avoid a runaway loop.",
        MAX_ITERATIONS,
    )
    return None


def start_program():
    # Reads requests from stdin and runs the agentic loop until each is complete.
    #
    # STEP 5 (test): try a prompt that needs sequential tool calls, e.g.
    #   "Search for the populations of Paris and Berlin, then calculate how many
    #    times bigger Berlin is."
    # Expect: iteration 1 -> web_search (stop_reason=tool_use), iteration 2 ->
    # calculator (tool_use), iteration 3 -> final answer (end_turn). That is at
    # least two tool-call iterations before end_turn, well under MAX_ITERATIONS.
    print("Welcome to the agentic loop program. You can either calculate expressions or do web search.")
    while True:
        user_input = input("I can either calcualte expressions or do web search. Enter your request (or 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break
        run_agentic_loop(user_input)

"""
Try this prompt: "Search for the populations of Paris and Berlin, 
then calculate how many times bigger Berlin is." 
You should see iteration 1 and iteration 2 end with stop_reason=tool_use, 
then a final end_turn. Claude may batch both searches into a single turn, 
which is fine. The calculator call still has to come in a later iteration, 
because it needs the search results.
"""

if __name__ == "__main__":
    start_program()
