"""Unit tests for Geopy/Nominatim GIS routing and Playwright listing normalization."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from geopy.exc import GeocoderTimedOut

from src.services.scraper import (
    PlaywrightListingCollector,
    extract_price_from_text,
    normalize_listing_payload,
)
from src.utils.geocoder import assign_nearest_broker, get_coordinates, haversine_distance_km


def test_haversine_distance_and_nearest_broker_dallas():
    broker_name, dist_km = assign_nearest_broker(32.80, -96.77)
    assert "Dallas" in broker_name or "DFW" in broker_name
    assert dist_km < 10.0


def test_haversine_same_point_is_zero():
    assert haversine_distance_km(32.7767, -96.7970, 32.7767, -96.7970) == 0.0


def test_get_coordinates_uses_metro_fallback_on_timeout():
    with patch("src.utils.geocoder.Nominatim") as mock_nominatim:
        mock_geo = MagicMock()
        mock_geo.geocode.side_effect = GeocoderTimedOut("Rate limit timeout")
        mock_nominatim.return_value = mock_geo

        coords = get_coordinates("4510 Swiss Ave, Dallas, TX")
        assert coords is not None
        assert coords["lat"] == 32.7767
        assert coords["lng"] == -96.7970


def test_normalize_listing_payload_parses_currency_strings():
    prop = normalize_listing_payload(
        {
            "property_id": "SCRAPE-01",
            "address": "100 Main St, Austin, TX",
            "price": "$425,000.00",
            "raw_description": "Turnkey duplex.",
            "link": "https://portal.reference-cre.example/listings/scrape-01",
        }
    )
    assert prop is not None
    assert prop.price == Decimal("425000.00")


def test_playwright_collector_falls_back_to_structured_feed():
    collector = PlaywrightListingCollector(
        target_urls=[],
        fallback_feed_path="data/raw_mock_data.json",
    )
    properties = collector.load_properties()
    assert len(properties) >= 1


def test_playwright_extract_page_parses_positive_price_and_normalizes():
    collector = PlaywrightListingCollector()
    mock_page = MagicMock()
    mock_page.title.return_value = "210 Oak St, Dallas, TX"
    mock_page.locator.return_value.inner_text.return_value = (
        "Turnkey 4-plex listed at $685,000.00 with strong cash flow."
    )

    raw = collector._extract_page(
        mock_page, "https://portal.reference-cre.example/listings/live-1", 1
    )
    assert raw is not None
    assert raw["price"] == Decimal("685000.00")

    prop = normalize_listing_payload(raw)
    assert prop is not None
    assert prop.property_id == "LIVE-001"
    assert prop.price == Decimal("685000.00")


def test_extract_price_from_text_returns_none_when_missing():
    assert extract_price_from_text("Call broker for pricing details") is None
