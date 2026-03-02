"""
Trip Recommendation Service.

Generates personalized destination recommendations based on:
- Trip destination coordinates (from DB or geocoded)
- Trip members preferences and interests
"""

import logging
import hashlib
from typing import Optional, List, Dict, Any
from collections import Counter

from apps.trips.models import Trip, TripMember
from apps.preferences.models import Preference
from .geocoder import geocode_location
from .opentripmap import opentripmap_service
from .unsplash import unsplash_service

logger = logging.getLogger(__name__)

# Default fallback image for destinations without images
DEFAULT_DESTINATION_IMAGE = 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800'

# Known city coordinates for fallback when geocoding fails
KNOWN_CITY_COORDINATES = {
    'goa': (15.2993, 74.1240),
    'mumbai': (19.0760, 72.8777),
    'delhi': (28.6139, 77.2090),
    'bangalore': (12.9716, 77.5946),
    'chennai': (13.0827, 80.2707),
    'kolkata': (22.5726, 88.3639),
    'jaipur': (26.9124, 75.7873),
    'udaipur': (24.5854, 73.7125),
    'kerala': (10.8505, 76.2711),
    'manali': (32.2396, 77.1887),
    'shimla': (31.1048, 77.1734),
    'varanasi': (25.3176, 82.9739),
    'agra': (27.1767, 78.0081),
    'paris': (48.8566, 2.3522),
    'london': (51.5074, -0.1278),
    'new york': (40.7128, -74.0060),
    'tokyo': (35.6762, 139.6503),
    'dubai': (25.2048, 55.2708),
    'singapore': (1.3521, 103.8198),
    'bangkok': (13.7563, 100.5018),
    'bali': (-8.3405, 115.0920),
    'rome': (41.9028, 12.4964),
    'barcelona': (41.3851, 2.1734),
}


CATEGORY_TO_KINDS = {
    'nature': 'natural',
    'adventure': 'sport',
    'culture': 'cultural,historic',
    'gastronomy': 'foods',
    'all': None,
}

INTEREST_TO_KINDS = {
    'adventure': 'sport',
    'hiking': 'natural,sport',
    'sports': 'sport',
    'water sports': 'sport,beaches',
    'nature': 'natural',
    'beaches': 'beaches,natural',
    'mountains': 'natural',
    'wildlife': 'natural',
    'culture': 'cultural,historic',
    'history': 'historic,cultural',
    'architecture': 'architecture,cultural',
    'museums': 'museums,cultural',
    'art': 'cultural,museums',
    'food': 'foods',
    'gastronomy': 'foods',
    'nightlife': 'amusements',
    'shopping': 'shops',
    'relaxation': 'natural,beaches',
    'photography': 'natural,architecture,cultural',
}

CATEGORY_FALLBACK_IMAGES = {
    'nature': [
        'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800',
        'https://images.unsplash.com/photo-1511593358241-7eea1f3c84e5?w=800',
        'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800',
    ],
    'adventure': [
        'https://images.unsplash.com/photo-1551632811-561732d1e306?w=800',
        'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800',
    ],
    'culture': [
        'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800',
        'https://images.unsplash.com/photo-1533929736458-ca588d08c8be?w=800',
    ],
    'food': [
        'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800',
        'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800',
    ],
    'leisure': [
        'https://images.unsplash.com/photo-1540541338287-41700207dee6?w=800',
        'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800',
    ],
}


class TripRecommender:
    """
    Service class for generating trip-based destination recommendations.
    """
    
    def __init__(self, trip: Trip):
        self.trip = trip
        self.members_data: List[Dict] = []
        
    def _ensure_coordinates(self) -> bool:
        """
        Ensure trip has coordinates. Geocode if missing and save to DB.
        Uses fallback coordinates for known cities if geocoding fails.
        
        Returns:
            True if coordinates available, False otherwise
        """
        # DEBUG: Log trip info
        print(f"[DEBUG] Trip ID: {self.trip.id}")
        print(f"[DEBUG] Trip City: {self.trip.city}")
        print(f"[DEBUG] Trip Country: {self.trip.country}")
        print(f"[DEBUG] Existing Coordinates: ({self.trip.latitude}, {self.trip.longitude})")
        
        if self.trip.latitude and self.trip.longitude:
            print(f"[DEBUG] Using existing coordinates: ({self.trip.latitude}, {self.trip.longitude})")
            return True
        
        # Try geocoding first
        lat, lon = geocode_location(
            city=self.trip.city,
            region=self.trip.region,
            country=self.trip.country
        )
        
        # FALLBACK: Use known city coordinates if geocoding fails
        if lat is None or lon is None:
            city_lower = (self.trip.city or '').lower().strip()
            print(f"[DEBUG] Geocoding failed, checking fallback for: '{city_lower}'")
            
            if city_lower in KNOWN_CITY_COORDINATES:
                lat, lon = KNOWN_CITY_COORDINATES[city_lower]
                print(f"[DEBUG] Using fallback coordinates for {city_lower}: ({lat}, {lon})")
            else:
                # Try partial match
                for known_city, coords in KNOWN_CITY_COORDINATES.items():
                    if known_city in city_lower or city_lower in known_city:
                        lat, lon = coords
                        print(f"[DEBUG] Using partial match fallback for {known_city}: ({lat}, {lon})")
                        break
        
        if lat is None or lon is None:
            logger.warning(f"Could not geocode trip {self.trip.id}: {self.trip.city}, {self.trip.country}")
            print(f"[DEBUG] FAILED to get coordinates for: {self.trip.city}")
            return False
        
        self.trip.latitude = lat
        self.trip.longitude = lon
        self.trip.save(update_fields=['latitude', 'longitude'])
        logger.info(f"Saved coordinates for trip {self.trip.id}: ({lat}, {lon})")
        print(f"[DEBUG] Saved coordinates: ({lat}, {lon})")
        return True
    
    def _load_members_data(self) -> None:
        """Load preferences and interests for all accepted trip members."""
        members = TripMember.objects.filter(
            trip=self.trip,
            status=TripMember.MembershipStatus.ACCEPTED
        ).select_related('user')
        
        for member in members:
            try:
                preference = Preference.objects.prefetch_related('interests').get(
                    user=member.user
                )
                self.members_data.append({
                    'user_id': member.user.id,
                    'budget_range': preference.budget_range,
                    'travel_style': preference.travel_style,
                    'interests': list(preference.interests.values_list('name', flat=True)),
                })
            except Preference.DoesNotExist:
                self.members_data.append({
                    'user_id': member.user.id,
                    'budget_range': None,
                    'travel_style': None,
                    'interests': [],
                })
    
    def _get_dominant_interests(self) -> List[str]:
        """Get interests sorted by frequency across all members."""
        all_interests = []
        for member in self.members_data:
            all_interests.extend(member.get('interests', []))
        
        if not all_interests:
            return []
        
        interest_counts = Counter(all_interests)
        return [interest for interest, _ in interest_counts.most_common()]
    
    def _map_interests_to_kinds(self, interests: List[str]) -> Optional[str]:
        """Map user interests to OpenTripMap kinds."""
        if not interests:
            return None
        
        kinds_set = set()
        for interest in interests[:5]:
            interest_lower = interest.lower()
            if interest_lower in INTEREST_TO_KINDS:
                kinds_set.update(INTEREST_TO_KINDS[interest_lower].split(','))
        
        if not kinds_set:
            return None
        
        return ','.join(list(kinds_set)[:8])
    
    def _categorize_place(self, kinds_str: str) -> str:
        """Categorize a place based on its kinds."""
        kinds_lower = kinds_str.lower()
        
        if any(k in kinds_lower for k in ['natural', 'beach', 'mountain', 'park']):
            return 'nature'
        if any(k in kinds_lower for k in ['sport', 'climbing', 'diving']):
            return 'adventure'
        if any(k in kinds_lower for k in ['cultural', 'historic', 'museum', 'architecture']):
            return 'culture'
        if any(k in kinds_lower for k in ['food', 'restaurant', 'cafe']):
            return 'food'
        
        return 'culture'
    
    def _format_place(self, place: Dict, details: Optional[Dict] = None) -> Dict[str, Any]:
        """Format a place into the expected response format with intelligent image resolution."""
        merged = {**place}
        if details:
            merged.update(details)
        
        # Extract place information - try multiple sources for name
        place_name = merged.get('name', '')
        
        # If no name, try to generate one from kinds
        if not place_name:
            kinds = merged.get('kinds', '')
            if kinds:
                # Generate a readable name from kinds (e.g., "stadiums" -> "Stadium")
                kind_parts = kinds.split(',')
                for part in kind_parts:
                    part = part.strip()
                    if part and part not in ['sport', 'other']:
                        place_name = part.replace('_', ' ').title()
                        print(f"[DEBUG] Generated name from kinds: {place_name}")
                        break
        
        # If still no name, use location-based name
        if not place_name:
            place_name = f"Place near {self.trip.city}"
            print(f"[DEBUG] Using default name: {place_name}")
        
        city = self.trip.city or ''
        country = self.trip.country or ''
        
        print(f"[DEBUG] _format_place: name='{place_name}', xid={merged.get('xid', 'N/A')}")
        
        # Determine category
        category = self._categorize_place(merged.get('kinds', ''))
        
        # Initialize image and source
        image = None
        image_source = 'fallback'
        
        # STEP 1: Try OpenTripMap enriched image
        if merged.get('image'):
            image = merged['image']
            image_source = 'opentripmap'
            print(f"[DEBUG] Got OpenTripMap image: {image[:50]}...")
        elif merged.get('preview'):
            image = merged['preview'].get('source', '')
            if image:
                image_source = 'opentripmap'
                print(f"[DEBUG] Got OpenTripMap preview: {image[:50]}...")
        
        # STEP 2: If no OpenTripMap image, use Unsplash with intelligent fallback
        if not image:
            print(f"[DEBUG] No OTM image, trying Unsplash for '{place_name}'...")
            try:
                image, image_source = unsplash_service.get_place_image_with_fallback(
                    place_name=place_name,
                    city=city,
                    country=country,
                    category=category
                )
                if image:
                    print(f"[DEBUG] Got Unsplash image: {image[:50]}... (source={image_source})")
                else:
                    print(f"[DEBUG] Unsplash returned no image")
            except Exception as e:
                print(f"[DEBUG] Unsplash error: {str(e)}")
        
        # STEP 3: Final safety fallback (should rarely happen now)
        if not image:
            print(f"[DEBUG] Using fallback image for category: {category}")
            fallback_images = CATEGORY_FALLBACK_IMAGES.get(category, CATEGORY_FALLBACK_IMAGES['culture'])
            if isinstance(fallback_images, list):
                # Rotate images based on place name for variety
                hash_obj = hashlib.md5(place_name.encode())
                index = int(hash_obj.hexdigest(), 16) % len(fallback_images)
                image = fallback_images[index]
            else:
                image = fallback_images
            image_source = 'fallback'
            print(f"[DEBUG] Fallback image: {image[:50]}...")
        
        # Extract description
        description = merged.get('description', '')
        if not description and merged.get('wikipedia_extracts'):
            description = merged['wikipedia_extracts'].get('text', '')[:300]
        
        # Extract coordinates
        point = merged.get('point', {})
        lat = point.get('lat') or merged.get('lat', 0)
        lon = point.get('lon') or merged.get('lon', 0)
        
        return {
            'xid': merged.get('xid', ''),
            'name': place_name or 'Unknown Place',
            'city': city,
            'image': image,
            'image_source': image_source,  # Track where image came from
            'short_description': description,
            'category': category,
            'lat': lat,
            'lon': lon,
            'kinds': merged.get('kinds', ''),
            'wikipedia': merged.get('wikipedia', ''),
            'address': merged.get('address', {}),
        }
    
    def recommend(
        self,
        category: Optional[str] = None,
        radius: int = 50000,  # Increased default radius to 50km
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations for the trip.
        
        Args:
            category: Optional category filter ('nature', 'adventure', 'culture', 'gastronomy')
            radius: Search radius in meters (default 50km)
            limit: Maximum number of results
            
        Returns:
            List of recommendation dictionaries
        """
        print(f"[DEBUG] recommend() called - category={category}, radius={radius}, limit={limit}")
        
        if not self._ensure_coordinates():
            print("[DEBUG] _ensure_coordinates() returned False - no coordinates available")
            return []
        
        print(f"[DEBUG] Trip coordinates: ({self.trip.latitude}, {self.trip.longitude})")
        
        self._load_members_data()
        
        if category and category in CATEGORY_TO_KINDS:
            kinds = CATEGORY_TO_KINDS[category]
        else:
            interests = self._get_dominant_interests()
            kinds = self._map_interests_to_kinds(interests)
            logger.info(f"Trip {self.trip.id} interests: {interests}, kinds: {kinds}")
        
        print(f"[DEBUG] Searching with kinds={kinds}")
        
        # Try OpenTripMap first with kinds filter
        places = opentripmap_service.get_places_by_radius(
            lat=self.trip.latitude,
            lon=self.trip.longitude,
            kinds=kinds,
            radius=radius,
            limit=limit * 2
        )
        print(f"[DEBUG] OpenTripMap with kinds returned {len(places) if places else 0} places")
        
        # FALLBACK 1: Try without kinds filter (get any interesting places)
        if not places:
            print("[DEBUG] Trying OpenTripMap without kinds filter...")
            places = opentripmap_service.get_places_by_radius(
                lat=self.trip.latitude,
                lon=self.trip.longitude,
                kinds=None,  # No filter - get any POIs
                radius=radius,
                limit=limit * 2
            )
            print(f"[DEBUG] OpenTripMap without kinds returned {len(places) if places else 0} places")
        
        # FALLBACK 2: Try Overpass API if OpenTripMap returns nothing
        if not places:
            print("[DEBUG] Trying Overpass API...")
            places = opentripmap_service.get_places_from_overpass(
                lat=self.trip.latitude,
                lon=self.trip.longitude,
                radius=radius,
                limit=limit * 2
            )
            print(f"[DEBUG] Overpass API returned {len(places) if places else 0} places")
        
        if not places:
            print("[DEBUG] All APIs returned no places - returning empty list")
            return []
        
        # Enrich places with details (images and descriptions) for first 12 results
        print(f"[DEBUG] Enriching {len(places)} places with details...")
        enriched_places = opentripmap_service.get_places_with_details(
            places=places,
            max_details=12
        )
        print(f"[DEBUG] After enrichment: {len(enriched_places)} places")
        
        recommendations = []
        seen_xids = set()
        
        for place in enriched_places:
            if len(recommendations) >= limit:
                break
            
            xid = place.get('xid')
            if not xid or xid in seen_xids:
                continue
            
            seen_xids.add(xid)
            
            # Use enriched data (includes image and description)
            details = place.get('details')
            formatted = self._format_place(place, details)
            
            # Skip category filtering for now - return all results
            # if category and category != 'all':
            #     if formatted['category'] != category:
            #         continue
            
            recommendations.append(formatted)
        
        print(f"[DEBUG] Final recommendations count: {len(recommendations)}")
        if recommendations:
            print(f"[DEBUG] First recommendation: {recommendations[0].get('name', 'unknown')}")
        
        return recommendations
    
    def get_group_analysis(self) -> Dict[str, Any]:
        """Get analysis of the group's preferences."""
        self._load_members_data()
        
        interests = self._get_dominant_interests()
        budgets = [m['budget_range'] for m in self.members_data if m['budget_range']]
        styles = [m['travel_style'] for m in self.members_data if m['travel_style']]
        
        budget_counts = Counter(budgets)
        style_counts = Counter(styles)
        
        return {
            'member_count': len(self.members_data),
            'dominant_interests': interests[:5],
            'budget_distribution': dict(budget_counts),
            'dominant_budget': budget_counts.most_common(1)[0][0] if budget_counts else None,
            'style_distribution': dict(style_counts),
            'dominant_style': style_counts.most_common(1)[0][0] if style_counts else None,
        }


def recommend_for_trip(
    trip: Trip,
    category: Optional[str] = None,
    limit: int = 30
) -> List[Dict[str, Any]]:
    """
    Convenience function to get recommendations for a trip.
    
    Args:
        trip: Trip model instance
        category: Optional category filter
        limit: Maximum number of results
        
    Returns:
        List of recommendation dictionaries
    """
    recommender = TripRecommender(trip)
    return recommender.recommend(category=category, limit=limit)


def get_group_analysis(trip: Trip) -> Dict[str, Any]:
    """
    Convenience function to get group analysis for a trip.
    
    Args:
        trip: Trip model instance
        
    Returns:
        Dictionary with group preference analysis
    """
    recommender = TripRecommender(trip)
    return recommender.get_group_analysis()
