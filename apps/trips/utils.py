"""
Utility functions for trips app.
"""

from django.db.models import Q
from .models import Trip, TripMember


def check_date_overlap(user, start_date, end_date, exclude_trip_id=None):
    """
    Check if a user has any trips with overlapping dates.
    
    A user is considered to be in a trip if they are:
    - The creator of the trip, OR
    - An accepted member of the trip
    
    Date ranges overlap if:
    - new_start <= existing_end AND new_end >= existing_start
    
    Args:
        user: The User instance to check
        start_date: The start date to check (date object)
        end_date: The end date to check (date object)
        exclude_trip_id: Optional trip ID to exclude from check (for updates)
        
    Returns:
        dict with:
            - 'has_overlap': bool
            - 'overlapping_trips': list of overlapping trip dicts
    """
    # Get all trips where user is creator or accepted member
    user_trips = Trip.objects.filter(
        Q(creator=user) | 
        Q(members__user=user, members__status=TripMember.MembershipStatus.ACCEPTED)
    ).distinct()
    
    # Exclude specific trip if provided (for update operations)
    if exclude_trip_id:
        user_trips = user_trips.exclude(id=exclude_trip_id)
    
    # Check for date overlaps
    # Two date ranges overlap if: start1 <= end2 AND end1 >= start2
    overlapping_trips = user_trips.filter(
        Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
    )
    
    has_overlap = overlapping_trips.exists()
    
    # Build response with trip details
    overlapping_trip_list = []
    if has_overlap:
        for trip in overlapping_trips:
            overlapping_trip_list.append({
                'id': trip.id,
                'title': trip.title,
                'destination': trip.display_destination or trip.destination,
                'start_date': trip.start_date,
                'end_date': trip.end_date,
            })
    
    return {
        'has_overlap': has_overlap,
        'overlapping_trips': overlapping_trip_list
    }


def format_date_overlap_error(overlapping_trips):
    """
    Format a user-friendly error message for date overlaps.
    
    Args:
        overlapping_trips: List of overlapping trip dicts
        
    Returns:
        str: Formatted error message
    """
    if not overlapping_trips:
        return "Date range conflicts with existing trips."
    
    if len(overlapping_trips) == 1:
        trip = overlapping_trips[0]
        return (
            f"You already have a trip '{trip['title']}' to {trip['destination']} "
            f"from {trip['start_date']} to {trip['end_date']} that overlaps with these dates."
        )
    else:
        trip_list = ", ".join([f"'{t['title']}'" for t in overlapping_trips])
        return f"You have {len(overlapping_trips)} trips ({trip_list}) with overlapping dates."
