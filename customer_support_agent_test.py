import pytest
from pydantic import ValidationError
from customer_support_agent import (
    execute_tool,
    ToolResult
)
from unittest.mock import patch, MagicMock

# ==========================================
# 1. TESTS FOR execute_tool (Local Router)
# ==========================================


def test_execute_tool_get_ticket_success():
    """Verify get_ticket routes correctly and processes input parameters."""
    payload = {"id": "12345"}
    result = execute_tool("get_ticket", payload)

    assert isinstance(result, ToolResult)
    assert "12345" in result.output
    assert "Open" in result.output


def test_execute_tool_get_ticket_missing_id():
    """Verify fallback string when ticket ID is unexpectedly absent."""
    payload = {}
    result = execute_tool("get_ticket", payload)
    assert "UNKNOWN" in result.output

@patch("hubspot_client.SecretClient")
@patch("hubspot_client.DefaultAzureCredential")
@patch("hubspot_client.HubSpot")
def test_execute_tool_lookup_crm_contact_success(mock_hubspot, mock_cred, mock_secret_client):
    """Verify look up contact uses a mocked Azure and HubSpot context."""
    
    # 1. Mock the Azure Key Vault secret value return
    mock_vault_instance = MagicMock()
    mock_vault_instance.get_secret.return_value.value = "mocked-service-key-12345"
    mock_secret_client.return_value = mock_vault_instance

    # 2. Mock the HubSpot API search return payload
    mock_hubspot_instance = MagicMock()
    mock_search_result = MagicMock()
    mock_contact = MagicMock()
    
    mock_contact.id = "12345"
    mock_contact.properties = {
        "firstname": "John",
        "lastname": "Doe",
        "email": "test@example.com"
    }
    
    mock_search_result.results = [mock_contact]
    mock_hubspot_instance.crm.contacts.search_api.do_search.return_value = mock_search_result
    mock_hubspot.return_value = mock_hubspot_instance

    # 3. Execute your tool execution block
    payload = {"emailid": "test@example.com"}
    result = execute_tool("lookup_crm_contact", payload)
    
    # 4. Assert that your agent logic formatted the mock data perfectly
    assert "John" in result.output
    assert "12345" in result.output


def test_execute_tool_static_responses():
    """Ensure parameterless dummy tools return expected success strings."""
    assert "Supabase DB Query" in execute_tool("query_order_history", {}).output
    assert "SendGrid success" in execute_tool("send_email", {}).output
    assert "Slack notification sent" in execute_tool("post_slack_message", {}).output
    assert "Freshdesk API success" in execute_tool("close_ticket", {}).output


def test_execute_tool_not_found():
    """Verify router cleanly handles unknown tool name execution."""
    result = execute_tool("invalid_tool_name", {})
    assert "not found" in result.output


# ==========================================
# 2. TESTS FOR HUBSPOT API FUNCTIONS (Mocked)
# ==========================================



# ==========================================
# 3. TESTS FOR PYDANTIC DATA VALIDATION
# ==========================================


def test_tool_result_validation_success():
    """Ensure ToolResult validates valid string schemas correctly."""
    result = ToolResult(output="Valid string outcome")
    assert result.output == "Valid string outcome"


def test_tool_result_validation_failure():
    """Ensure ToolResult enforces data constraints (e.g. rejects lists/dicts)."""
    with pytest.raises(ValidationError):
        # Passing invalid data type to test strict validation handling
        ToolResult(output=["not", "a", "string"])  # type: ignore
