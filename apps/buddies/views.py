"""
Buddies app views.

This module defines API views for buddy matching and buddy requests.
"""

from rest_framework import views, status, permissions, generics
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .services import get_buddy_matches
from .models import BuddyRequest
from .serializers import (
    BuddyMatchSerializer,
    BuddyRequestSerializer,
    BuddyRequestCreateSerializer,
    BuddyRequestActionSerializer,
)
from apps.notifications.models import Notification


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


class BuddyRequestListCreateView(views.APIView):
    """
    GET /api/buddies/requests/
        Returns incoming and outgoing buddy requests for the authenticated user.
        
        Query Parameters:
            type: 'incoming' | 'outgoing' | 'all' (default: 'all')
            status: 'pending' | 'accepted' | 'rejected' (optional)
    
    POST /api/buddies/requests/
        Sends a buddy request to another user.
        
        Request Body:
            receiver_id: ID of the user to send the request to
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        request_type = request.query_params.get('type', 'all')
        status_filter = request.query_params.get('status')

        # Build queryset based on type
        if request_type == 'incoming':
            queryset = BuddyRequest.objects.filter(receiver=user)
        elif request_type == 'outgoing':
            queryset = BuddyRequest.objects.filter(sender=user)
        else:
            # All requests where user is sender or receiver
            from django.db.models import Q
            queryset = BuddyRequest.objects.filter(
                Q(sender=user) | Q(receiver=user)
            )

        # Apply status filter if provided
        if status_filter and status_filter in ['pending', 'accepted', 'rejected']:
            queryset = queryset.filter(status=status_filter)

        # Optimize queries
        queryset = queryset.select_related('sender', 'receiver')

        serializer = BuddyRequestSerializer(queryset, many=True)
        
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = BuddyRequestCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            buddy_request = serializer.save()
            
            # Create notification for receiver
            Notification.create_buddy_request_received(
                receiver=buddy_request.receiver,
                sender=buddy_request.sender,
                buddy_request_id=buddy_request.id
            )
            
            response_serializer = BuddyRequestSerializer(buddy_request)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BuddyRequestAcceptView(views.APIView):
    """
    POST /api/buddies/requests/<id>/accept/
    
    Accepts a pending buddy request.
    Only the receiver can accept.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        buddy_request = get_object_or_404(
            BuddyRequest.objects.select_related('sender', 'receiver'),
            pk=pk
        )
        
        serializer = BuddyRequestActionSerializer(
            data={'action': 'accept'},
            context={'request': request, 'buddy_request': buddy_request}
        )
        
        if serializer.is_valid():
            updated_request = serializer.save()
            
            # Create notification for sender that their request was accepted
            Notification.create_buddy_request_accepted(
                sender=updated_request.sender,
                receiver=updated_request.receiver,
                buddy_request_id=updated_request.id
            )
            
            response_serializer = BuddyRequestSerializer(updated_request)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BuddyRequestRejectView(views.APIView):
    """
    POST /api/buddies/requests/<id>/reject/
    
    Rejects a pending buddy request.
    Only the receiver can reject.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        buddy_request = get_object_or_404(
            BuddyRequest.objects.select_related('sender', 'receiver'),
            pk=pk
        )
        
        serializer = BuddyRequestActionSerializer(
            data={'action': 'reject'},
            context={'request': request, 'buddy_request': buddy_request}
        )
        
        if serializer.is_valid():
            updated_request = serializer.save()
            
            # Create notification for sender that their request was rejected
            Notification.create_buddy_request_rejected(
                sender=updated_request.sender,
                receiver=updated_request.receiver,
                buddy_request_id=updated_request.id
            )
            
            response_serializer = BuddyRequestSerializer(updated_request)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcceptedBuddiesListView(views.APIView):
    """
    GET /api/buddies/accepted/
    
    Returns a list of accepted buddies (confirmed connections) for the user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        from django.db.models import Q
        
        # Get all accepted requests where user is sender or receiver
        accepted_requests = BuddyRequest.objects.filter(
            Q(sender=user) | Q(receiver=user),
            status=BuddyRequest.Status.ACCEPTED
        ).select_related('sender', 'receiver')

        # Extract buddy info
        buddies = []
        for req in accepted_requests:
            # The buddy is the other person in the request
            buddy = req.receiver if req.sender == user else req.sender
            buddies.append({
                'id': buddy.id,
                'full_name': buddy.full_name,
                'email': buddy.email,
                'connected_at': req.updated_at,
            })

        return Response({
            'count': len(buddies),
            'results': buddies
        }, status=status.HTTP_200_OK)


class BuddyRequestCancelView(views.APIView):
    """
    DELETE /api/buddies/requests/<id>/cancel/
    
    Cancels a pending buddy request.
    Only the sender can cancel.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        buddy_request = get_object_or_404(
            BuddyRequest,
            pk=pk,
            sender=request.user
        )
        
        if buddy_request.status != BuddyRequest.Status.PENDING:
            return Response(
                {'error': 'Can only cancel pending requests.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        buddy_request.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
