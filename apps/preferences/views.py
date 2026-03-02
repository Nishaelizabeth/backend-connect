from rest_framework import status, generics, permissions, views
from rest_framework.response import Response
from django.db.models import Q
from .models import Preference, Interest
from .serializers import (
    PreferenceSerializer, 
    PreferenceDetailSerializer, 
    InterestSerializer
)

class UserPreferenceView(views.APIView):
    """
    Manage logged-in user's preferences.
    GET: Retrieve preferences
    POST: Create preferences
    PUT: Update preferences
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            preference = Preference.objects.get(user=request.user)
            serializer = PreferenceDetailSerializer(preference)
            return Response(serializer.data)
        except Preference.DoesNotExist:
            # Return empty state as per requirements, not 404
            return Response({})

    def post(self, request):
        # Check if preferences already exist
        if Preference.objects.filter(user=request.user).exists():
            return Response(
                {"detail": "Preferences already exist for this user. Use PUT to update."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = PreferenceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            preference = serializer.save()
            # Return detailed representation after creation
            detail_serializer = PreferenceDetailSerializer(preference)
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        try:
            preference = Preference.objects.get(user=request.user)
        except Preference.DoesNotExist:
            return Response(
                {"detail": "Preferences not found. Use POST to create."}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        serializer = PreferenceSerializer(
            preference, 
            data=request.data, 
            context={'request': request}, 
            partial=False 
        )
        if serializer.is_valid():
            preference = serializer.save()
            detail_serializer = PreferenceDetailSerializer(preference)
            return Response(detail_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InterestListView(generics.ListCreateAPIView):
    """
    GET:  List interests visible to the requesting user:
          - all is_default=True interests (global/seeded)
          - the user's own custom interests (is_default=False, created_by=user)
    POST: Create a new custom interest for the authenticated user.
          The interest is private (is_default=False) and only visible to its creator.
    """
    serializer_class = InterestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Interest.objects.filter(
            Q(is_default=True) | Q(created_by=user),
            is_active=True
        ).order_by('is_default', 'name')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def perform_create(self, serializer):
        """Save a new custom interest owned by the requesting user."""
        serializer.save(
            is_default=False,
            created_by=self.request.user,
            is_active=True
        )
