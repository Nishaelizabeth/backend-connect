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
        Notification.objects.create(
            user=trip.creator,
            type='trip_invitation_accepted',
            message=f"{request.user.get_full_name()} accepted your trip invitation to '{trip.title}'.",
            related_object_id=trip.id
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
        Notification.objects.create(
            user=trip.creator,
            type='trip_invitation_rejected',
            message=f"{request.user.get_full_name()} declined your trip invitation to '{trip.title}'.",
            related_object_id=trip.id
        )

        return Response({'detail': 'Invitation rejected.'})


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
