"""Modular Playwright Chromium listing collector with structured fixture fallback."""

import re
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from src.domain.schemas import PropertyInput
from src.services.ingestor import JsonFileIngestor
from src.services.interfaces import DataIngestor
from src.utils.logger import get_logger

logger = get_logger("playwright_collector")
PRICE_PATTERN = re.compile(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{2})?)")


def extract_price_from_text(text: str) -> Decimal | None:
    """Extract the first positive USD listing price from unstructured page text."""
    match = PRICE_PATTERN.search(text)
    if not match:
        return None
    try:
        value = Decimal(match.group(1).replace(",", ""))
        return value if value > 0 else None
    except ArithmeticError:
        return None


def normalize_listing_payload(raw_payload: dict[str, Any]) -> PropertyInput | None:
    """Normalize raw scraped dictionary payloads into validated PropertyInput contracts."""
    try:
        cleaned = dict(raw_payload)
        if isinstance(cleaned.get("price"), str):
            numeric_str = (
                cleaned["price"].replace("$", "").replace(",", "").strip()
            )
            cleaned["price"] = Decimal(numeric_str)
        return PropertyInput(**cleaned)
    except (ValidationError, ArithmeticError, ValueError) as exc:
        logger.warning("Failed to normalize listing payload: %s", exc)
        return None


class PlaywrightListingCollector(DataIngestor):
    """
    Collects property listing details and deal links using headless Chromium.
    Falls back cleanly to structured local deal feeds when running offline or in CI.
    """

    def __init__(
        self,
        target_urls: list[str] | None = None,
        fallback_feed_path: str = "data/raw_mock_data.json",
    ) -> None:
        self.target_urls = target_urls or []
        self.fallback_feed_path = fallback_feed_path

    def load_properties(self) -> list[PropertyInput]:
        """Collect properties from target URLs or fall back to structured feed."""
        if not self.target_urls:
            logger.info(
                "No live target URLs configured; loading structured deal feed from %s",
                self.fallback_feed_path,
            )
            return JsonFileIngestor(self.fallback_feed_path).load_properties()

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning(
                "Playwright package unavailable in current environment; falling back to %s",
                self.fallback_feed_path,
            )
            return JsonFileIngestor(self.fallback_feed_path).load_properties()

        collected: list[PropertyInput] = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                    )
                )
                page = context.new_page()
                for idx, url in enumerate(self.target_urls, start=1):
                    raw = self._extract_page(page, url, idx)
                    if raw:
                        prop = normalize_listing_payload(raw)
                        if prop:
                            collected.append(prop)
                context.close()
                browser.close()
        except Exception as exc:
            logger.warning(
                "Playwright execution degraded (%s); falling back to structured feed %s",
                exc,
                self.fallback_feed_path,
            )
            return JsonFileIngestor(self.fallback_feed_path).load_properties()

        return collected

    def _extract_page(self, page: Any, url: str, index: int) -> dict[str, Any] | None:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            title = (page.title() or "").strip()
            body_text = (page.locator("body").inner_text(timeout=5000) or "").strip()
            extracted_price = extract_price_from_text(f"{title} {body_text}")
            if extracted_price is None:
                logger.warning("No valid listing price found on %s; skipping page.", url)
                return None
            return {
                "property_id": f"LIVE-{index:03d}",
                "address": title or "Pending Address Extraction",
                "price": extracted_price,
                "raw_description": body_text[:1500],
                "link": url,
            }
        except Exception as exc:
            logger.warning("Skipping unreachable listing URL %s: %s", url, exc)
            return None
