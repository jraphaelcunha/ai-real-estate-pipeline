
from geopy.geocoders import Nominatim


def get_coordinates(address: str) -> dict[str, float] | None:
    """
    Geocodes an address string to latitude/longitude coordinates.
    Returns a dictionary compatible with Monday.com Location column (lat, lng, address).
    Returns None if geocoding fails.
    """
    try:
        # Unique user_agent as required by Nominatim
        geolocator = Nominatim(user_agent="ai_real_estate_agent_v1")
        
        # Geocode
        location = geolocator.geocode(address)
        
        if location:
            return {
                "lat": location.latitude,
                "lng": location.longitude,
                "address": address
            }
        return None
        
    except Exception as e:
        # Fail silently but could log if logger was passed
        print(f"Geocoding error for {address}: {e}")
        return None
