"""Integration test for the end-to-end pipeline entrypoint."""

from unittest.mock import patch

from src.main import main


def test_pipeline_main_executes_end_to_end(monkeypatch):
    monkeypatch.setattr("src.config.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr("src.config.settings.MONDAY_API_KEY", "")

    with patch(
        "src.services.monday.get_coordinates",
        return_value={"lat": 32.7767, "lng": -96.7970, "address": "Dallas, TX"},
    ):
        processed_count = main("data/raw_mock_data.json")
        assert processed_count == 8
