"""
Pytest global fixtures and configurations for AI Real Estate Pipeline test suite.
"""

from decimal import Decimal
import pytest
from src.domain.schemas import PropertyInput, PropertyAnalysis, ActionEnum


@pytest.fixture
def sample_property_input():
    """Valid PropertyInput instance for property underwriting."""
    return PropertyInput(
        property_id="PROP-101",
        address="950 Summit Ave, Seattle, WA",
        price=Decimal("650000.00"),
        raw_description="Immaculate 4-plex in highly desirable Capitol Hill. Cap rate approx 8%.",
        link="https://www.zillow.com/homedetails/prop-101"
    )


@pytest.fixture
def sample_property_analysis():
    """Valid PropertyAnalysis instance."""
    return PropertyAnalysis(
        viability_score=88,
        summary="High yield Capitol Hill 4-plex with strong rental history and low initial capex requirements.",
        risk_factors=["Potential Seattle municipal rental ordinance restrictions"],
        recommended_action=ActionEnum.BUY,
        arv=Decimal("845000.00"),
        renovation_cost=Decimal("97500.00")
    )
