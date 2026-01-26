from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Trip, TripMember
from .serializers import TripCreateSerializer, TripListSerializer, TripDetailSerializer
from apps.notifications.models import Notification


class TripListCreateAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        trips = Trip.objects.filter(
            Q(creator=user) | Q(members__user=user, members__status=TripMember.MembershipStatus.ACCEPTED)
        ).distinct().select_related('creator').prefetch_related('members__user').order_by('start_date')

        serializer = TripListSerializer(trips, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TripCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        trip = serializer.save()
        out = TripDetailSerializer(trip)
        return Response(out.data, status=status.HTTP_201_CREATED)


class TripDetailAPIView(APIView):
    """GET /api/trips/<pk>/ - Get trip details"""
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        user = request.user

        # Check if user is creator or accepted member
        is_creator = trip.creator == user
        is_member = TripMember.objects.filter(
            trip=trip, user=user, status=TripMember.MembershipStatus.ACCEPTED
        ).exists()

        if not is_creator and not is_member:
            return Response({'detail': 'You do not have access to this trip.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = TripDetailSerializer(trip)
        return Response(serializer.data)


class RemoveMemberAPIView(APIView):
    """POST /api/trips/<pk>/remove-member/<member_id>/ - Remove a member (creator only)"""
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk, member_id):
        trip = get_object_or_404(Trip, pk=pk)

        # Only creator can remove members
        if trip.creator != request.user:
            return Response({'detail': 'Only the trip creator can remove members.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            membership = TripMember.objects.get(id=member_id, trip=trip)
        except TripMember.DoesNotExist:
            return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Cannot remove the creator
        if membership.role == TripMember.Role.CREATOR:
            return Response({'detail': 'Cannot remove the trip creator.'}, status=status.HTTP_400_BAD_REQUEST)

        removed_user = membership.user
        membership.delete()

        # Notify removed user
        # Notify removed user
        Notification.create_trip_member_removed(
            user=removed_user,
            trip=trip
        )

        return Response({'detail': 'Member removed successfully.'})


class DeleteTripAPIView(APIView):
    """DELETE /api/trips/<pk>/ - Delete/cancel a trip (creator only)"""
    permission_classes = (IsAuthenticated,)

    def delete(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)

        # Only creator can delete
        if trip.creator != request.user:
            return Response({'detail': 'Only the trip creator can delete this trip.'}, status=status.HTTP_403_FORBIDDEN)

        # Notify all members before deletion
        members = TripMember.objects.filter(trip=trip).exclude(user=request.user)
        for membership in members:
            Notification.create_trip_cancelled(
                user=membership.user,
                trip_title=trip.title
            )

        trip.delete()
        return Response({'detail': 'Trip deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)


class InviteToTripAPIView(APIView):
    """POST /api/trips/<pk>/invite/ - Invite a buddy to an existing trip (creator only)"""
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        from apps.buddies.models import BuddyRequest
        from django.contrib.auth import get_user_model
        User = get_user_model()

        trip = get_object_or_404(Trip, pk=pk)

        # Only creator can invite
        if trip.creator != request.user:
            return Response({'detail': 'Only the trip creator can invite members.'}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_to_invite = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Check if user is already a member
        if TripMember.objects.filter(trip=trip, user=user_to_invite).exists():
            return Response({'detail': 'User is already invited or a member of this trip.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user is a connected buddy
        connected = BuddyRequest.objects.filter(
            (Q(sender=request.user) & Q(receiver=user_to_invite) | Q(sender=user_to_invite) & Q(receiver=request.user))
            & Q(status=BuddyRequest.Status.ACCEPTED)
        ).exists()

        if not connected:
            return Response({'detail': 'You can only invite connected buddies.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create trip member with invited status
        TripMember.objects.create(
            trip=trip,
            user=user_to_invite,
            role=TripMember.Role.MEMBER,
            status=TripMember.MembershipStatus.INVITED
        )

        # Create notifications
        Notification.create_trip_invite_sent(
            sender=request.user,
            receiver=user_to_invite,
            trip=trip
        )

        Notification.create_trip_invite_received(
            receiver=user_to_invite,
            sender=request.user,
            trip=trip
        )

        return Response({'detail': 'Invitation sent successfully.'}, status=status.HTTP_201_CREATED)


class AcceptTripAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        try:
            membership = TripMember.objects.get(trip=trip, user=request.user)
        except TripMember.DoesNotExist:
            return Response({'detail': 'Not invited to this trip.'}, status=status.HTTP_403_FORBIDDEN)

        if membership.status != TripMember.MembershipStatus.INVITED:
            return Response({'detail': 'Invitation cannot be accepted.'}, status=status.HTTP_400_BAD_REQUEST)

        membership.status = TripMember.MembershipStatus.ACCEPTED
        membership.joined_at = timezone.now()
        membership.save()

        # Notify creator
        Notification.create_trip_invite_accepted(
            sender=trip.creator,
            receiver=request.user,
            trip=trip
        )

        return Response({'detail': 'Invitation accepted.'})


class RejectTripAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        try:
            membership = TripMember.objects.get(trip=trip, user=request.user)
        except TripMember.DoesNotExist:
            return Response({'detail': 'Not invited to this trip.'}, status=status.HTTP_403_FORBIDDEN)

        if membership.status != TripMember.MembershipStatus.INVITED:
            return Response({'detail': 'Invitation cannot be rejected.'}, status=status.HTTP_400_BAD_REQUEST)

        membership.status = TripMember.MembershipStatus.REJECTED
        membership.save()

        # Notify creator
        Notification.create_trip_invite_rejected(
            sender=trip.creator,
            receiver=request.user,
            trip=trip
        )

        return Response({'detail': 'Invitation rejected.'})


class LeaveTripAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        try:
            membership = TripMember.objects.get(trip=trip, user=request.user)
        except TripMember.DoesNotExist:
            return Response({'detail': 'You are not a member of this trip.'}, status=status.HTTP_404_NOT_FOUND)

        if membership.role == TripMember.Role.CREATOR:
            return Response({'detail': 'Trip creator cannot leave the trip. Delete the trip instead.'}, status=status.HTTP_400_BAD_REQUEST)

        # Notify creator before deleting membership
        Notification.create_member_left_trip(
            user=trip.creator,
            member_name=request.user.get_full_name(),
            trip=trip
        )

        membership.delete()
        return Response({'detail': 'Successfully left the trip.'})


class DashboardStatsView(APIView):
    """
    GET /api/trips/dashboard/stats/
    Returns:
        {
            "trips_created": int,
            "trips_joined": int
        }
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        
        # Count trips created by user
        trips_created = Trip.objects.filter(creator=user).count()
        
        # Count trips joined (where user is accepted member but not creator)
        trips_joined = TripMember.objects.filter(
            user=user,
            status=TripMember.MembershipStatus.ACCEPTED
        ).exclude(trip__creator=user).count()
        
        return Response({
            'trips_created': trips_created,
            'trips_joined': trips_joined
        })


class InvitationsListAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        invitations = TripMember.objects.filter(user=user, status=TripMember.MembershipStatus.INVITED).select_related('trip__creator', 'user', 'trip')

        from .serializers import TripInvitationSerializer

        serializer = TripInvitationSerializer(invitations, many=True)
        return Response({
            'count': invitations.count(),
            'results': serializer.data
        })
