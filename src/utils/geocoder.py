"""Geospatial resolution and Haversine nearest-broker routing utilities."""

import math
from dataclasses import dataclass

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

from src.utils.logger import get_logger

logger = get_logger("geocoder")


@dataclass(frozen=True)
class FieldBroker:
    """Represents a regional acquisitions broker for automated GIS territory dispatch."""

    name: str
    market: str
    lat: float
    lng: float


ACTIVE_FIELD_BROKERS: tuple[FieldBroker, ...] = (
    FieldBroker("Elena Vance (DFW Multifamily)", "Dallas-Fort Worth, TX", 32.7767, -96.7970),
    FieldBroker("Marcus Sterling (Central TX)", "Austin, TX", 30.2672, -97.7431),
    FieldBroker("Claire Bennett (PNW)", "Seattle, WA", 47.6062, -122.3321),
    FieldBroker("Carlos Mendez (South FL)", "Miami, FL", 25.7617, -80.1918),
    FieldBroker("Devon Brooks (Midwest)", "Detroit / Cleveland", 41.9000, -82.3500),
    FieldBroker("Sophia Lin (SoCal)", "Los Angeles, CA", 34.0522, -118.2437),
    FieldBroker("Liam O'Connor (Northeast)", "Boston / Newark", 41.5500, -72.6000),
)

METRO_CENTROID_FALLBACKS: dict[str, tuple[float, float]] = {
    "dallas": (32.7767, -96.7970),
    "austin": (30.2672, -97.7431),
    "seattle": (47.6062, -122.3321),
    "miami": (25.7617, -80.1918),
    "detroit": (42.3314, -83.0458),
    "los angeles": (34.0522, -118.2437),
    "cleveland": (41.4993, -81.6944),
    "boston": (42.3601, -71.0589),
    "newark": (40.7357, -74.1724),
}


def haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate great-circle distance in kilometers between two WGS84 coordinates."""
    earth_radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(earth_radius_km * c, 2)


def assign_nearest_broker(lat: float, lng: float) -> tuple[str, float]:
    """Select the closest regional field broker using Haversine distance."""
    nearest = min(
        ACTIVE_FIELD_BROKERS,
        key=lambda broker: haversine_distance_km(lat, lng, broker.lat, broker.lng),
    )
    distance = haversine_distance_km(lat, lng, nearest.lat, nearest.lng)
    return nearest.name, distance


def _fallback_metro_coordinates(address: str) -> dict[str, float | str] | None:
    lowered = address.lower()
    for city, (lat, lng) in METRO_CENTROID_FALLBACKS.items():
        if city in lowered:
            return {"lat": lat, "lng": lng, "address": address}
    return None


def get_coordinates(address: str, timeout: int = 5) -> dict[str, float | str] | None:
    """
    Geocodes an address string to latitude/longitude coordinates via Nominatim GIS.
    Gracefully falls back to metro centroids if Nominatim is rate-limited or offline.
    """
    try:
        geolocator = Nominatim(user_agent="ai_real_estate_pipeline_v2", timeout=timeout)
        location = geolocator.geocode(address)

        if location:
            return {
                "lat": location.latitude,
                "lng": location.longitude,
                "address": address,
            }
        return _fallback_metro_coordinates(address)

    except (GeocoderTimedOut, GeocoderServiceError) as exc:
        logger.warning(
            "Nominatim geocoder unavailable/rate-limited for %s (%s). Using metro fallback.",
            address,
            exc,
        )
        return _fallback_metro_coordinates(address)
    except Exception as exc:
        logger.warning("Unexpected geocoding error for %s: %s", address, exc)
        return _fallback_metro_coordinates(address)
