"""
Unit tests for real estate JSON file ingestion service.
"""

import json

from src.services.ingestor import JsonFileIngestor


def test_ingestor_loads_mock_data():
    ingestor = JsonFileIngestor("data/raw_mock_data.json")
    properties = ingestor.load_properties()

    assert len(properties) > 0
    assert properties[0].property_id.startswith("PROP-")
    assert properties[0].price > 0


def test_ingestor_missing_file_returns_empty():
    ingestor = JsonFileIngestor("data/non_existent_file.json")
    properties = ingestor.load_properties()
    assert properties == []


def test_ingestor_fault_tolerance_with_malformed_records(tmp_path):
    temp_file = tmp_path / "test_malformed.json"
    data = [
        {
            "property_id": "PROP-VALID-1",
            "address": "123 Valid St, Seattle, WA",
            "price": 500000.0,
            "raw_description": "Valid listing",
            "link": "https://example.com/prop1"
        },
        {
            "property_id": "PROP-INVALID",
            # Missing address field and invalid price
            "price": "not-a-number",
            "raw_description": "Broken listing",
            "link": "https://example.com/prop2"
        }
    ]
    temp_file.write_text(json.dumps(data), encoding="utf-8")

    ingestor = JsonFileIngestor(str(temp_file))
    properties = ingestor.load_properties()

    assert len(properties) == 1
    assert properties[0].property_id == "PROP-VALID-1"
