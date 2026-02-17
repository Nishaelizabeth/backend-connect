"""
OpenWeather API Service.

Fetches weather data from OpenWeather API with caching support.
"""

import logging
import requests
from typing import Optional, Dict, Any
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
REQUEST_TIMEOUT = 10


class WeatherService:
    """
    Service class for fetching weather data from OpenWeather API.
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENWEATHER_API_KEY', '')
        self.cache_minutes = getattr(settings, 'OPENWEATHER_CACHE_MINUTES', 30)
    
    def get_weather_by_coords(
        self,
        lat: float,
        lon: float
    ) -> Optional[Dict[str, Any]]:
        """
        Get weather data for given coordinates.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dictionary with temperature, condition, description, icon
            or None if request fails
        """
        if not self.api_key:
            logger.error("OPENWEATHER_API_KEY not configured")
            return None
        
        try:
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            logger.info(f"OpenWeather request: lat={lat}, lon={lon}")
            response = requests.get(
                OPENWEATHER_BASE_URL,
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response
            weather_info = data.get('weather', [{}])[0]
            main_info = data.get('main', {})
            
            result = {
                'temperature': round(main_info.get('temp', 0)),
                'feels_like': round(main_info.get('feels_like', 0)),
                'condition': weather_info.get('main', 'Unknown'),
                'description': weather_info.get('description', '').title(),
                'icon': weather_info.get('icon', '01d'),
                'humidity': main_info.get('humidity', 0),
                'city_name': data.get('name', ''),
            }
            
            logger.info(f"OpenWeather response: {result['temperature']}°C, {result['condition']}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenWeather API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in weather service: {e}")
            return None
    
    def get_weather_for_trip(self, trip) -> Optional[Dict[str, Any]]:
        """
        Get weather for a trip, using cached data if available and fresh.
        
        Priority:
        1. First saved destination coordinates
        2. Trip city coordinates
        
        Args:
            trip: Trip model instance
            
        Returns:
            Weather data dictionary or None
        """
        from apps.trips.models import TripWeatherCache
        from apps.recommendations.models import TripSavedDestination
        
        # Check cache first
        cache_cutoff = timezone.now() - timedelta(minutes=self.cache_minutes)
        try:
            cache = TripWeatherCache.objects.get(
                trip=trip,
                last_updated__gte=cache_cutoff
            )
            logger.info(f"Using cached weather for trip {trip.id}")
            return {
                'temperature': cache.temperature,
                'condition': cache.condition,
                'description': cache.description,
                'icon': cache.icon,
                'city_name': cache.city_name,
                'cached': True,
                'last_updated': cache.last_updated.isoformat(),
            }
        except TripWeatherCache.DoesNotExist:
            pass
        
        # Determine coordinates to use
        lat, lon = None, None
        location_source = None
        
        # Priority 1: First saved destination with coordinates
        try:
            saved_dest = TripSavedDestination.objects.filter(
                trip=trip,
                destination__lat__isnull=False,
                destination__lon__isnull=False
            ).select_related('destination').first()
            
            if saved_dest:
                lat = saved_dest.destination.lat
                lon = saved_dest.destination.lon
                location_source = 'itinerary'
                logger.info(f"Using itinerary destination coords: {lat}, {lon}")
        except Exception as e:
            logger.warning(f"Failed to get itinerary destination: {e}")
        
        # Priority 2: Trip city coordinates
        if lat is None and trip.latitude and trip.longitude:
            lat = trip.latitude
            lon = trip.longitude
            location_source = 'trip'
            logger.info(f"Using trip coords: {lat}, {lon}")
        
        if lat is None or lon is None:
            logger.warning(f"No coordinates available for trip {trip.id}")
            return None
        
        # Fetch fresh weather data
        weather_data = self.get_weather_by_coords(lat, lon)
        
        if weather_data:
            # Update cache
            TripWeatherCache.objects.update_or_create(
                trip=trip,
                defaults={
                    'temperature': weather_data['temperature'],
                    'condition': weather_data['condition'],
                    'description': weather_data['description'],
                    'icon': weather_data['icon'],
                    'city_name': weather_data.get('city_name', trip.city or ''),
                    'last_updated': timezone.now(),
                }
            )
            
            weather_data['cached'] = False
            weather_data['location_source'] = location_source
        
        return weather_data
    
    def get_icon_url(self, icon_code: str) -> str:
        """Get the full URL for a weather icon."""
        return f"https://openweathermap.org/img/wn/{icon_code}@2x.png"


# Global service instance
weather_service = WeatherService()
