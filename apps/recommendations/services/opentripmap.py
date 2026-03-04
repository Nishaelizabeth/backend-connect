"""
OpenTripMap API Service Layer.

Handles POI (Points of Interest) searches using the OpenTripMap radius endpoint.
Geocoding is handled separately by the geocoder service.
"""

import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any
from django.conf import settings
from django.core.cache import cache
from datetime import timedelta

logger = logging.getLogger(__name__)

OPENTRIPMAP_BASE_URL = "https://api.opentripmap.com/0.1/en/places"
REQUEST_TIMEOUT = 3  # Reduced from 10s to fail fast
DETAILS_CACHE_TIMEOUT = 600  # 10 minutes


class OpenTripMapService:
    """
    Service class for fetching POIs from OpenTripMap.
    
    Only uses the radius endpoint for searching places near coordinates.
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENTRIPMAP_API_KEY', '')
        self.base_url = OPENTRIPMAP_BASE_URL
        
    def get_places_by_radius(
        self,
        lat: float,
        lon: float,
        kinds: Optional[str] = None,
        radius: int = 30000,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get places within a radius of given coordinates.
        
        Args:
            lat: Latitude of center point
            lon: Longitude of center point
            kinds: Comma-separated category filters (e.g., 'cultural,natural')
            radius: Search radius in meters (default 30km)
            limit: Maximum number of results
            
        Returns:
            List of place dictionaries with basic info
        """
        if not self.api_key:
            logger.error("OPENTRIPMAP_API_KEY not configured")
            print("[DEBUG] OPENTRIPMAP_API_KEY not configured!")
            return []
        
        params = {
            'apikey': self.api_key,
            'lat': lat,
            'lon': lon,
            'radius': radius,
            'limit': limit,
            'format': 'json',
        }
        
        if kinds:
            params['kinds'] = kinds
        
        try:
            url = f"{self.base_url}/radius"
            print(f"[DEBUG] OpenTripMap API call: {url}, lat={lat}, lon={lon}, radius={radius}, kinds={kinds}")
            logger.info(f"OpenTripMap request: {url} with params lat={lat}, lon={lon}, radius={radius}")
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            print(f"[DEBUG] OpenTripMap status code: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            
            print(f"[DEBUG] OpenTripMap raw response type: {type(result)}, length: {len(result) if isinstance(result, (list, dict)) else 'N/A'}")
            logger.info(f"OpenTripMap response type: {type(result)}, content: {str(result)[:200]}")
            
            if isinstance(result, list):
                # Require both xid AND a meaningful name (≥3 chars)
                places = [
                    place for place in result
                    if place.get('xid') and place.get('name', '').strip() and len(place.get('name', '').strip()) >= 3
                ]
                print(f"[DEBUG] Total places from API: {len(result)}, After filter (xid+name): {len(places)}")
                if result and len(result) > 0:
                    print(f"[DEBUG] First raw place example: {result[0]}")
                logger.info(f"Found {len(places)} named places near ({lat}, {lon})")
                return places
            elif isinstance(result, dict):
                # API might return error as dict
                if result.get('error') or result.get('status') == 'NOT_FOUND':
                    logger.warning(f"OpenTripMap error: {result}")
                # Empty dict means no results
                logger.info(f"No places found near ({lat}, {lon})")
            
            return []
            
        except requests.exceptions.Timeout:
            logger.error(f"OpenTripMap timeout for radius search at ({lat}, {lon})")
            print(f"[DEBUG] OpenTripMap TIMEOUT at ({lat}, {lon})")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenTripMap request error: {str(e)}")
            print(f"[DEBUG] OpenTripMap REQUEST ERROR: {str(e)}")
            return []
        except ValueError as e:
            logger.error(f"OpenTripMap JSON parse error: {str(e)}")
            print(f"[DEBUG] OpenTripMap JSON PARSE ERROR: {str(e)}")
            return []
    
    def get_place_details(self, xid: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific place with caching.
        
        Args:
            xid: The unique identifier for the place in OpenTripMap
            
        Returns:
            Dictionary with detailed place information (empty dict on error)
        """
        if not self.api_key:
            print(f"[DEBUG] get_place_details: OPENTRIPMAP_API_KEY not configured!")
            logger.error("OPENTRIPMAP_API_KEY not configured")
            return {}
        
        # Check cache first
        cache_key = f"opentripmap_details_{xid}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            print(f"[DEBUG] get_place_details: Cache HIT for {xid}")
            logger.debug(f"Cache hit for place details: {xid}")
            return cached_result
        
        try:
            url = f"{self.base_url}/xid/{xid}"
            params = {'apikey': self.api_key}
            
            print(f"[DEBUG] get_place_details: Fetching {xid}...")
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            print(f"[DEBUG] get_place_details: Status {response.status_code} for {xid}")
            response.raise_for_status()
            result = response.json()
            
            if result and result.get('xid'):
                # Cache the successful result
                cache.set(cache_key, result, DETAILS_CACHE_TIMEOUT)
                print(f"[DEBUG] get_place_details: Got name='{result.get('name', '')}' for {xid}")
                return result
            
            print(f"[DEBUG] get_place_details: Empty/invalid result for {xid}")
            # Cache empty result to avoid repeated failures
            cache.set(cache_key, {}, DETAILS_CACHE_TIMEOUT)
            return {}
            
        except requests.exceptions.Timeout:
            print(f"[DEBUG] get_place_details: TIMEOUT for {xid}")
            logger.warning(f"OpenTripMap timeout for place details: {xid}")
            cache.set(cache_key, {}, 60)  # Cache failure for 1 minute
            return {}
        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] get_place_details: REQUEST ERROR for {xid}: {str(e)}")
            logger.warning(f"OpenTripMap request error for {xid}: {str(e)}")
            cache.set(cache_key, {}, 60)
            return {}
        except ValueError as e:
            print(f"[DEBUG] get_place_details: JSON ERROR for {xid}: {str(e)}")
            logger.warning(f"OpenTripMap JSON parse error for {xid}: {str(e)}")
            cache.set(cache_key, {}, 60)
            return {}
    
    def _enrich_single_place(self, index: int, place: Dict[str, Any]) -> tuple:
        """
        Fetch and enrich a single place with details.
        Returns (index, enriched_place) tuple to allow ordered reassembly.
        """
        xid = place.get('xid', '')
        original_name = place.get('name', '')

        if not xid or xid.startswith('osm_'):
            return index, {
                **place,
                'image': None,
                'description': '',
            }

        details = self.get_place_details(xid)
        image = None
        description = ''
        name = original_name

        if details:
            if not name and details.get('name'):
                name = details['name']
            if details.get('preview') and details['preview'].get('source'):
                image = details['preview']['source']
            elif details.get('image'):
                image = details['image']
            if details.get('wikipedia_extracts') and details['wikipedia_extracts'].get('text'):
                description = details['wikipedia_extracts']['text']

        return index, {
            **place,
            'name': name,
            'image': image,
            'description': description,
            'details': details,
        }

    def get_places_with_details(self, places: List[Dict[str, Any]], max_details: int = 12) -> List[Dict[str, Any]]:
        """
        Enrich a list of places with detailed information (images and descriptions).
        Detail fetches for the first `max_details` places are done in parallel.

        Args:
            places: List of basic place dictionaries from radius search
            max_details: Maximum number of places to enrich with details

        Returns:
            List of enriched place dictionaries (same order as input)
        """
        print(f"[DEBUG] get_places_with_details: Enriching {len(places)} places (max_details={max_details})")

        # Split into places that need detail calls vs those that don't
        detail_places = places[:max_details]
        skip_places = places[max_details:]

        # Fetch details for the first batch IN PARALLEL
        results: Dict[int, Dict] = {}
        with ThreadPoolExecutor(max_workers=min(max_details, 8)) as executor:
            futures = {
                executor.submit(self._enrich_single_place, i, place): i
                for i, place in enumerate(detail_places)
            }
            for future in as_completed(futures):
                try:
                    idx, enriched = future.result()
                    results[idx] = enriched
                except Exception as e:
                    orig_idx = futures[future]
                    print(f"[DEBUG] Place {orig_idx}: parallel fetch error: {e}")
                    results[orig_idx] = {
                        **detail_places[orig_idx],
                        'image': None,
                        'description': '',
                    }

        # Reassemble in original order
        enriched_places = [results[i] for i in range(len(detail_places))]

        # Append skipped places (no detail call needed)
        for place in skip_places:
            enriched_places.append({
                **place,
                'image': None,
                'description': '',
            })

        places_with_names = [p for p in enriched_places if p.get('name')]
        print(f"[DEBUG] Enrichment complete: {len(enriched_places)} total, {len(places_with_names)} with names")
        logger.info(f"Enriched {len(detail_places)} places with details (parallel)")
        return enriched_places
    
    def get_places_from_overpass(
        self,
        lat: float,
        lon: float,
        radius: int = 30000,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Fallback: Get places from Overpass API (OpenStreetMap).
        No API key required.
        """
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        # Query for tourism and historic places
        query = f"""
        [out:json][timeout:25];
        (
          node["tourism"](around:{radius},{lat},{lon});
          node["historic"](around:{radius},{lat},{lon});
          node["leisure"="park"](around:{radius},{lat},{lon});
          node["amenity"~"restaurant|cafe|museum"](around:{radius},{lat},{lon});
        );
        out body {limit};
        """
        
        try:
            response = requests.post(
                overpass_url,
                data={'data': query},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            places = []
            for element in data.get('elements', []):
                tags = element.get('tags', {})
                name = tags.get('name')
                if not name:
                    continue
                
                # Determine category
                kinds = []
                if tags.get('tourism'):
                    kinds.append(tags['tourism'])
                if tags.get('historic'):
                    kinds.append('historic')
                if tags.get('leisure'):
                    kinds.append(tags['leisure'])
                if tags.get('amenity'):
                    kinds.append(tags['amenity'])
                
                places.append({
                    'xid': f"osm_{element.get('id')}",
                    'name': name,
                    'lat': element.get('lat'),
                    'lon': element.get('lon'),
                    'kinds': ','.join(kinds),
                    'osm_id': element.get('id'),
                })
            
            logger.info(f"Overpass found {len(places)} places near ({lat}, {lon})")
            return places[:limit]
            
        except Exception as e:
            logger.error(f"Overpass API error: {str(e)}")
            return []


opentripmap_service = OpenTripMapService()
