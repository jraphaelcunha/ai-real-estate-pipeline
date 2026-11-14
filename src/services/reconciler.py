"""Cross-document financial reconciliation service for deal intake packages."""

from decimal import Decimal

from src.domain.schemas import (
    DiscrepancyFlag,
    PropertyInput,
    ReconciliationReport,
)
from src.utils.logger import get_logger

logger = get_logger("reconciler")


class FinancialReconciler:
    """
    Compares extracted metrics across Offering Memorandums, Rent Rolls,
    and Broker Summaries while preserving document & page provenance.
    """

    def reconcile_documents(
        self,
        prop: PropertyInput,
        tolerance_pct: float = 0.02,
    ) -> ReconciliationReport:
        """
        Inspect multi-document metrics for variance exceeding tolerance_pct.
        Flags conflicting NOI, asking price, or unit count for analyst review.
        """
        if not prop.document_sources:
            return ReconciliationReport(
                is_consistent=True,
                tolerance_pct=tolerance_pct,
                discrepancies=[],
                audit_notes=["Single-source intake; no multi-document conflicts detected."],
            )

        discrepancies: list[DiscrepancyFlag] = []
        audit_notes: list[str] = []

        self._check_decimal_field(
            prop=prop,
            attr_name="reported_price",
            label="asking_price",
            baseline_value=prop.price,
            baseline_label="intake_listing",
            tolerance_pct=tolerance_pct,
            discrepancies=discrepancies,
            audit_notes=audit_notes,
        )
        self._check_decimal_field(
            prop=prop,
            attr_name="reported_noi",
            label="annual_noi",
            baseline_value=prop.stated_noi,
            baseline_label="stated_noi",
            tolerance_pct=tolerance_pct,
            discrepancies=discrepancies,
            audit_notes=audit_notes,
        )
        self._check_unit_counts(
            prop=prop,
            discrepancies=discrepancies,
            audit_notes=audit_notes,
        )

        is_consistent = len(discrepancies) == 0
        if is_consistent:
            audit_notes.append(
                f"Verified consistency across {len(prop.document_sources)} source documents "
                f"(tolerance {tolerance_pct * 100:.1f}%)."
            )
        else:
            logger.warning(
                "Detected %d financial conflict(s) for %s (%s)",
                len(discrepancies),
                prop.property_id,
                prop.address,
            )

        return ReconciliationReport(
            is_consistent=is_consistent,
            tolerance_pct=tolerance_pct,
            discrepancies=discrepancies,
            audit_notes=audit_notes,
        )

    def _check_decimal_field(
        self,
        *,
        prop: PropertyInput,
        attr_name: str,
        label: str,
        baseline_value: Decimal | None,
        baseline_label: str,
        tolerance_pct: float,
        discrepancies: list[DiscrepancyFlag],
        audit_notes: list[str],
    ) -> None:
        source_values: dict[str, Decimal] = {}
        for doc in prop.document_sources:
            val = getattr(doc, attr_name)
            if val is not None:
                source_key = f"{doc.document_type} (p.{doc.page_number})"
                source_values[source_key] = val

        if baseline_value is not None and len(source_values) >= 1:
            source_values[baseline_label] = baseline_value

        if len(source_values) < 2:
            return

        vals = list(source_values.values())
        min_val = min(vals)
        max_val = max(vals)

        if max_val == 0:
            return

        variance_pct = float((max_val - min_val) / max_val)
        if variance_pct > tolerance_pct:
            formatted = {k: f"${v:,.2f}" for k, v in source_values.items()}
            discrepancies.append(
                DiscrepancyFlag(
                    field_name=label,
                    values_by_source=formatted,
                    variance_pct=round(variance_pct, 4),
                    requires_analyst_review=True,
                )
            )
            audit_notes.append(
                f"Conflict on {label}: {variance_pct * 100:.1f}% variance across {list(formatted.keys())}."
            )

    def _check_unit_counts(
        self,
        *,
        prop: PropertyInput,
        discrepancies: list[DiscrepancyFlag],
        audit_notes: list[str],
    ) -> None:
        unit_sources: dict[str, int] = {}
        for doc in prop.document_sources:
            if doc.reported_units is not None:
                source_key = f"{doc.document_type} (p.{doc.page_number})"
                unit_sources[source_key] = doc.reported_units

        if prop.units is not None and len(unit_sources) >= 1:
            unit_sources["intake_listing"] = prop.units

        if len(unit_sources) < 2:
            return

        unique_counts = set(unit_sources.values())
        if len(unique_counts) > 1:
            min_u = min(unique_counts)
            max_u = max(unique_counts)
            variance_pct = round((max_u - min_u) / max_u, 4)
            formatted = {k: str(v) for k, v in unit_sources.items()}
            discrepancies.append(
                DiscrepancyFlag(
                    field_name="unit_count",
                    values_by_source=formatted,
                    variance_pct=variance_pct,
                    requires_analyst_review=True,
                )
            )
            audit_notes.append(
                f"Conflict on unit_count across sources: {formatted}."
            )
