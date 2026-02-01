"""
Trip Recommendation Service.

Generates personalized destination recommendations based on:
- Trip destination coordinates (from DB or geocoded)
- Trip members preferences and interests
"""

import logging
from typing import Optional, List, Dict, Any
from collections import Counter

from apps.trips.models import Trip, TripMember
from apps.preferences.models import Preference
from .geocoder import geocode_location
from .opentripmap import opentripmap_service
from .unsplash import unsplash_service

logger = logging.getLogger(__name__)


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
        
        Returns:
            True if coordinates available, False otherwise
        """
        if self.trip.latitude and self.trip.longitude:
            return True
        
        lat, lon = geocode_location(
            city=self.trip.city,
            region=self.trip.region,
            country=self.trip.country
        )
        
        if lat is None or lon is None:
            logger.warning(f"Could not geocode trip {self.trip.id}: {self.trip.city}, {self.trip.country}")
            return False
        
        self.trip.latitude = lat
        self.trip.longitude = lon
        self.trip.save(update_fields=['latitude', 'longitude'])
        logger.info(f"Saved coordinates for trip {self.trip.id}: ({lat}, {lon})")
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
        
        # Extract place information
        place_name = merged.get('name', '')
        city = self.trip.city or ''
        country = self.trip.country or ''
        
        # Determine category
        category = self._categorize_place(merged.get('kinds', ''))
        
        # Initialize image and source
        image = None
        image_source = 'fallback'
        
        # STEP 1: Try OpenTripMap enriched image
        if merged.get('image'):
            image = merged['image']
            image_source = 'opentripmap'
        elif merged.get('preview'):
            image = merged['preview'].get('source', '')
            if image:
                image_source = 'opentripmap'
        
        # STEP 2: If no OpenTripMap image, use Unsplash with intelligent fallback
        if not image and place_name:
            image, image_source = unsplash_service.get_place_image_with_fallback(
                place_name=place_name,
                city=city,
                country=country,
                category=category
            )
        
        # STEP 3: Final safety fallback (should rarely happen now)
        if not image:
            fallback_images = CATEGORY_FALLBACK_IMAGES.get(category, CATEGORY_FALLBACK_IMAGES['culture'])
            if isinstance(fallback_images, list):
                # Rotate images based on place name for variety
                import hashlib
                hash_obj = hashlib.md5(place_name.encode())
                index = int(hash_obj.hexdigest(), 16) % len(fallback_images)
                image = fallback_images[index]
            else:
                image = fallback_images
            image_source = 'fallback'
        
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
        radius: int = 30000,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations for the trip.
        
        Args:
            category: Optional category filter ('nature', 'adventure', 'culture', 'gastronomy')
            radius: Search radius in meters
            limit: Maximum number of results
            
        Returns:
            List of recommendation dictionaries
        """
        if not self._ensure_coordinates():
            return []
        
        self._load_members_data()
        
        if category and category in CATEGORY_TO_KINDS:
            kinds = CATEGORY_TO_KINDS[category]
        else:
            interests = self._get_dominant_interests()
            kinds = self._map_interests_to_kinds(interests)
            logger.info(f"Trip {self.trip.id} interests: {interests}, kinds: {kinds}")
        
        # Try OpenTripMap first
        places = opentripmap_service.get_places_by_radius(
            lat=self.trip.latitude,
            lon=self.trip.longitude,
            kinds=kinds,
            radius=radius,
            limit=limit * 2
        )
        
        # Fallback to Overpass API if OpenTripMap returns nothing
        if not places:
            logger.info(f"OpenTripMap returned no results, trying Overpass API")
            places = opentripmap_service.get_places_from_overpass(
                lat=self.trip.latitude,
                lon=self.trip.longitude,
                radius=radius,
                limit=limit * 2
            )
        
        if not places:
            return []
        
        # Enrich places with details (images and descriptions) for first 12 results
        enriched_places = opentripmap_service.get_places_with_details(
            places=places,
            max_details=12
        )
        
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
            
            if category and category != 'all':
                if formatted['category'] != category:
                    continue
            
            recommendations.append(formatted)
        
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
