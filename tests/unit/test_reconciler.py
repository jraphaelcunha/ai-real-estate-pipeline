"""Unit tests for cross-document FinancialReconciler service."""

from decimal import Decimal

from src.domain.schemas import DocumentSourceMetric, PropertyInput
from src.services.reconciler import FinancialReconciler


def test_reconciler_passes_within_tolerance(sample_property_input):
    reconciler = FinancialReconciler()
    report = reconciler.reconcile_documents(sample_property_input, tolerance_pct=0.02)

    assert report.is_consistent is True
    assert report.discrepancies == []


def test_reconciler_flags_noi_conflict_with_page_provenance(conflicting_property_input):
    reconciler = FinancialReconciler()
    report = reconciler.reconcile_documents(conflicting_property_input, tolerance_pct=0.02)

    assert report.is_consistent is False
    assert len(report.discrepancies) == 1
    flag = report.discrepancies[0]
    assert flag.field_name == "annual_noi"
    assert "offering_memorandum (p.4)" in flag.values_by_source
    assert "rent_roll (p.2)" in flag.values_by_source
    assert flag.variance_pct > 0.20
    assert flag.requires_analyst_review is True


def test_reconciler_flags_unit_count_mismatch():
    prop = PropertyInput(
        property_id="PROP-UNITS",
        address="100 Elm St, Dallas, TX",
        price=Decimal("400000.00"),
        units=4,
        raw_description="Multifamily asset.",
        link="https://portal.reference-cre.example/listings/prop-units",
        document_sources=[
            DocumentSourceMetric(
                document_type="offering_memorandum",
                page_number=2,
                reported_units=4,
            ),
            DocumentSourceMetric(
                document_type="rent_roll",
                page_number=1,
                reported_units=3,
            ),
        ],
    )

    reconciler = FinancialReconciler()
    report = reconciler.reconcile_documents(prop)

    assert report.is_consistent is False
    assert report.discrepancies[0].field_name == "unit_count"
