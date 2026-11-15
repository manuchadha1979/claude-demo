import anthropic
client = anthropic.Anthropic()

def run_agent(messages, tools, model, max_tokens=2048,
              max_pauses=5, max_truncation_retries=2):
    pauses = truncs = 0
    while True:
        resp = client.messages.create(
            model=model, max_tokens=max_tokens,
            tools=tools, messages=messages,
        )
        sr = resp.stop_reason

        if sr == "end_turn":
            return resp

        elif sr == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = [
                {"type": "tool_result", "tool_use_id": b.id,
                 "content": execute_tool(b.name, b.input)}  # your code
                for b in resp.content if b.type == "tool_use"
            ]
            messages.append({"role": "user", "content": results})

        elif sr == "pause_turn":
            # Documented pattern: append assistant content, call again
            pauses += 1
            if pauses > max_pauses:
                raise RuntimeError("Too many pause_turn continuations")
            messages.append({"role": "assistant", "content": resp.content})

        elif sr == "max_tokens":
            truncs += 1
            if truncs > max_truncation_retries:
                return mark_truncated(resp, "max_tokens")
            max_tokens *= 2  # or continue; see note below

        elif sr == "model_context_window_exceeded":
            # More output budget won't help: the window is full.
            # Trim/summarise history or chunk the input.
            return mark_truncated(resp, "context_window")

        elif sr == "stop_sequence":
            # Expected, not an error. resp.stop_sequence holds the match.
            return resp

        elif sr == "refusal":
            # HTTP 200, not an exception. Log stop_details, then
            # fall back to another model or show a safe message.
            log_refusal(resp)
            return handle_refusal(resp)

        else:
            # Unknown future value: fail loudly, don't assume tool_use
            raise ValueError(f"Unhandled stop_reason: {sr}")
