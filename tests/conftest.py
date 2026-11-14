"""Pytest global fixtures and configurations for AI Real Estate Pipeline test suite."""

from decimal import Decimal

import pytest

from src.domain.schemas import (
    ActionEnum,
    DocumentSourceMetric,
    PropertyAnalysis,
    PropertyInput,
)


@pytest.fixture
def sample_property_input():
    """Valid PropertyInput instance with consistent multi-document provenance."""
    return PropertyInput(
        property_id="PROP-101",
        address="950 Summit Ave, Seattle, WA",
        price=Decimal("650000.00"),
        sqft=3400,
        units=4,
        stated_noi=Decimal("52000.00"),
        raw_description="Immaculate 4-plex in highly desirable Capitol Hill. Cap rate approx 8%.",
        link="https://portal.reference-cre.example/listings/prop-101",
        document_sources=[
            DocumentSourceMetric(
                document_type="offering_memorandum",
                page_number=3,
                reported_price=Decimal("650000.00"),
                reported_noi=Decimal("52000.00"),
                reported_units=4,
            ),
            DocumentSourceMetric(
                document_type="rent_roll",
                page_number=1,
                reported_noi=Decimal("51500.00"),
                reported_units=4,
            ),
        ],
    )


@pytest.fixture
def conflicting_property_input():
    """PropertyInput containing a significant NOI discrepancy between OM and Rent Roll."""
    return PropertyInput(
        property_id="PROP-CONFLICT",
        address="4510 Swiss Ave, Dallas, TX",
        price=Decimal("485000.00"),
        sqft=2950,
        units=4,
        stated_noi=Decimal("46000.00"),
        raw_description="Turnkey brick 4-plex near East Dallas medical corridor. New HVAC installed.",
        link="https://portal.reference-cre.example/listings/prop-conflict",
        document_sources=[
            DocumentSourceMetric(
                document_type="offering_memorandum",
                page_number=4,
                reported_price=Decimal("485000.00"),
                reported_noi=Decimal("46000.00"),
                reported_units=4,
            ),
            DocumentSourceMetric(
                document_type="rent_roll",
                page_number=2,
                reported_noi=Decimal("36200.00"),
                reported_units=4,
            ),
        ],
    )


@pytest.fixture
def sample_property_analysis():
    """Valid PropertyAnalysis instance."""
    return PropertyAnalysis(
        viability_score=88,
        summary="High-yield Capitol Hill 4-plex with strong rental history and low initial CapEx requirements.",
        risk_factors=["Potential Seattle municipal rental ordinance restrictions"],
        recommended_action=ActionEnum.BUY,
        arv=Decimal("845000.00"),
        renovation_cost=Decimal("97500.00"),
        price_per_sqft=Decimal("191.18"),
    )
