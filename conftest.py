import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_azure_and_anthropic():
    """Automatically patches out Azure and Anthropic networks globally during testing."""
    # Mock get_anthropic_client directly to prevent Azure calls
    with patch("customer_support_agent.get_anthropic_client") as mock_client:
        # Prevent Anthropic from making real API calls during initialization setup
        mock_instance = patch("anthropic.Anthropic").start()
        mock_client.return_value = mock_instance
        yield
