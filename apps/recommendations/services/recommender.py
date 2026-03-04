"""
Trip Recommendation Service.

Generates personalized destination recommendations based on:
- Trip destination coordinates (from DB or geocoded)
- Trip members preferences and interests

Quality pipeline:
1. Fetch POIs from OpenTripMap (curated kinds whitelist)
2. Strict name filtering (reject generic / empty / junk names)
3. Distance validation (within 30 km of trip centre)
4. Coordinate-based deduplication
5. Smart category mapping (Nature, Culture, Heritage, Adventure, Attraction)
6. Quality scoring (popularity + wikipedia + image)
7. Unsplash image resolution (<place> <city> travel)
8. Return top-12 scored results
"""

import logging
import math
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
DEFAULT_DESTINATION_IMAGE = ''

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

# ────────────────────────────────────────────────────────────────
# CURATED WHITELIST — only these OpenTripMap kinds are fetched
# ────────────────────────────────────────────────────────────────
ALLOWED_OTM_KINDS = {
    'tourism', 'natural', 'historic', 'architecture', 'cultural',
    'museums', 'monuments_and_memorials', 'temples', 'beaches',
    'view_points', 'national_parks', 'castles', 'churches',
    'waterfalls', 'mountain_peaks', 'gardens_and_parks',
    'archaeological_sites', 'theatres_and_entertainments',
    'bridges', 'towers', 'lighthouses', 'zoos',
    'geological_formations', 'sport', 'amusements',
    'urban_environment', 'pools',
    'interesting_places', 'other',
}

# ────────────────────────────────────────────────────────────────
# STRICT NAME REJECT LIST — any place whose name matches is dropped
# ────────────────────────────────────────────────────────────────
REJECTED_NAMES = {
    'religion', 'view points', 'culture', 'nature', 'unknown',
    'viewpoints', 'other', 'sport', 'stadiums', 'stadium',
    'historic', 'cultural', 'interesting places', 'water',
    'geological formations', 'burial places', 'cemeteries',
    'churches', 'monuments', 'architecture', 'museums',
    'amusements', 'foods', 'shops', 'natural', 'beaches',
    'industrial facilities', 'fortifications',
}

# ────────────────────────────────────────────────────────────────
# CATEGORY MAPPING — deterministic rules, no inference from kinds
# ────────────────────────────────────────────────────────────────
# Priority-ordered: first matching rule wins.
CATEGORY_RULES: List[tuple] = [
    # Nature
    (['natural', 'beach', 'mountain', 'waterfall', 'lake', 'river',
      'national_park', 'gardens_and_parks', 'geological_formation',
      'pools', 'island', 'forests', 'nature_reserves'], 'Nature'),
    # Culture
    (['temple', 'mosque', 'church', 'synagogue', 'religion',
      'museum', 'theatre', 'art_gallery', 'cultural', 'opera',
      'libraries'], 'Culture'),
    # Heritage
    (['historic', 'monument', 'castle', 'fort', 'archaeological',
      'memorial', 'ruins', 'palace', 'heritage', 'old_city'], 'Heritage'),
    # Adventure
    (['sport', 'climbing', 'diving', 'surfing', 'ski',
      'amusement', 'theme_park', 'zoo', 'aquarium',
      'adventure'], 'Adventure'),
    # Attraction (catch-all for valid tourist POIs)
]

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

# Maximum distance (km) from trip centre for a place to be valid
MAX_DISTANCE_KM = 30


# ────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────
def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in km between two points."""
    R = 6371  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _classify_category(kinds_str: str) -> str:
    """Deterministic category from OpenTripMap kinds string."""
    k = kinds_str.lower()
    for keywords, category in CATEGORY_RULES:
        if any(kw in k for kw in keywords):
            return category
    return 'Attraction'


def _is_valid_name(name: str) -> bool:
    """Return True only for real, meaningful place names."""
    if not name or len(name.strip()) < 3:
        return False
    return name.strip().lower() not in REJECTED_NAMES


def _has_allowed_kinds(kinds_str: str) -> bool:
    """Return True if the place has at least one whitelisted kind."""
    if not kinds_str:
        return False
    parts = {p.strip().lower() for p in kinds_str.split(',')}
    return bool(parts & ALLOWED_OTM_KINDS)


def _quality_score(place: Dict, has_image: bool) -> float:
    """Score a place for ranking.  Higher = better."""
    score = 0.0
    # OpenTripMap rate field (0-3 popularity) — may come back as a string
    try:
        score += int(place.get('rate', 0) or 0) * 10
    except (ValueError, TypeError):
        pass
    # Has Wikipedia → high quality signal
    if place.get('wikipedia') or place.get('wikipedia_extracts'):
        score += 20
    # Has an image already (OTM or Unsplash)
    if has_image:
        score += 15
    # Has a description
    if place.get('description') or place.get('wikipedia_extracts'):
        score += 10
    # Penalise missing name (shouldn't happen after filter, but safe)
    if not place.get('name'):
        score -= 50
    return score


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
        """
        print(f"[DEBUG] Trip ID: {self.trip.id}")
        print(f"[DEBUG] Trip City: {self.trip.city}")
        print(f"[DEBUG] Trip Country: {self.trip.country}")
        print(f"[DEBUG] Existing Coordinates: ({self.trip.latitude}, {self.trip.longitude})")
        
        if self.trip.latitude and self.trip.longitude:
            print(f"[DEBUG] Using existing coordinates: ({self.trip.latitude}, {self.trip.longitude})")
            return True
        
        lat, lon = geocode_location(
            city=self.trip.city,
            region=self.trip.region,
            country=self.trip.country
        )
        
        if lat is None or lon is None:
            city_lower = (self.trip.city or '').lower().strip()
            print(f"[DEBUG] Geocoding failed, checking fallback for: '{city_lower}'")
            
            if city_lower in KNOWN_CITY_COORDINATES:
                lat, lon = KNOWN_CITY_COORDINATES[city_lower]
            else:
                for known_city, coords in KNOWN_CITY_COORDINATES.items():
                    if known_city in city_lower or city_lower in known_city:
                        lat, lon = coords
                        break
        
        if lat is None or lon is None:
            logger.warning(f"Could not geocode trip {self.trip.id}: {self.trip.city}, {self.trip.country}")
            return False
        
        self.trip.latitude = lat
        self.trip.longitude = lon
        self.trip.save(update_fields=['latitude', 'longitude'])
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

    # ────────────────────────────────────────────────
    # FILTERING  &  DEDUP  PIPELINE
    # ────────────────────────────────────────────────
    def _filter_places(self, places: List[Dict]) -> List[Dict]:
        """Apply strict name + kind + distance filters and deduplicate."""
        trip_lat = self.trip.latitude
        trip_lon = self.trip.longitude
        filtered: List[Dict] = []
        seen_names: Dict[str, bool] = {}       # lowercase name → True
        seen_coords: List[tuple] = []           # (lat, lon) of accepted places

        for p in places:
            name = (p.get('name') or '').strip()

            # 1. Name validity
            if not _is_valid_name(name):
                continue

            # 2. Kinds whitelist
            if not _has_allowed_kinds(p.get('kinds', '')):
                continue

            # 3. Distance check
            point = p.get('point', {})
            p_lat = point.get('lat') or p.get('lat')
            p_lon = point.get('lon') or p.get('lon')
            if p_lat and p_lon and trip_lat and trip_lon:
                dist = _haversine_km(trip_lat, trip_lon, p_lat, p_lon)
                if dist > MAX_DISTANCE_KM:
                    continue
            
            # 4. Deduplicate by name (case-insensitive)
            name_key = name.lower()
            if name_key in seen_names:
                continue

            # 5. Deduplicate by proximity (< 200 m apart)
            if p_lat and p_lon:
                too_close = False
                for (sl, sn) in seen_coords:
                    if _haversine_km(sl, sn, p_lat, p_lon) < 0.2:
                        too_close = True
                        break
                if too_close:
                    continue
                seen_coords.append((p_lat, p_lon))

            seen_names[name_key] = True
            filtered.append(p)

        print(f"[FILTER] {len(places)} raw → {len(filtered)} after strict filter + dedup")
        return filtered

    # ────────────────────────────────────────────────
    # FORMAT  &  IMAGE RESOLUTION
    # ────────────────────────────────────────────────
    def _format_place(self, place: Dict, details: Optional[Dict] = None) -> Dict[str, Any]:
        """Format a place into the clean output format with image resolution."""
        merged = {**place}
        if details:
            merged.update(details)
        
        place_name = (merged.get('name') or '').strip()
        city = self.trip.city or ''
        country = self.trip.country or ''
        
        # Deterministic category
        category = _classify_category(merged.get('kinds', ''))
        
        # ── Image resolution ──
        image = None
        image_source = 'fallback'
        
        # Step 1: OpenTripMap image
        if merged.get('image'):
            image = merged['image']
            image_source = 'opentripmap'
        elif merged.get('preview') and merged['preview'].get('source'):
            image = merged['preview']['source']
            image_source = 'opentripmap'
        
        # Step 2: Unsplash — "<place> <city> travel"
        if not image:
            try:
                image, image_source = unsplash_service.get_place_image_with_fallback(
                    place_name=place_name,
                    city=city,
                    country=country,
                    category=category.lower()
                )
            except Exception as e:
                logger.warning(f"Unsplash error for {place_name}: {e}")
        
        # Step 3: empty string (frontend renders gradient placeholder)
        if not image:
            image = ''
            image_source = 'fallback'
        
        # Description
        description = merged.get('description', '')
        if not description and merged.get('wikipedia_extracts'):
            description = merged['wikipedia_extracts'].get('text', '')[:300]
        
        # Coordinates
        point = merged.get('point', {})
        lat = point.get('lat') or merged.get('lat', 0)
        lon = point.get('lon') or merged.get('lon', 0)
        
        return {
            'xid': merged.get('xid', ''),
            'name': place_name,
            'city': city,
            'image': image,
            'image_source': image_source,
            'short_description': description,
            'category': category,
            'lat': lat,
            'lon': lon,
            'kinds': merged.get('kinds', ''),
            'wikipedia': merged.get('wikipedia', ''),
            'address': merged.get('address', {}),
        }

    # ────────────────────────────────────────────────
    # MAIN  RECOMMEND  PIPELINE
    # ────────────────────────────────────────────────
    def recommend(
        self,
        radius: int = 30000,   # 30 km default
        limit: int = 12        # return top 12
    ) -> List[Dict[str, Any]]:
        """
        Generate high-quality destination recommendations.

        Pipeline:
        1. Resolve coordinates
        2. Fetch raw POIs (with interest-based kinds where available)
        3. Strict filter + dedup
        4. Enrich top candidates with details (parallel)
        5. Format → score → sort → take top *limit*
        """
        print(f"[RECOMMEND] trip={self.trip.id}, city={self.trip.city}, radius={radius}, limit={limit}")
        
        if not self._ensure_coordinates():
            return []
        
        self._load_members_data()
        interests = self._get_dominant_interests()
        kinds = self._map_interests_to_kinds(interests)
        print(f"[RECOMMEND] interests={interests}, otm_kinds={kinds}")
        
        # ── Fetch raw places ──
        places = opentripmap_service.get_places_by_radius(
            lat=self.trip.latitude,
            lon=self.trip.longitude,
            kinds=kinds,
            radius=radius,
            limit=100   # fetch more so filtering has room
        )
        print(f"[RECOMMEND] OTM (with kinds) → {len(places) if places else 0}")
        
        # Fallback: broader search without kinds filter
        if not places or len(places) < limit:
            broad = opentripmap_service.get_places_by_radius(
                lat=self.trip.latitude,
                lon=self.trip.longitude,
                kinds=None,
                radius=radius,
                limit=100
            )
            if broad:
                existing_xids = {p['xid'] for p in (places or [])}
                for p in broad:
                    if p.get('xid') and p['xid'] not in existing_xids:
                        (places or []).append(p)
                        existing_xids.add(p['xid'])
            if not places:
                places = broad or []
            print(f"[RECOMMEND] After broad search: {len(places)} total raw")
        
        if not places:
            return []
        
        # ── Strict filter + dedup ──
        filtered = self._filter_places(places)
        if not filtered:
            print("[RECOMMEND] All places rejected by filter — returning empty")
            return []
        
        # ── Enrich top candidates with details ──
        # Request more than *limit* so scoring can pick the best
        enrich_count = min(len(filtered), limit * 3)
        enriched = opentripmap_service.get_places_with_details(
            places=filtered[:enrich_count],
            max_details=min(enrich_count, 20)
        )
        
        # ── Format, score, sort ──
        scored: List[tuple] = []   # (score, formatted_dict)
        for place in enriched:
            details = place.get('details')
            # Re-check name after enrichment (details may override)
            merged_name = (details or {}).get('name') or place.get('name', '')
            if not _is_valid_name(merged_name):
                continue
            
            formatted = self._format_place(place, details)
            has_image = bool(formatted['image'])
            score = _quality_score({**place, **(details or {})}, has_image)
            scored.append((score, formatted))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        recommendations = [item for _, item in scored[:limit]]
        
        print(f"[RECOMMEND] Returning {len(recommendations)} high-quality destinations")
        if recommendations:
            for i, r in enumerate(recommendations[:3]):
                print(f"  #{i+1} {r['name']} ({r['category']}) score={scored[i][0]}")
        
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
    limit: int = 12
) -> List[Dict[str, Any]]:
    """Convenience function to get recommendations for a trip."""
    recommender = TripRecommender(trip)
    return recommender.recommend(limit=limit)


def get_group_analysis(trip: Trip) -> Dict[str, Any]:
    """Convenience function to get group analysis for a trip."""
    recommender = TripRecommender(trip)
    return recommender.get_group_analysis()
