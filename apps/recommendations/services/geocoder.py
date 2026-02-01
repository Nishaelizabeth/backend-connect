"""
Geocoder Service using Nominatim (OpenStreetMap).

Provides reliable geocoding for city/region/country combinations.
"""

import logging
import requests
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org/search"
REQUEST_TIMEOUT = 10


def geocode_location(
    city: str,
    region: Optional[str] = None,
    country: Optional[str] = None
) -> Tuple[Optional[float], Optional[float]]:
    """
    Geocode a location using Nominatim.
    
    Args:
        city: City name (required)
        region: Region/state name (optional)
        country: Country name (optional)
        
    Returns:
        Tuple of (latitude, longitude) or (None, None) if not found
    """
    if not city:
        logger.warning("Geocode called with empty city")
        return (None, None)
    
    # Build query string
    query_parts = [city]
    if region:
        query_parts.append(region)
    if country:
        query_parts.append(country)
    
    query = ", ".join(query_parts)
    
    try:
        params = {
            'q': query,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1,
        }
        headers = {
            'User-Agent': 'TravelBuddyApp/1.0 (https://github.com/travel-buddy; contact@travelbuddy.local)',
            'Accept-Language': 'en',
        }
        
        response = requests.get(
            NOMINATIM_BASE_URL,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        results = response.json()
        
        if results and len(results) > 0:
            result = results[0]
            lat = float(result['lat'])
            lon = float(result['lon'])
            logger.info(f"Geocoded '{query}' to ({lat}, {lon})")
            return (lat, lon)
        
        logger.warning(f"No geocoding results for: {query}")
        return (None, None)
        
    except requests.exceptions.Timeout:
        logger.error(f"Geocoding timeout for: {query}")
        return (None, None)
    except requests.exceptions.RequestException as e:
        logger.error(f"Geocoding request error for '{query}': {str(e)}")
        return (None, None)
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Geocoding parse error for '{query}': {str(e)}")
        return (None, None)
