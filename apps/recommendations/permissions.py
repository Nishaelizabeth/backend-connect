from rest_framework.permissions import BasePermission
from apps.trips.models import Trip, TripMember


class IsTripMember(BasePermission):
    """
    Permission check for trip creators and accepted trip members.
    Creator and accepted members are treated equally.
    """

    def has_permission(self, request, view):
        trip_id = view.kwargs.get('trip_id')
        if not trip_id:
            return False

        # Check if user is the trip creator
        is_creator = Trip.objects.filter(
            id=trip_id,
            creator=request.user
        ).exists()

        if is_creator:
            return True

        # Check if user is an accepted member
        return TripMember.objects.filter(
            trip_id=trip_id,
            user=request.user,
            status=TripMember.MembershipStatus.ACCEPTED
        ).exists()

