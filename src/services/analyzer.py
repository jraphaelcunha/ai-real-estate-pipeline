"""Automated underwriting service with Pydantic v2 validation, reconciliation, and heuristic fallback."""

import re
from decimal import ROUND_HALF_UP, Decimal

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from openai import APIError, AuthenticationError, RateLimitError

from src.config import settings
from src.domain.schemas import (
    ActionEnum,
    LLMUnderwritingOutput,
    PropertyAnalysis,
    PropertyInput,
    ReconciliationReport,
)
from src.services.reconciler import FinancialReconciler
from src.utils.logger import get_logger

logger = get_logger("analyzer")

_RISK_RULES: tuple[tuple[tuple[str, ...], int, Decimal, str, bool], ...] = (
    (
        ("foundation", "structural damage"),
        -24,
        Decimal("0.18"),
        "Structural foundation remediation required",
        True,
    ),
    (
        ("flood zone", "fema"),
        -18,
        Decimal("0.05"),
        "High-risk FEMA flood zone exposure and mandatory insurance cost",
        True,
    ),
    (
        ("mold",),
        -10,
        Decimal("0.06"),
        "Historical mold remediation requiring clearance verification",
        True,
    ),
    (
        ("eviction", "non-payment"),
        -16,
        Decimal("0.03"),
        "Active tenant eviction / delinquency legal overhead",
        True,
    ),
    (
        ("zoning", "variance", "denied"),
        -22,
        Decimal("0.04"),
        "Unresolved municipal zoning variance dependency",
        True,
    ),
    (
        ("contamination", "dry cleaner", "phase 1"),
        -25,
        Decimal("0.15"),
        "Adjacent environmental contamination risk (Phase I ESA required)",
        True,
    ),
    (
        ("dated", "cosmetic", "older furnace", "roof age"),
        -4,
        Decimal("0.07"),
        "Deferred interior or mechanical CapEx items noted",
        False,
    ),
)

_POSITIVE_RULES: tuple[tuple[tuple[str, ...], int, Decimal], ...] = (
    (("immaculate", "turnkey", "new hvac", "recent upgrades"), 12, Decimal("0.08")),
    (("cap rate", "roi projected", "section 8", "cash flow"), 8, Decimal("0.04")),
    (("comps", "3.5m+", "luxury flip", "booming suburb"), 10, Decimal("0.16")),
)


class RealEstateAnalyzer:
    """
    Evaluates property acquisitions using structured LLM extraction paired with
    cross-document reconciliation and deterministic heuristic fallbacks.
    """

    def __init__(self, reconciler: FinancialReconciler | None = None) -> None:
        self.heuristic_mode = False
        self.llm = None
        self.reconciler = reconciler or FinancialReconciler()

        if not settings.OPENAI_API_KEY:
            logger.warning(
                "OPENAI_API_KEY not configured. Enabling deterministic heuristic underwriting mode."
            )
            self.heuristic_mode = True
        else:
            try:
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0,
                    timeout=15,
                    max_retries=2,
                )
            except Exception as exc:
                logger.error(
                    "Failed to initialize ChatOpenAI (%s). Falling back to heuristic mode.",
                    exc,
                )
                self.heuristic_mode = True

    @property
    def mock_mode(self) -> bool:
        """Backward-compatible alias indicating offline/deterministic heuristic mode."""
        return self.heuristic_mode

    def analyze_property(self, property_data: PropertyInput) -> PropertyAnalysis | None:
        """
        Execute multi-document reconciliation followed by structured LLM underwriting.
        Automatically degrades to deterministic heuristic underwriting on API limits/errors.
        """
        logger.info("Starting underwriting analysis for: %s", property_data.address)

        reconciliation = self.reconciler.reconcile_documents(property_data)
        price_per_sqft = self._calculate_price_per_sqft(property_data)

        if self.heuristic_mode:
            return self._compute_heuristic_underwriting(
                property_data=property_data,
                reconciliation=reconciliation,
                price_per_sqft=price_per_sqft,
            )

        system_msg = (
            "You are a Senior Real Estate Acquisitions Underwriter evaluating U.S. residential "
            "and small multifamily properties. Assess physical/environmental/legal risk factors "
            "strictly from the provided listing text and document reconciliation context. "
            "Estimate realistic renovation reserves and After Repair Value (ARV). "
            "If financial conflicts exist across documents or critical zoning/environmental risks appear, "
            "recommend INVESTIGATE or PASS rather than BUY."
        )

        reconciliation_summary = (
            "Consistent across available sources."
            if reconciliation.is_consistent
            else "; ".join(reconciliation.audit_notes)
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_msg),
                (
                    "user",
                    "Property ID: {property_id}\n"
                    "Address: {address}\n"
                    "Asking Price: ${price}\n"
                    "Square Footage: {sqft}\n"
                    "Units: {units}\n"
                    "Stated NOI: {stated_noi}\n"
                    "Document Reconciliation: {reconciliation_summary}\n"
                    "Listing Description: {description}\n"
                    "Source Link: {link}",
                ),
            ]
        )

        try:
            structured_llm = self.llm.with_structured_output(LLMUnderwritingOutput)
            chain = prompt | structured_llm

            result: LLMUnderwritingOutput = chain.invoke(
                {
                    "property_id": property_data.property_id,
                    "address": property_data.address,
                    "price": f"{property_data.price:,.2f}",
                    "sqft": property_data.sqft or "Unknown",
                    "units": property_data.units or "Unknown",
                    "stated_noi": f"${property_data.stated_noi:,.2f}"
                    if property_data.stated_noi is not None
                    else "Not provided",
                    "reconciliation_summary": reconciliation_summary,
                    "description": property_data.raw_description,
                    "link": str(property_data.link),
                }
            )

            enriched_risks = list(result.risk_factors)
            existing_risks_lower = " ".join(enriched_risks).lower()
            for critical_label in self._extract_critical_risk_labels(property_data.raw_description):
                if critical_label.lower() not in existing_risks_lower:
                    enriched_risks.append(critical_label)
            if not reconciliation.is_consistent:
                enriched_risks.extend(reconciliation.audit_notes)

            validated = PropertyAnalysis(
                viability_score=result.viability_score,
                summary=result.summary,
                risk_factors=enriched_risks,
                recommended_action=result.recommended_action,
                arv=result.arv,
                renovation_cost=result.renovation_cost,
                price_per_sqft=price_per_sqft,
                reconciliation=reconciliation,
            )
            logger.info("LLM underwriting completed for %s.", property_data.property_id)
            return validated

        except (AuthenticationError, RateLimitError, APIError) as exc:
            logger.warning(
                "OpenAI API degraded (%s: %s). Switching to deterministic heuristic fallback.",
                type(exc).__name__,
                exc,
            )
            return self._compute_heuristic_underwriting(
                property_data=property_data,
                reconciliation=reconciliation,
                price_per_sqft=price_per_sqft,
            )

        except Exception as exc:
            logger.warning(
                "Unexpected LLM pipeline failure (%s). Switching to heuristic fallback.",
                exc,
            )
            return self._compute_heuristic_underwriting(
                property_data=property_data,
                reconciliation=reconciliation,
                price_per_sqft=price_per_sqft,
            )

    def _calculate_price_per_sqft(self, prop: PropertyInput) -> Decimal | None:
        if not prop.sqft or prop.sqft <= 0:
            return None
        return (prop.price / Decimal(prop.sqft)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @staticmethod
    def _matches_keywords(text: str, keywords: tuple[str, ...]) -> bool:
        """Return True when any keyword phrase appears on non-word boundaries in text."""
        return any(re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", text) for kw in keywords)

    @classmethod
    def _extract_critical_risk_labels(cls, description: str) -> list[str]:
        """Extract deterministic critical underwriting risk labels from raw listing text."""
        lowered = description.lower()
        return [
            risk_label
            for keywords, _score_delta, _capex_delta, risk_label, is_critical in _RISK_RULES
            if is_critical and cls._matches_keywords(lowered, keywords)
        ]

    def _compute_heuristic_underwriting(
        self,
        property_data: PropertyInput,
        reconciliation: ReconciliationReport | None = None,
        price_per_sqft: Decimal | None = None,
    ) -> PropertyAnalysis:
        """
        Deterministic underwriting fallback that preserves batch continuity when external
        LLM endpoints experience rate limits or transient outages.
        """
        recon = reconciliation or self.reconciler.reconcile_documents(property_data)
        ppsf = price_per_sqft or self._calculate_price_per_sqft(property_data)
        text = property_data.raw_description.lower()

        score = 72
        reno_ratio = Decimal("0.08")
        arv_multiplier = Decimal("1.24")
        risk_factors: list[str] = []
        has_critical_risk = False

        for keywords, score_delta, capex_delta, risk_label, is_critical in _RISK_RULES:
            if self._matches_keywords(text, keywords):
                score += score_delta
                reno_ratio += capex_delta
                risk_factors.append(risk_label)
                if is_critical:
                    has_critical_risk = True

        for keywords, score_delta, arv_delta in _POSITIVE_RULES:
            if self._matches_keywords(text, keywords):
                score += score_delta
                arv_multiplier += arv_delta

        if has_critical_risk or not recon.is_consistent:
            score = min(score, 66)

        if not recon.is_consistent:
            risk_factors.extend(recon.audit_notes)

        if not risk_factors:
            risk_factors.append("Standard physical inspection and title verification pending")

        bounded_score = max(0, min(100, score))
        renovation_cost = (property_data.price * reno_ratio).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        arv = (property_data.price * arv_multiplier).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        if not recon.is_consistent:
            action = ActionEnum.INVESTIGATE
        elif has_critical_risk:
            action = ActionEnum.INVESTIGATE if bounded_score >= 52 else ActionEnum.PASS
        elif bounded_score >= 75:
            action = ActionEnum.BUY
        elif bounded_score >= 52:
            action = ActionEnum.INVESTIGATE
        else:
            action = ActionEnum.PASS

        ppsf_note = f" (${ppsf:,.2f}/sqft)" if ppsf is not None else ""
        if not recon.is_consistent:
            summary = (
                f"Heuristic screening flagged financial discrepancies across deal documents{ppsf_note}. "
                "Routed to analyst queue for side-by-side document verification."
            )
        else:
            summary = (
                f"Heuristic underwriting scored asset at {bounded_score}/100{ppsf_note} with "
                f"estimated ${renovation_cost:,.0f} CapEx and ${arv:,.0f} projected ARV."
            )

        return PropertyAnalysis(
            viability_score=bounded_score,
            summary=summary,
            risk_factors=risk_factors,
            recommended_action=action,
            arv=arv,
            renovation_cost=renovation_cost,
            price_per_sqft=ppsf,
            reconciliation=recon,
        )
