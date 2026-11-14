"""Entrypoint orchestrating property intake, financial reconciliation, underwriting, and Monday.com sync."""

from src.services.analyzer import RealEstateAnalyzer
from src.services.ingestor import JsonFileIngestor
from src.services.monday import MondayClient
from src.utils.logger import get_logger

logger = get_logger("pipeline_main")


def main(data_path: str = "data/raw_mock_data.json") -> int:
    """Run the full real estate underwriting pipeline and return processed property count."""
    ingestor = JsonFileIngestor(file_path=data_path)
    analyzer = RealEstateAnalyzer()
    monday = MondayClient()

    properties = ingestor.load_properties()
    if not properties:
        logger.warning("No valid properties loaded from %s.", data_path)
        return 0

    logger.info("Loaded %d properties. Starting underwriting & reconciliation...", len(properties))
    processed = 0

    for prop in properties:
        result = analyzer.analyze_property(prop)
        if not result:
            logger.error("Underwriting skipped for %s", prop.address)
            continue

        monday.create_item(prop, result)
        processed += 1

        recon_status = (
            "CONSISTENT"
            if result.reconciliation is None or result.reconciliation.is_consistent
            else f"CONFLICT_FLAGGED ({len(result.reconciliation.discrepancies)} issue(s))"
        )
        ppsf_text = f"${result.price_per_sqft:,.2f}/sqft" if result.price_per_sqft else "N/A"

        print(
            f"[{prop.property_id}] {prop.address} | Score: {result.viability_score}/100 | "
            f"Action: {result.recommended_action.value} | Price/SqFt: {ppsf_text} | "
            f"Docs: {recon_status} | Broker: {result.assigned_broker or 'Unassigned'}"
        )
        print(f"Summary: {result.summary}")
        print("-" * 70)

    return processed


if __name__ == "__main__":
    main()
