"""
Background Recommendation Generator.

Generates trip recommendations asynchronously to avoid blocking API requests.
Uses threading for background execution (can be replaced with Celery if available).
"""

import logging
import threading
import traceback
from typing import Optional
from datetime import timedelta
from django.utils import timezone
from django.db import transaction, close_old_connections

logger = logging.getLogger(__name__)


def generate_trip_recommendations_async(trip_id: int) -> None:
    """
    Trigger background generation of trip recommendations.
    
    Args:
        trip_id: ID of the trip to generate recommendations for
    """
    print(f"[GENERATOR] STARTING THREAD for trip: {trip_id}")
    thread = threading.Thread(
        target=_generate_recommendations_worker,
        args=(trip_id,),
        daemon=True,
        name=f"RecommendationGenerator-{trip_id}"
    )
    thread.start()
    print(f"[GENERATOR] Thread started: {thread.name}")
    logger.info(f"🚀 Started background recommendation generation for trip {trip_id}")


def _generate_recommendations_worker(trip_id: int) -> None:
    """
    Worker function that runs in background thread to generate recommendations.
    
    CRITICAL: This function MUST always update cache status (ready or failed).
    
    Args:
        trip_id: ID of the trip
    """
    print(f"[GENERATOR] WORKER STARTED for trip: {trip_id}")
    
    # Close old database connections for thread safety
    close_old_connections()
    
    cache = None
    
    try:
        # Import models inside thread to avoid circular imports
        print(f"[GENERATOR] Importing models...")
        from apps.trips.models import Trip
        from apps.recommendations.models import TripRecommendationCache
        from apps.recommendations.services.recommender import TripRecommender
        print(f"[GENERATOR] Models imported successfully")
        
        # Get trip
        print(f"[GENERATOR] Fetching trip {trip_id}...")
        trip = Trip.objects.get(id=trip_id)
        print(f"[GENERATOR] Trip found: {trip.title}, city={trip.city}, country={trip.country}")
        
        # Get or create cache entry
        cache, created = TripRecommendationCache.objects.get_or_create(
            trip=trip,
            defaults={
                'status': TripRecommendationCache.Status.PENDING,
                'data': {},
                'expires_at': timezone.now() + timedelta(hours=24)
            }
        )
        print(f"[GENERATOR] Cache entry {'created' if created else 'found'}, status={cache.status}")
        
        # Create recommender instance
        print(f"[GENERATOR] Creating TripRecommender...")
        recommender = TripRecommender(trip)
        
        # Single fetch — get all destinations for the trip location
        try:
            print(f"[GENERATOR] Fetching destinations for trip location...")
            recommendations = recommender.recommend(limit=12)
            print(f"[GENERATOR] Got {len(recommendations)} destinations")
        except Exception as e:
            print(f"[GENERATOR] ERROR fetching destinations: {str(e)}")
            logger.error(f"✗ Failed to generate recommendations: {str(e)}")
            recommendations = []
        
        # Update cache with SUCCESS
        print(f"[GENERATOR] Saving cache data...")
        cache.data = {'recommendations': recommendations}
        cache.status = TripRecommendationCache.Status.READY
        cache.error_message = ''
        cache.expires_at = timezone.now() + timedelta(hours=24)
        cache.save()
        
        print(f"[GENERATOR] COMPLETED for trip {trip_id} with {len(recommendations)} recommendations")
        logger.info(f"✅ Successfully cached recommendations for trip {trip_id}")
        
    except Exception as e:
        # CRITICAL: Always update cache status on error
        error_msg = str(e)
        tb = traceback.format_exc()
        print(f"[GENERATOR ERROR] Trip {trip_id}: {error_msg}")
        print(f"[GENERATOR ERROR] Traceback:\n{tb}")
        logger.error(f"❌ Failed to generate recommendations for trip {trip_id}: {error_msg}", exc_info=True)
        
        # Try to mark cache as failed
        try:
            from apps.recommendations.models import TripRecommendationCache
            close_old_connections()
            
            cache_obj, _ = TripRecommendationCache.objects.get_or_create(
                trip_id=trip_id,
                defaults={'expires_at': timezone.now() + timedelta(hours=1)}
            )
            cache_obj.status = TripRecommendationCache.Status.FAILED
            cache_obj.error_message = f"{error_msg[:500]}\n{tb[:500]}"
            cache_obj.save()
            print(f"[GENERATOR] Cache marked as FAILED for trip {trip_id}")
        except Exception as cache_error:
            print(f"[GENERATOR ERROR] Failed to update cache status: {str(cache_error)}")
    
    finally:
        # Ensure database connections are closed
        close_old_connections()
        print(f"[GENERATOR] Worker finished for trip {trip_id}")


def invalidate_trip_cache(trip_id: int) -> None:
    """
    Invalidate recommendation cache for a trip.
    
    Args:
        trip_id: ID of the trip
    """
    from apps.recommendations.models import TripRecommendationCache
    
    try:
        cache = TripRecommendationCache.objects.filter(trip_id=trip_id).first()
        if cache:
            cache.delete()
            logger.info(f"🗑️ Deleted recommendation cache for trip {trip_id}")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache for trip {trip_id}: {str(e)}")


def get_or_generate_recommendations(trip_id: int) -> dict:
    """
    Get cached recommendations or trigger generation.
    
    FAIL-SAFE: Always returns valid dict, never raises exception.
    
    Args:
        trip_id: ID of the trip
        
    Returns:
        Dictionary with status and data/recommendations
    """
    from apps.trips.models import Trip
    from apps.recommendations.models import TripRecommendationCache
    
    print(f"[DEBUG] get_or_generate_recommendations called: trip_id={trip_id}")
    
    try:
        trip = Trip.objects.get(id=trip_id)
        print(f"[DEBUG] Trip found: {trip.title}")
    except Trip.DoesNotExist:
        print(f"[DEBUG] ERROR: Trip {trip_id} not found")
        return {
            'status': 'ready',
            'recommendations': [],
            'message': 'Trip not found'
        }
    except Exception as e:
        print(f"[DEBUG] ERROR fetching trip: {str(e)}")
        return {
            'status': 'ready',
            'recommendations': [],
            'message': 'Failed to load trip'
        }
    
    try:
        # Check for existing cache
        cache = TripRecommendationCache.objects.filter(trip=trip).first()
        print(f"[DEBUG] Cache found: {cache is not None}, status={cache.status if cache else 'N/A'}")
        
        # If cache exists and is ready
        if cache and cache.is_ready():
            recommendations = cache.data.get('recommendations', [])
            print(f"[DEBUG] Cache is READY, returning {len(recommendations)} recommendations")
            
            return {
                'status': 'ready',
                'recommendations': recommendations if recommendations else [],
                'cached_at': cache.last_generated.isoformat(),
                'expires_at': cache.expires_at.isoformat(),
            }
        
        # If cache is pending
        if cache and cache.status == TripRecommendationCache.Status.PENDING:
            # Check if pending for too long (more than 5 minutes = stuck)
            minutes_pending = (timezone.now() - cache.last_generated).total_seconds() / 60
            print(f"[DEBUG] Cache is PENDING for {minutes_pending:.1f} minutes")
            
            if minutes_pending > 2:
                # Stuck - restart generation (e.g. server was reloaded mid-generation)
                print(f"[DEBUG] Cache stuck in PENDING for {minutes_pending:.1f} min, restarting...")
                cache.status = TripRecommendationCache.Status.PENDING
                cache.last_generated = timezone.now()
                cache.save()
                generate_trip_recommendations_async(trip_id)
            
            return {
                'status': 'loading',
                'message': 'Recommendations are being generated...'
            }
        
        # If cache failed
        if cache and cache.status == TripRecommendationCache.Status.FAILED:
            print(f"[DEBUG] Cache FAILED, will retry. Error was: {cache.error_message}")
            # Retry generation
            try:
                cache.delete()
            except Exception:
                pass
        
        # No cache or expired - create new one and trigger generation
        print(f"[DEBUG] Creating new cache and triggering background generation...")
        try:
            with transaction.atomic():
                cache, created = TripRecommendationCache.objects.get_or_create(
                    trip=trip,
                    defaults={
                        'status': TripRecommendationCache.Status.PENDING,
                        'data': {},
                        'expires_at': timezone.now() + timedelta(hours=24),
                    }
                )
                print(f"[DEBUG] Cache created={created}, status={cache.status}")
                
                # If we just created it or it was expired, trigger generation
                if created or cache.is_expired():
                    cache.status = TripRecommendationCache.Status.PENDING
                    cache.data = {}
                    cache.save()
                    
                    # Start background generation
                    print(f"[DEBUG] Calling generate_trip_recommendations_async({trip_id})")
                    generate_trip_recommendations_async(trip_id)
        except Exception as e:
            print(f"[DEBUG] Recommendation Cache Error: {str(e)}")
            # Still return loading to trigger retry
        
        return {
            'status': 'loading',
            'message': 'Generating AI-powered recommendations...'
        }
        
    except Exception as e:
        # FAIL-SAFE: Catch all errors and return empty data
        print(f"Recommendation Error: {str(e)}")
        return {
            'status': 'ready',
            'recommendations': [],
            'message': 'No recommendations available yet.'
        }
