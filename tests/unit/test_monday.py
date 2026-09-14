"""
Unit tests for MondayClient service and GraphQL mutation preparation.
"""

from unittest.mock import patch, MagicMock
from src.services.monday import MondayClient


def test_monday_client_dry_run_without_api_key(sample_property_input, sample_property_analysis, monkeypatch):
    """Verify that MondayClient logs dry-run without crashing when no API key is set."""
    monkeypatch.setattr("src.config.settings.MONDAY_API_KEY", "")
    client = MondayClient()

    with patch("src.services.monday.get_coordinates", return_value={"lat": 47.6, "lng": -122.3}):
        success = client.create_item(sample_property_input, sample_property_analysis)
        assert success is True


@patch("src.services.monday.requests.post")
def test_monday_client_executes_mutation_with_api_key(
    mock_post,
    sample_property_input,
    sample_property_analysis,
    monkeypatch
):
    """Verify that MondayClient dispatches GraphQL POST request when API key is provided."""
    monkeypatch.setattr("src.config.settings.MONDAY_API_KEY", "test_monday_key")
    client = MondayClient()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"create_item": {"id": "12345678"}}}
    mock_post.return_value = mock_resp

    with patch("src.services.monday.get_coordinates", return_value={"lat": 47.6, "lng": -122.3}):
        success = client.create_item(sample_property_input, sample_property_analysis)
        assert success is True
        assert mock_post.called
