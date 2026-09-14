"""
Unit tests for RealEstateAnalyzer service and fallback strategies.
"""

from decimal import Decimal
from unittest.mock import patch, MagicMock
from src.services.analyzer import RealEstateAnalyzer
from src.domain.schemas import ActionEnum


def test_analyzer_fallback_to_mock_mode_when_no_api_key(sample_property_input, monkeypatch):
    """Verify analyzer initializes mock mode gracefully without API key."""
    monkeypatch.setattr("src.config.settings.OPENAI_API_KEY", "")
    analyzer = RealEstateAnalyzer()

    assert analyzer.mock_mode is True
    result = analyzer.analyze_property(sample_property_input)

    assert result is not None
    assert result.viability_score == 85
    assert result.recommended_action == ActionEnum.BUY
    assert result.arv == Decimal("350000.00")


def test_analyzer_recovers_from_api_error(sample_property_input, monkeypatch):
    """Verify analyzer catches API errors and falls back to mock analysis."""
    monkeypatch.setattr("src.config.settings.OPENAI_API_KEY", "mock_key")
    analyzer = RealEstateAnalyzer()

    with patch.object(analyzer, "_get_mock_analysis") as mock_fallback:
        mock_fallback.return_value = "fallback_called"
        # Force exception on structured output or invoke
        analyzer.llm = MagicMock()
        analyzer.llm.with_structured_output.side_effect = Exception("API Timeout")

        result = analyzer.analyze_property(sample_property_input)
        assert result == "fallback_called"
