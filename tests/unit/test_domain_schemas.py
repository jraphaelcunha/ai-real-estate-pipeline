"""
Unit tests for domain schemas and contracts in AI Real Estate Pipeline.
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError
from src.domain.schemas import PropertyInput, PropertyAnalysis, ActionEnum


def test_property_input_valid(sample_property_input):
    assert sample_property_input.property_id == "PROP-101"
    assert sample_property_input.price == Decimal("650000.00")
    assert "Capitol Hill" in sample_property_input.raw_description


def test_property_analysis_valid(sample_property_analysis):
    assert sample_property_analysis.viability_score == 88
    assert sample_property_analysis.recommended_action == ActionEnum.BUY
    assert sample_property_analysis.arv == Decimal("845000.00")


def test_property_analysis_score_bounds():
    with pytest.raises(ValidationError):
        PropertyAnalysis(
            viability_score=105,  # Out of 0-100 range
            summary="Invalid score test",
            risk_factors=[],
            recommended_action=ActionEnum.PASS,
            arv=Decimal("100000"),
            renovation_cost=Decimal("10000")
        )


def test_action_enum_values():
    assert ActionEnum.BUY.value == "BUY"
    assert ActionEnum.PASS.value == "PASS"
    assert ActionEnum.INVESTIGATE.value == "INVESTIGATE"
