from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.trips.models import Trip
from .models import Destination, TripSavedDestination
from .serializers import (
    DestinationSerializer,
    TripSavedDestinationSerializer,
    SaveDestinationSerializer,
)
from .permissions import IsTripMember


class TripRecommendationsView(APIView):
    """
    GET /api/trips/{trip_id}/recommendations/
    Returns destinations filtered by trip destination (city or country match).
    Optional category filter via query param.
    """
    permission_classes = [IsAuthenticated, IsTripMember]

    def get(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)

        destination_parts = [part.strip() for part in trip.destination.split(',')]

        queryset = Destination.objects.filter(is_active=True)

        location_filter = Q()
        for part in destination_parts:
            location_filter |= Q(city__icontains=part) | Q(country__icontains=part)

        queryset = queryset.filter(location_filter)

        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        queryset = queryset.distinct()

        serializer = DestinationSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SaveDestinationView(APIView):
    """
    POST /api/trips/{trip_id}/save-destination/
    Saves a destination to the trip.
    """
    permission_classes = [IsAuthenticated, IsTripMember]

    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)

        serializer = SaveDestinationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        destination_id = serializer.validated_data['destination_id']
        destination = get_object_or_404(Destination, id=destination_id, is_active=True)

        saved_destination, created = TripSavedDestination.objects.get_or_create(
            trip=trip,
            destination=destination,
            defaults={'saved_by': request.user}
        )

        if not created:
            return Response(
                {'detail': 'Destination already saved for this trip.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = TripSavedDestinationSerializer(saved_destination)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class TripSavedDestinationsView(APIView):
    """
    GET /api/trips/{trip_id}/saved-destinations/
    Returns all saved destinations for a trip.
    """
    permission_classes = [IsAuthenticated, IsTripMember]

    def get(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)

        saved_destinations = TripSavedDestination.objects.filter(
            trip=trip
        ).select_related('destination', 'saved_by')

        serializer = TripSavedDestinationSerializer(saved_destinations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
