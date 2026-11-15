"""Unit tests for domain schemas and Pydantic v2 safety validators."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.domain.schemas import (
    ActionEnum,
    DiscrepancyFlag,
    PropertyAnalysis,
    ReconciliationReport,
)


def test_property_input_valid(sample_property_input):
    assert sample_property_input.property_id == "PROP-101"
    assert sample_property_input.price == Decimal("650000.00")
    assert len(sample_property_input.document_sources) == 2


def test_property_analysis_valid(sample_property_analysis):
    assert sample_property_analysis.viability_score == 88
    assert sample_property_analysis.recommended_action == ActionEnum.BUY
    assert sample_property_analysis.arv == Decimal("845000.00")


def test_property_analysis_score_bounds():
    with pytest.raises(ValidationError):
        PropertyAnalysis(
            viability_score=105,
            summary="Invalid score test",
            risk_factors=[],
            recommended_action=ActionEnum.PASS,
            arv=Decimal(100000),
            renovation_cost=Decimal(10000),
        )


def test_property_analysis_escalates_buy_when_reconciliation_conflicts():
    conflict_report = ReconciliationReport(
        is_consistent=False,
        tolerance_pct=0.02,
        discrepancies=[
            DiscrepancyFlag(
                field_name="annual_noi",
                values_by_source={
                    "offering_memorandum (p.4)": "$46,000.00",
                    "rent_roll (p.2)": "$36,200.00",
                },
                variance_pct=0.213,
            )
        ],
        audit_notes=["Conflict on annual_noi: 21.3% variance"],
    )

    analysis = PropertyAnalysis(
        viability_score=86,
        summary="Strong upside potential.",
        risk_factors=[],
        recommended_action=ActionEnum.BUY,
        arv=Decimal("600000.00"),
        renovation_cost=Decimal("40000.00"),
        reconciliation=conflict_report,
    )

    assert analysis.recommended_action == ActionEnum.INVESTIGATE
    assert analysis.viability_score <= 68


def test_action_enum_values():
    assert ActionEnum.BUY.value == "BUY"
    assert ActionEnum.PASS.value == "PASS"
    assert ActionEnum.INVESTIGATE.value == "INVESTIGATE"


@pytest.mark.parametrize(
    "risk_factor",
    [
        "Structural foundation remediation required",
        "High-risk FEMA flood zone exposure and mandatory insurance cost",
        "Adjacent environmental contamination risk (Phase I ESA required)",
        "Unresolved municipal zoning variance dependency",
        "Historical mold remediation requiring clearance verification",
        "Active tenant eviction / delinquency legal overhead",
    ],
)
def test_critical_risk_factors_block_buy_and_cap_score(risk_factor: str):
    """Critical underwriting hazards must downgrade BUY to INVESTIGATE and cap viability_score."""
    analysis = PropertyAnalysis(
        viability_score=85,
        summary="Strong upside potential on nominal cash flow.",
        risk_factors=[risk_factor],
        recommended_action=ActionEnum.BUY,
        arv=Decimal("600000.00"),
        renovation_cost=Decimal("40000.00"),
    )

    assert analysis.recommended_action == ActionEnum.INVESTIGATE
    assert analysis.viability_score <= 68


def test_non_critical_risk_factors_preserve_buy_and_score():
    """Benign cosmetic or ordinary regulatory notes must not falsely trip critical guardrails."""
    analysis = PropertyAnalysis(
        viability_score=84,
        summary="Strong turnkey asset with minor interior touch-ups.",
        risk_factors=[
            "Minor crown molding repair in foyer",
            "Potential Seattle municipal rental ordinance restrictions",
            "Deferred interior or mechanical CapEx items noted",
        ],
        recommended_action=ActionEnum.BUY,
        arv=Decimal("600000.00"),
        renovation_cost=Decimal("20000.00"),
    )

    assert analysis.recommended_action == ActionEnum.BUY
    assert analysis.viability_score == 84

