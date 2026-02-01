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
    SaveDestinationFromAPISerializer,
    RecommendedDestinationSerializer,
)
from .permissions import IsTripMember
from .services.recommender import recommend_for_trip, get_group_analysis


class TripRecommendationsView(APIView):
    """
    GET /api/trips/{trip_id}/recommendations/
    
    Returns AI-powered destination recommendations based on:
    - Trip destination city
    - Group members' preferences and interests
    
    Uses OpenTripMap API to fetch relevant POIs.
    
    Query params:
    - category: Filter by category ('nature', 'adventure', 'culture', 'gastronomy')
    - limit: Maximum number of results (default: 30)
    """
    permission_classes = [IsAuthenticated, IsTripMember]

    def get(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        
        # Get query parameters
        category = request.query_params.get('category')
        if category == 'all':
            category = None
        
        try:
            limit = int(request.query_params.get('limit', 30))
            limit = min(max(limit, 1), 100)
        except ValueError:
            limit = 30
        
        # Generate recommendations using the new recommender
        recommendations = recommend_for_trip(trip, category=category, limit=limit)
        
        # If no OpenTripMap results, fall back to database
        if not recommendations:
            city_name = trip.city or ''
            
            queryset = Destination.objects.filter(is_active=True)
            
            location_filter = Q()
            if trip.city:
                location_filter |= Q(city__icontains=trip.city)
            if trip.country:
                location_filter |= Q(country__icontains=trip.country)
            
            if location_filter:
                queryset = queryset.filter(location_filter)
            
            if category:
                queryset = queryset.filter(category=category)
            
            queryset = queryset.distinct()[:limit]
            
            recommendations = [
                {
                    'xid': f"db_{dest.id}",
                    'name': dest.name,
                    'city': dest.city or city_name,
                    'image': dest.image_url or '',
                    'short_description': dest.description,
                    'category': dest.category,
                    'lat': dest.lat,
                    'lon': dest.lon,
                    'kinds': dest.kinds,
                    'wikipedia': '',
                    'address': {},
                }
                for dest in queryset
            ]
        
        serializer = RecommendedDestinationSerializer(recommendations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TripGroupAnalysisView(APIView):
    """
    GET /api/trips/{trip_id}/group-analysis/
    
    Returns analysis of the group's preferences for recommendation tuning.
    """
    permission_classes = [IsAuthenticated, IsTripMember]
    
    def get(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        
        analysis = get_group_analysis(trip)
        
        return Response(analysis, status=status.HTTP_200_OK)


class SaveDestinationView(APIView):
    """
    POST /api/trips/{trip_id}/save-destination/
    
    Saves a destination to the trip.
    Supports two modes:
    1. By destination_id (for already cached destinations)
    2. By OpenTripMap data (xid, name, etc.) for new destinations
    """
    permission_classes = [IsAuthenticated, IsTripMember]

    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        
        # Check if this is OpenTripMap data or legacy destination_id
        if 'xid' in request.data:
            # OpenTripMap data - create/get destination first
            serializer = SaveDestinationFromAPISerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Extract city from trip
            city = trip.city or ''
            validated_data = {**serializer.validated_data, 'city': city}
            
            # Get or create the destination
            destination = serializer.create_destination(validated_data)
            notes = serializer.validated_data.get('notes', '')
        else:
            # Legacy mode - destination_id
            serializer = SaveDestinationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            destination_id = serializer.validated_data['destination_id']
            destination = get_object_or_404(Destination, id=destination_id, is_active=True)
            notes = ''

        # Check for duplicate
        existing = TripSavedDestination.objects.filter(
            trip=trip,
            destination=destination
        ).first()
        
        if existing:
            return Response(
                {'detail': 'Destination already saved for this trip.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the saved destination
        saved_destination = TripSavedDestination.objects.create(
            trip=trip,
            destination=destination,
            saved_by=request.user,
            notes=notes
        )

        # Create notification
        try:
            from apps.notifications.models import Notification
            Notification.create_destination_saved(
                user=request.user,
                destination=destination,
                trip=trip
            )
        except Exception as e:
            # Don't fail the save if notification fails
            import logging
            logging.error(f"Failed to create notification: {e}")

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
