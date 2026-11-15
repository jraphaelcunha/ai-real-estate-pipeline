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


def test_heuristic_critical_risk_blocks_buy_despite_positive_keywords(monkeypatch):
    """Positive listing keywords must never override structural, flood, or zoning hazards into BUY."""
    monkeypatch.setattr("src.config.settings.OPENAI_API_KEY", "")
    analyzer = RealEstateAnalyzer()

    structural_prop = PropertyInput(
        property_id="PROP-RISK-1",
        address="101 Pine St, Seattle, WA",
        price=Decimal("450000.00"),
        sqft=2200,
        raw_description=(
            "Turnkey luxury flip with cap rate 10%, new HVAC, high cash flow. "
            "Minor structural damage to foundation."
        ),
        link="https://portal.reference-cre.example/listings/prop-risk-1",
    )
    res_structural = analyzer.analyze_property(structural_prop)
    assert res_structural is not None
    assert res_structural.recommended_action != ActionEnum.BUY
    assert res_structural.viability_score <= 68
    assert "Structural foundation remediation required" in res_structural.risk_factors

    flood_prop = PropertyInput(
        property_id="PROP-RISK-2",
        address="202 River Rd, Miami, FL",
        price=Decimal("520000.00"),
        sqft=2400,
        raw_description=(
            "Turnkey luxury flip with cap rate 10%, new HVAC, high cash flow. "
            "Situated inside a high-risk FEMA flood zone."
        ),
        link="https://portal.reference-cre.example/listings/prop-risk-2",
    )
    res_flood = analyzer.analyze_property(flood_prop)
    assert res_flood is not None
    assert res_flood.recommended_action != ActionEnum.BUY
    assert res_flood.viability_score <= 68


def test_heuristic_ignores_crown_molding_false_positive(monkeypatch):
    """Word-boundary risk matching must not confuse decorative crown molding with mold."""
    monkeypatch.setattr("src.config.settings.OPENAI_API_KEY", "")
    analyzer = RealEstateAnalyzer()

    clean_prop = PropertyInput(
        property_id="PROP-CLEAN-MOLDING",
        address="303 Oak Ave, Austin, TX",
        price=Decimal("400000.00"),
        sqft=2000,
        raw_description=(
            "Turnkey luxury residence featuring custom crown molding, new HVAC, "
            "and cap rate 9% with high cash flow."
        ),
        link="https://portal.reference-cre.example/listings/prop-clean-molding",
    )
    result = analyzer.analyze_property(clean_prop)
    assert result is not None
    assert all("mold" not in risk.lower() for risk in result.risk_factors)
    assert result.recommended_action == ActionEnum.BUY


def test_live_llm_critical_risk_in_raw_description_enforces_investigate(
    sample_property_input, monkeypatch
):
    """Even if a live LLM omits a critical listing hazard, deterministic guardrails block BUY."""
    monkeypatch.setattr("src.config.settings.OPENAI_API_KEY", "sk-test-fake-key-for-mock")
    with patch("src.services.analyzer.ChatOpenAI") as mock_chat:
        mock_instance = MagicMock()
        mock_instance.with_structured_output.return_value = MagicMock()
        mock_chat.return_value = mock_instance
        analyzer = RealEstateAnalyzer()

    risky_input = sample_property_input.model_copy(
        update={
            "raw_description": (
                "Turnkey luxury asset in Capitol Hill. Recent Phase 1 ESA flagged adjacent "
                "dry cleaner contamination risk."
            )
        }
    )
    permissive_llm_output = LLMUnderwritingOutput(
        viability_score=89,
        summary="High-yield urban property.",
        risk_factors=["Minor exterior paint wear"],
        recommended_action=ActionEnum.BUY,
        arv=Decimal("780000.00"),
        renovation_cost=Decimal("15000.00"),
    )

    with patch("src.services.analyzer.ChatPromptTemplate.from_messages") as mock_prompt_cls:
        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = permissive_llm_output
        mock_prompt.__or__.return_value = mock_chain
        mock_prompt_cls.return_value = mock_prompt

        result = analyzer.analyze_property(risky_input)

    assert result is not None
    assert result.recommended_action == ActionEnum.INVESTIGATE
    assert result.viability_score <= 68
    assert any("contamination" in r.lower() for r in result.risk_factors)

