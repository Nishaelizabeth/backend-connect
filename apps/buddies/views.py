"""
Buddies app views.

This module defines API views for buddy matching endpoints.
"""

from rest_framework import views, status, permissions
from rest_framework.response import Response

from .services import get_buddy_matches
from .serializers import BuddyMatchSerializer


class BuddyMatchListView(views.APIView):
    """
    GET /api/buddies/matches/
    
    Returns top compatible buddies for the authenticated user.
    Uses rule-based matching algorithm to compute compatibility scores.
    
    Query Parameters:
        limit (int): Maximum number of matches to return (default: 10, max: 50)
        min_score (float): Minimum match score threshold (default: 0)
    
    Returns:
        200: List of buddy matches sorted by score descending
        401: Unauthorized (not authenticated)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Parse query parameters
        try:
            limit = min(int(request.query_params.get('limit', 10)), 50)
        except (ValueError, TypeError):
            limit = 10
        
        try:
            min_score = float(request.query_params.get('min_score', 0))
        except (ValueError, TypeError):
            min_score = 0.0

        # Get matches using the service
        matches = get_buddy_matches(
            user=request.user,
            limit=limit,
            min_score=min_score
        )

        # Serialize and return
        serializer = BuddyMatchSerializer(matches, many=True)
        return Response({
            'count': len(matches),
            'results': serializer.data
        }, status=status.HTTP_200_OK)
