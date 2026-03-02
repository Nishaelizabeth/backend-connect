"""
Signals for cache invalidation.

Automatically invalidates recommendation cache when trip data changes.
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.trips.models import Trip, TripMember

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Trip)
def invalidate_cache_on_trip_update(sender, instance, created, update_fields, **kwargs):
    """
    Invalidate cache when trip location changes.
    
    Triggered when: city, country, or region changes
    """
    if created:
        # Don't invalidate on creation
        return
    
    # If update_fields is provided, check if relevant fields were updated
    if update_fields is not None:
        relevant_fields = {'city', 'country', 'region'}
        if not relevant_fields.intersection(update_fields):
            # None of the relevant fields were updated
            return
    
    logger.info(f"🔄 Trip {instance.id} updated, invalidating cache")
    
    from apps.recommendations.services.background_generator import invalidate_trip_cache
    invalidate_trip_cache(instance.id)


@receiver([post_save, post_delete], sender=TripMember)
def invalidate_cache_on_member_change(sender, instance, **kwargs):
    """
    Invalidate cache when trip members change.
    
    Triggered when: members are added or removed (affects group preferences)
    """
    # Only invalidate for accepted members
    if hasattr(instance, 'status') and instance.status == TripMember.MembershipStatus.ACCEPTED:
        logger.info(f"🔄 Trip {instance.trip_id} members changed, invalidating cache")
        
        from apps.recommendations.services.background_generator import invalidate_trip_cache
        invalidate_trip_cache(instance.trip_id)
