"""
Unsplash API Service Layer.

Fetches high-quality destination images from Unsplash with intelligent fallback strategy.
Uses database caching to minimize API calls.
"""

import logging
import requests
from typing import Optional, Tuple
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

UNSPLASH_API_BASE = "https://api.unsplash.com"
REQUEST_TIMEOUT = 10

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
    ],
    'adventure': [
        'https://images.unsplash.com/photo-1551632811-561732d1e306?w=800',  # Rock climbing
        'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800',  # Hiking
        'https://images.unsplash.com/photo-1483728642387-6c3bdd6c93e5?w=800',  # Mountains
        'https://images.unsplash.com/photo-1501555088652-021faa106b9b?w=800',  # Adventure
    ],
    'culture': [
        'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800',  # Historic building
        'https://images.unsplash.com/photo-1533929736458-ca588d08c8be?w=800',  # Museum
        'https://images.unsplash.com/photo-1555400038-63f5ba517a47?w=800',  # Temple
        'https://images.unsplash.com/photo-1558525148-544f74d6678f?w=800',  # Architecture
    ],
    'food': [
        'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800',  # Food platter
        'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800',  # Restaurant
        'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800',  # Pizza
        'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800',  # Salad
    ],
    'gastronomy': [
        'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800',
        'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800',
    ],
    'leisure': [
        'https://images.unsplash.com/photo-1540541338287-41700207dee6?w=800',  # Beach leisure
        'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800',  # Tropical beach
        'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800',  # Pool
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
        # Check if Unsplash is temporarily disabled due to 403 errors
        if cache.get(UNSPLASH_DISABLED_KEY):
            logger.warning("Unsplash API temporarily disabled due to previous 403 errors")
            return None
        
        if not self.access_key:
            logger.warning("UNSPLASH_ACCESS_KEY not configured")
            return None
        
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
            
            # Handle 403 Forbidden - likely rate limit or invalid API key
            if response.status_code == 403:
                error_message = response.text[:200] if response.text else "No error details"
                
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
                    logger.info(f"✓ Unsplash found image for: {query}")
                    return image_url
            
            logger.debug(f"✗ No Unsplash results for: {query}")
            return None
            
        except requests.exceptions.Timeout:
            logger.warning(f"Unsplash timeout for: {query}")
            return None
        except requests.exceptions.RequestException as e:
            # Don't log full error for 403 to avoid spam
            if '403' not in str(e):
                logger.warning(f"Unsplash request error for '{query}': {str(e)}")
            return None
        except Exception as e:
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
                import hashlib
                hash_obj = hashlib.md5(f"{place_name}_{city}".encode())
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
        fallback_queries = []
        
        # STEP 1: Full detailed search
        if place_name and city and country:
            fallback_queries.append(f"{place_name} {city} {country}")
        elif place_name and city:
            fallback_queries.append(f"{place_name} {city}")
        elif place_name:
            fallback_queries.append(place_name)
        
        # STEP 2: Category-based search with city
        if city and category in CATEGORY_KEYWORDS:
            fallback_queries.append(f"{city} {CATEGORY_KEYWORDS[category]}")
        
        # STEP 3: City + country
        if city and country:
            fallback_queries.append(f"{city} {country}")
        elif city:
            fallback_queries.append(f"{city} landmark")
        
        # Try each query in order
        for query in fallback_queries:
            query_normalized = query.lower().strip()
            
            # Check database cache first
            try:
                cached = DestinationImageCache.objects.filter(query=query_normalized).first()
                if cached:
                    logger.info(f"📦 DB cache hit for: {query}")
                    return cached.image_url, cached.image_source
            except Exception as e:
                logger.warning(f"Error checking cache: {e}")
            
            # Try Unsplash
            image_url = self._search_unsplash(query)
            
            if image_url:
                # Save to database cache
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
        
        # STEP 4: All Unsplash attempts failed, use curated fallback
        logger.info(f"⚠ Using curated fallback for category: {category}")
        
        # Get category fallback images and rotate through them
        fallback_images = CATEGORY_FALLBACK_IMAGES.get(category, CATEGORY_FALLBACK_IMAGES['culture'])
        if isinstance(fallback_images, list):
            # Use hash of place name to consistently select same image for same place
            import hashlib
            hash_obj = hashlib.md5(f"{place_name}_{city}".encode())
            index = int(hash_obj.hexdigest(), 16) % len(fallback_images)
            fallback_url = fallback_images[index]
        else:
            fallback_url = fallback_images
        
        # Cache the fallback too to avoid repeated attempts
        try:
            cache_key = f"{place_name}_{city}_{country}".lower().strip()
            if cache_key:
                DestinationImageCache.objects.update_or_create(
                    query=cache_key,
                    defaults={
                        'image_url': fallback_url,
                        'image_source': 'fallback'
                    }
                )
        except Exception:
            pass
        
        return fallback_url, 'fallback'


# Singleton instance
unsplash_service = UnsplashService()
