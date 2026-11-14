from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

DocumentType = Literal[
    "offering_memorandum",
    "rent_roll",
    "broker_summary",
    "listing_portal",
]


class DocumentSourceMetric(BaseModel):
    """Financial metric extracted from a specific deal package document and page."""

    document_type: DocumentType
    page_number: int = Field(ge=1)
    reported_price: Decimal | None = Field(default=None, gt=0)
    reported_noi: Decimal | None = Field(default=None, ge=0)
    reported_units: int | None = Field(default=None, ge=1)


class DiscrepancyFlag(BaseModel):
    """Tracks a financial variance exceeding tolerance across multiple deal documents."""

    field_name: str
    values_by_source: dict[str, str]
    variance_pct: float = Field(ge=0.0)
    requires_analyst_review: bool = True


class ReconciliationReport(BaseModel):
    """Cross-document consistency summary produced prior to or alongside LLM underwriting."""

    is_consistent: bool
    tolerance_pct: float = Field(default=0.02, ge=0.0)
    discrepancies: list[DiscrepancyFlag] = Field(default_factory=list)
    audit_notes: list[str] = Field(default_factory=list)


class PropertyInput(BaseModel):
    """Validated property intake contract from scrapers or JSON deal feeds."""

    property_id: str
    address: str
    price: Decimal = Field(gt=0)
    raw_description: str
    link: HttpUrl | str
    sqft: int | None = Field(default=None, gt=0)
    units: int | None = Field(default=None, ge=1)
    stated_noi: Decimal | None = Field(default=None, ge=0)
    document_sources: list[DocumentSourceMetric] = Field(default_factory=list)


class ActionEnum(str, Enum):
    """Workflow routing actions mapped to Monday.com CRM board statuses."""

    BUY = "BUY"
    PASS = "PASS"  # noqa: S105 # nosec B105 - Enum status action, not a password
    INVESTIGATE = "INVESTIGATE"


class LLMUnderwritingOutput(BaseModel):
    """Structured extraction contract strictly restricted to LLM-generated underwriting fields."""

    viability_score: int = Field(..., ge=0, le=100, description="Score from 0-100")
    summary: str = Field(..., description="Executive summary, max 2 sentences")
    risk_factors: list[str] = Field(default_factory=list)
    recommended_action: ActionEnum
    arv: Decimal = Field(..., description="After Repair Value")
    renovation_cost: Decimal = Field(..., description="Estimated Renovation Cost")


class PropertyAnalysis(BaseModel):
    """Strict underwriting output contract enforcing financial and escalation invariants."""

    viability_score: int = Field(..., ge=0, le=100, description="Score from 0-100")
    summary: str = Field(..., description="Executive summary, max 2 sentences")
    risk_factors: list[str] = Field(default_factory=list)
    recommended_action: ActionEnum
    arv: Decimal = Field(..., description="After Repair Value")
    renovation_cost: Decimal = Field(..., description="Estimated Renovation Cost")
    price_per_sqft: Decimal | None = Field(
        default=None, description="Normalized purchase price per square foot"
    )
    reconciliation: ReconciliationReport | None = Field(default=None)
    assigned_broker: str | None = Field(default=None)

    @model_validator(mode="after")
    def enforce_risk_and_reconciliation_guardrails(self) -> "PropertyAnalysis":
        """Never allow blind BUY approval when cross-document financials conflict."""
        if (
            self.reconciliation is not None
            and not self.reconciliation.is_consistent
            and self.recommended_action == ActionEnum.BUY
        ):
            self.recommended_action = ActionEnum.INVESTIGATE
            if self.viability_score > 68:
                self.viability_score = 68

        critical_risk_markers = (
            "soil contamination",
            "structural damage",
            "zoning variance denied",
        )
        lowered_risks = " ".join(self.risk_factors).lower()
        if (
            any(marker in lowered_risks for marker in critical_risk_markers)
            and self.recommended_action == ActionEnum.BUY
        ):
            self.recommended_action = ActionEnum.INVESTIGATE

        return self
