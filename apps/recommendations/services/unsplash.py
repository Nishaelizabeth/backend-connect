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
# Removed hardcoded URLs — Unsplash API or empty fallback is used instead
CATEGORY_FALLBACK_IMAGES: dict[str, list[str]] = {
    'nature': [],
    'adventure': [],
    'culture': [],
    'religion': [],
    'food': [],
    'gastronomy': [],
    'leisure': [],
    'all': [],
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
            fallback_images = CATEGORY_FALLBACK_IMAGES.get(category, CATEGORY_FALLBACK_IMAGES.get('culture', []))
            if isinstance(fallback_images, list) and len(fallback_images) > 0:
                hash_str = f"{place_name}_{city}_{country}".lower()
                hash_obj = hashlib.md5(hash_str.encode())
                index = int(hash_obj.hexdigest(), 16) % len(fallback_images)
                fallback_url = fallback_images[index]
            elif isinstance(fallback_images, str) and fallback_images:
                fallback_url = fallback_images
            else:
                # No fallback images configured - return empty
                return '', 'fallback'
            
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
        fallback_images = CATEGORY_FALLBACK_IMAGES.get(category, CATEGORY_FALLBACK_IMAGES.get('culture', []))
        if isinstance(fallback_images, list) and len(fallback_images) > 0:
            # Use hash of place name to consistently select different images for different places
            hash_str = f"{place_name}_{city}_{country}".lower()
            hash_obj = hashlib.md5(hash_str.encode())
            index = int(hash_obj.hexdigest(), 16) % len(fallback_images)
            fallback_url = fallback_images[index]
            print(f"[DEBUG] Fallback image index {index} for: {place_name}")
        elif isinstance(fallback_images, str) and fallback_images:
            fallback_url = fallback_images
        else:
            # No fallback images configured - return empty (no hardcoded images policy)
            print(f"[DEBUG] No fallback image available for category: {category}")
            return '', 'fallback'
        
        return fallback_url, 'fallback'


# Singleton instance
unsplash_service = UnsplashService()
