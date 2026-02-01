from rest_framework import permissions
from apps.trips.models import TripMember


class IsTripMemberAccepted(permissions.BasePermission):
    """
    Permission class to check if user is an accepted member of the trip.
    Creator is automatically included.
    """
    message = "You must be an accepted member of this trip to access the chat."

    def has_permission(self, request, view):
        trip_id = view.kwargs.get('trip_id')
        if not trip_id:
            return False
        
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        # Check if user is the trip creator or an accepted member
        return TripMember.objects.filter(
            trip_id=trip_id,
            user=user,
            status=TripMember.MembershipStatus.ACCEPTED
        ).exists()


def is_accepted_trip_member(user, trip_id):
    """
    Utility function to check if a user is an accepted trip member.
    Used in WebSocket consumer.
    """
    if not user or not user.is_authenticated:
        return False
    
    return TripMember.objects.filter(
        trip_id=trip_id,
        user=user,
        status=TripMember.MembershipStatus.ACCEPTED
    ).exists()
