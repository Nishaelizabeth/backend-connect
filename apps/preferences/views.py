from rest_framework import status, generics, permissions, views
from rest_framework.response import Response
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
    GET: List all available interests.
    POST: Create a new interest (Authenticated only).
    """
    queryset = Interest.objects.filter(is_active=True)
    serializer_class = InterestSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
