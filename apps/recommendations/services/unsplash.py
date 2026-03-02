"""
Unsplash API Service Layer.

Fetches high-quality destination images from Unsplash with intelligent fallback strategy.
Uses database caching to minimize API calls.
"""

import hashlib
import logging
import requests
from typing import Optional, Tuple
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

UNSPLASH_API_BASE = "https://api.unsplash.com"
REQUEST_TIMEOUT = 3  # Reduced to fail fast

# Global flag to disable Unsplash after repeated 403 errors
UNSPLASH_DISABLED_KEY = 'unsplash_api_disabled'
UNSPLASH_DISABLED_TIMEOUT = 3600  # Disable for 1 hour after 403 errors


# Category-to-search keyword mapping for fallback
CATEGORY_KEYWORDS = {
    'nature': 'landscape nature',
    'adventure': 'adventure outdoor',
    'culture': 'culture heritage',
    'food': 'food cuisine',
    'gastronomy': 'food cuisine',
    'leisure': 'leisure relaxation',
}

# Curated high-quality fallback images per category
# Using varied Unsplash photos to ensure diversity
CATEGORY_FALLBACK_IMAGES = {
    'nature': [
        'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800',  # Mountains
        'https://images.unsplash.com/photo-1511593358241-7eea1f3c84e5?w=800',  # Waterfall
        'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800',  # Forest
        'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800',  # Nature trail
        'https://images.unsplash.com/photo-1426604966848-d7adac402bff?w=800',  # Lake
        'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=800',  # Valley
        'https://images.unsplash.com/photo-1501854140801-50d01698950b?w=800',  # Hills
        'https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=800',  # Sunlight forest
    ],
    'adventure': [
        'https://images.unsplash.com/photo-1551632811-561732d1e306?w=800',  # Rock climbing
        'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800',  # Hiking
        'https://images.unsplash.com/photo-1483728642387-6c3bdd6c93e5?w=800',  # Mountains
        'https://images.unsplash.com/photo-1501555088652-021faa106b9b?w=800',  # Adventure
        'https://images.unsplash.com/photo-1527004013197-933c4bb611b3?w=800',  # Exploration
        'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800',  # Mountain peak
    ],
    'culture': [
        'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800',  # Historic building
        'https://images.unsplash.com/photo-1533929736458-ca588d08c8be?w=800',  # Museum
        'https://images.unsplash.com/photo-1555400038-63f5ba517a47?w=800',  # Temple
        'https://images.unsplash.com/photo-1558525148-544f74d6678f?w=800',  # Architecture
        'https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=800',  # Taj Mahal
        'https://images.unsplash.com/photo-1544735716-392fe2489ffa?w=800',  # Ancient ruins
        'https://images.unsplash.com/photo-1531572753322-ad063cecc140?w=800',  # Church
        'https://images.unsplash.com/photo-1548013146-72479768bada?w=800',  # Indian monument
        'https://images.unsplash.com/photo-1599661046827-dacff0c0f09a?w=800',  # Statue
        'https://images.unsplash.com/photo-1564507592333-c60657eea523?w=800',  # Tower
    ],
    'religion': [
        'https://images.unsplash.com/photo-1555400038-63f5ba517a47?w=800',  # Temple
        'https://images.unsplash.com/photo-1531572753322-ad063cecc140?w=800',  # Church
        'https://images.unsplash.com/photo-1548013146-72479768bada?w=800',  # Monument
        'https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=800',  # Taj Mahal
        'https://images.unsplash.com/photo-1600093463592-8e36ae95ef56?w=800',  # Mosque
        'https://images.unsplash.com/photo-1582657233895-0f37a3f150c0?w=800',  # Hindu temple
    ],
    'food': [
        'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800',  # Food platter
        'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800',  # Restaurant
        'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800',  # Pizza
        'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800',  # Salad
        'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800',  # Pancakes
        'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800',  # Bowl
    ],
    'gastronomy': [
        'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800',
        'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800',
        'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800',  # Fine dining
        'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800',  # Restaurant interior
    ],
    'leisure': [
        'https://images.unsplash.com/photo-1540541338287-41700207dee6?w=800',  # Beach leisure
        'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800',  # Tropical beach
        'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800',  # Pool
        'https://images.unsplash.com/photo-1519046904884-53103b34b206?w=800',  # Beach sunset
        'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800',  # Resort pool
    ],
    'all': [
        'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800',  # Nature
        'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800',  # City
        'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800',  # Beach
        'https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=800',  # Monument
        'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800',  # Mountains
        'https://images.unsplash.com/photo-1533929736458-ca588d08c8be?w=800',  # Cultural
        'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800',  # Adventure
        'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800',  # Food
    ],
}


class UnsplashService:
    """
    Service class for fetching destination images from Unsplash with intelligent fallback.
    
    Implements a 4-step fallback strategy:
    1. Search: <place_name> + <city> + <country>
    2. Search: <category_keyword> + <city>
    3. Search: <city> + <country>
    4. Use hardcoded category fallback
    """
    
    def __init__(self):
        self.access_key = getattr(settings, 'UNSPLASH_ACCESS_KEY', '')
        self.base_url = UNSPLASH_API_BASE
    
    def _search_unsplash(self, query: str) -> Optional[str]:
        """
        Make a single Unsplash API search request.
        
        Args:
            query: Search query string
            
        Returns:
            Image URL if found, None otherwise
        """
        print(f"[DEBUG] Unsplash search for: '{query}'")
        
        # Check if Unsplash is temporarily disabled due to 403 errors
        if cache.get(UNSPLASH_DISABLED_KEY):
            print("[DEBUG] Unsplash API temporarily disabled (previous 403)")
            logger.warning("Unsplash API temporarily disabled due to previous 403 errors")
            return None
        
        if not self.access_key:
            print("[DEBUG] UNSPLASH_ACCESS_KEY not configured!")
            logger.warning("UNSPLASH_ACCESS_KEY not configured")
            return None
        
        print(f"[DEBUG] Using Unsplash key: {self.access_key[:8]}...")
        
        try:
            url = f"{self.base_url}/search/photos"
            headers = {
                'Authorization': f'Client-ID {self.access_key}',
                'Accept-Version': 'v1'
            }
            params = {
                'query': query,
                'per_page': 1,
                'orientation': 'landscape',
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            print(f"[DEBUG] Unsplash response status: {response.status_code}")
            
            # Handle 403 Forbidden - likely rate limit or invalid API key
            if response.status_code == 403:
                error_message = response.text[:200] if response.text else "No error details"
                print(f"[DEBUG] Unsplash 403 ERROR: {error_message}")
                
                if 'Rate Limit' in error_message or 'rate limit' in error_message.lower():
                    logger.error(f"⚠ Unsplash API Rate Limit Exceeded - disabling for 1 hour")
                    logger.info(f"Free tier limit: 50 requests/hour. Consider upgrading or using fallbacks.")
                else:
                    logger.error(f"Unsplash API returned 403 Forbidden: {error_message}")
                
                # Disable Unsplash temporarily to prevent spam
                cache.set(UNSPLASH_DISABLED_KEY, True, UNSPLASH_DISABLED_TIMEOUT)
                return None
            
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            if results and len(results) > 0:
                image_url = results[0].get('urls', {}).get('regular')
                if image_url:
                    print(f"[DEBUG] Unsplash found image: {image_url[:60]}...")
                    logger.info(f"✓ Unsplash found image for: {query}")
                    return image_url
            
            print(f"[DEBUG] Unsplash no results for: {query}")
            logger.debug(f"✗ No Unsplash results for: {query}")
            return None
            
        except requests.exceptions.Timeout:
            print(f"[DEBUG] Unsplash TIMEOUT for: {query}")
            logger.debug(f"Unsplash timeout for: {query}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] Unsplash REQUEST ERROR: {str(e)}")
            # Don't log full error for 403 to avoid spam
            if '403' not in str(e):
                logger.warning(f"Unsplash request error for '{query}': {str(e)}")
            return None
        except Exception as e:
            print(f"[DEBUG] Unsplash UNEXPECTED ERROR: {str(e)}")
            logger.error(f"Unexpected error fetching Unsplash image: {str(e)}")
            return None
    
    def get_place_image_with_fallback(
        self,
        place_name: str,
        city: str = '',
        country: str = '',
        category: str = 'culture'
    ) -> Tuple[str, str]:
        """
        Fetch destination image using multi-step fallback strategy with DB caching.
        
        Args:
            place_name: Name of the destination/POI
            city: City name
            country: Country name
            category: Destination category (nature, culture, etc.)
            
        Returns:
            Tuple of (image_url, image_source)
            - image_url: The resolved image URL
            - image_source: 'unsplash' or 'fallback'
        """
        from apps.recommendations.models import DestinationImageCache
        
        # Check if Unsplash is temporarily disabled
        if cache.get(UNSPLASH_DISABLED_KEY):
            logger.warning("⚠ Unsplash API disabled - using category fallback immediately")
            
            # Use curated fallback with rotation
            fallback_images = CATEGORY_FALLBACK_IMAGES.get(category, CATEGORY_FALLBACK_IMAGES['culture'])
            if isinstance(fallback_images, list):
                hash_str = f"{place_name}_{city}_{country}".lower()
                hash_obj = hashlib.md5(hash_str.encode())
                index = int(hash_obj.hexdigest(), 16) % len(fallback_images)
                fallback_url = fallback_images[index]
            else:
                fallback_url = fallback_images
            
            return fallback_url, 'fallback'
        
        # Normalize inputs
        place_name = place_name.strip()
        city = city.strip()
        country = country.strip()
        
        # Build fallback queries in priority order
        # Build search queries - ONLY use specific queries, not generic ones
        # Avoid generic queries like "Goa culture" that return same image for all places
        search_queries = []
        
        # STEP 1: Try specific place name searches only
        if place_name and city and country:
            search_queries.append(f"{place_name} {city} {country}")
        if place_name and city:
            search_queries.append(f"{place_name} {city}")
        if place_name:
            search_queries.append(place_name)
        
        # Try specific queries only
        for query in search_queries:
            query_normalized = query.lower().strip()
            
            # Check database cache first
            try:
                cached = DestinationImageCache.objects.filter(query=query_normalized).first()
                if cached:
                    print(f"[DEBUG] DB cache hit for: {query}")
                    logger.info(f"📦 DB cache hit for: {query}")
                    return cached.image_url, cached.image_source
            except Exception as e:
                logger.warning(f"Error checking cache: {e}")
            
            # Try Unsplash
            image_url = self._search_unsplash(query)
            
            if image_url:
                # Save to database cache with SPECIFIC query key
                try:
                    DestinationImageCache.objects.update_or_create(
                        query=query_normalized,
                        defaults={
                            'image_url': image_url,
                            'image_source': 'unsplash'
                        }
                    )
                    logger.info(f"💾 Cached Unsplash result for: {query}")
                except Exception as e:
                    logger.warning(f"Error saving to cache: {e}")
                
                return image_url, 'unsplash'
        
        # STEP 2: All specific searches failed - use UNIQUE curated fallback
        # Use place name hash to ensure different places get different images
        print(f"[DEBUG] Using curated fallback for: {place_name} (category: {category})")
        logger.info(f"⚠ Using curated fallback for: {place_name}")
        
        # Get category fallback images and rotate through them based on place name
        fallback_images = CATEGORY_FALLBACK_IMAGES.get(category, CATEGORY_FALLBACK_IMAGES['culture'])
        if isinstance(fallback_images, list) and len(fallback_images) > 0:
            # Use hash of place name to consistently select different images for different places
            hash_str = f"{place_name}_{city}_{country}".lower()
            hash_obj = hashlib.md5(hash_str.encode())
            index = int(hash_obj.hexdigest(), 16) % len(fallback_images)
            fallback_url = fallback_images[index]
            print(f"[DEBUG] Fallback image index {index} for: {place_name}")
        else:
            fallback_url = fallback_images if isinstance(fallback_images, str) else CATEGORY_FALLBACK_IMAGES['culture'][0]
        
        return fallback_url, 'fallback'


# Singleton instance
unsplash_service = UnsplashService()
