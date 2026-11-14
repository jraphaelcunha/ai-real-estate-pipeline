"""Unit tests for RealEstateAnalyzer service, heuristic fallback, and guardrails."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.domain.schemas import ActionEnum, LLMUnderwritingOutput, PropertyInput
from src.services.analyzer import RealEstateAnalyzer


def test_analyzer_heuristic_mode_when_no_api_key(sample_property_input, monkeypatch):
    """Verify analyzer transitions cleanly to deterministic heuristic mode without API key."""
    monkeypatch.setattr("src.config.settings.OPENAI_API_KEY", "")
    analyzer = RealEstateAnalyzer()

    assert analyzer.heuristic_mode is True
    assert analyzer.mock_mode is True
    result = analyzer.analyze_property(sample_property_input)

    assert result is not None
    assert result.viability_score >= 75
    assert result.recommended_action == ActionEnum.BUY
    assert result.arv > sample_property_input.price
    assert result.renovation_cost > Decimal("0")
    assert result.price_per_sqft == Decimal("191.18")
    assert "Mock analysis" not in result.summary


def test_analyzer_escalates_conflicting_documents_to_investigate(
    conflicting_property_input, monkeypatch
):
    """Verify multi-document financial discrepancies prevent blind BUY recommendations."""
    monkeypatch.setattr("src.config.settings.OPENAI_API_KEY", "")
    analyzer = RealEstateAnalyzer()

    result = analyzer.analyze_property(conflicting_property_input)

    assert result is not None
    assert result.recommended_action == ActionEnum.INVESTIGATE
    assert result.reconciliation is not None
    assert result.reconciliation.is_consistent is False


def test_analyzer_penalizes_severe_physical_risks(monkeypatch):
    """Verify heuristic scoring penalizes foundation, flood zone, and contamination risks."""
    monkeypatch.setattr("src.config.settings.OPENAI_API_KEY", "")
    analyzer = RealEstateAnalyzer()
    distressed = PropertyInput(
        property_id="PROP-DISTRESSED",
        address="12 Biscayne Canal Rd, Miami, FL",
        price=Decimal("200000.00"),
        raw_description=(
            "Significant structural damage to foundation visible. Located in flood zone AE "
            "requiring FEMA insurance and mold clearance."
        ),
        link="https://portal.reference-cre.example/listings/prop-distressed",
    )

    result = analyzer.analyze_property(distressed)

    assert result is not None
    assert result.recommended_action == ActionEnum.PASS
    assert result.viability_score < 52
    assert len(result.risk_factors) >= 3


def test_analyzer_recovers_from_api_error(sample_property_input, monkeypatch):
    """Verify analyzer catches API errors and falls back to deterministic heuristic engine."""
    monkeypatch.setattr("src.config.settings.OPENAI_API_KEY", "test_key")
    analyzer = RealEstateAnalyzer()

    with patch.object(analyzer, "_compute_heuristic_underwriting") as mock_fallback:
        mock_fallback.return_value = "fallback_called"
        analyzer.llm = MagicMock()
        analyzer.llm.with_structured_output.side_effect = RuntimeError("API Timeout")

        result = analyzer.analyze_property(sample_property_input)
        assert result == "fallback_called"


def test_analyzer_live_llm_uses_isolated_llm_underwriting_schema(
    sample_property_input, monkeypatch
):
    """Verify live LLM path binds to LLMUnderwritingOutput and injects deterministic fields post-LLM."""
    monkeypatch.setattr("src.config.settings.OPENAI_API_KEY", "test_key")
    analyzer = RealEstateAnalyzer()
    analyzer.llm = MagicMock()

    mock_llm_output = LLMUnderwritingOutput(
        viability_score=84,
        summary="Strong value-add acquisition candidate.",
        risk_factors=["Minor roof wear"],
        recommended_action=ActionEnum.BUY,
        arv=Decimal("415000.00"),
        renovation_cost=Decimal("28000.00"),
    )

    with patch("src.services.analyzer.ChatPromptTemplate.from_messages") as mock_prompt_cls:
        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_llm_output
        mock_prompt.__or__.return_value = mock_chain
        mock_prompt_cls.return_value = mock_prompt

        result = analyzer.analyze_property(sample_property_input)

    analyzer.llm.with_structured_output.assert_called_once_with(LLMUnderwritingOutput)
    assert result is not None
    assert result.viability_score == 84
    assert result.price_per_sqft == Decimal("191.18")
    assert result.reconciliation is not None
    assert result.reconciliation.is_consistent is True
