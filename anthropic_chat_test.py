from unittest.mock import patch, MagicMock
from anthropic_chat import MODELS, PROMPT, run_models

KNOWN_VALID_MODELS = [
    "claude-sonnet-4-6",
    "claude-opus-4-7",
    "claude-haiku-4-5-20251001",
    # add valid ones here
]


def test_no_unknown_model_names():
    """Catches typos in model names before deployment."""
    for model in MODELS:
        assert model in KNOWN_VALID_MODELS, f"Unknown model: {model}"


def test_prompt_is_not_empty():
    assert PROMPT.strip() != ""


@patch("anthropic_chat.get_anthropic_client")
def test_run_models_calls_api_for_each_model(mock_get_client):
    """Verifies we call the API once per model."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.content[0].text = "Hello"
    mock_response.usage.input_tokens = 5
    mock_response.usage.output_tokens = 10
    mock_response.stop_reason = "end_turn"
    mock_client.messages.create.return_value = mock_response

    run_models()
    assert mock_client.messages.create.call_count == len(MODELS)
