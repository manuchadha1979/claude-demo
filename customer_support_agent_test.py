import pytest
import requests_mock
from pydantic import ValidationError
from customer_support_agent import (
    execute_tool, 
    lookup_crm_contact, 
    create_deal, 
    ToolResult, 
    BASE
)

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

def test_execute_tool_lookup_crm_contact_success():
    """Verify look up contact uses the custom parameter key."""
    payload = {"emailid": "test@example.com"}
    result = execute_tool("lookup_crm_contact", payload)
    assert "test@example.com" in result.output

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

def test_lookup_crm_contact_found():
    """Test contact lookup when HubSpot returns a matching record."""
    email = "john@example.com"
    mock_response = {
        "results": [
            {
                "id": "123",
                "properties": {"firstname": "John", "email": email}
            }
        ]
    }

    with requests_mock.Mocker() as mock:
        mock.get(f"{BASE}/crm/v3/objects/contacts/search", json=mock_response, status_code=200)
        
        contact = lookup_crm_contact(email)
        assert contact["id"] == "123"
        assert contact["properties"]["email"] == email

def test_lookup_crm_contact_not_found():
    """Test contact lookup when HubSpot returns an empty result list."""
    email = "missing@example.com"
    mock_response = {"results": []}

    with requests_mock.Mocker() as mock:
        mock.get(f"{BASE}/crm/v3/objects/contacts/search", json=mock_response, status_code=200)
        
        contact = lookup_crm_contact(email)
        assert contact == {}


def test_create_deal_success():
    """Verify payload generation and response mapping for deal creation."""
    mock_response = {
        "id": "998877",
        "properties": {
            "dealname": "Test Deal",
            "amount": "500.0",
            "dealstage": "appointmentscheduled"
        }
    }

    with requests_mock.Mocker() as mock:
        mock.post(f"{BASE}/crm/v3/objects/deals", json=mock_response, status_code=201)
        
        deal = create_deal(contact_id="123", deal_name="Test Deal", amount=500.0)
        assert deal["id"] == "998877"
        assert deal["properties"]["dealname"] == "Test Deal"


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