from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.trips.models import Trip
from .models import ChatRoom, Message
from .serializers import MessageSerializer, MessageCreateSerializer
from .permissions import IsTripMemberAccepted


class ChatMessagesView(APIView):
    """
    GET: Retrieve last 50 messages for a trip's chat room.
    POST: Send a new message (REST fallback for WebSocket).
    """
    permission_classes = [IsAuthenticated, IsTripMemberAccepted]

    def get(self, request, trip_id):
        """
        Get the most recent 50 messages for the trip chat.
        """
        trip = get_object_or_404(Trip, id=trip_id)
        
        # Get or create chat room (in case signal didn't fire for old trips)
        chat_room, _ = ChatRoom.objects.get_or_create(trip=trip)
        
        # Get last 50 messages, ordered by created_at ascending
        messages = chat_room.messages.select_related('sender').order_by('-created_at')[:50]
        # Reverse to show oldest first in the list
        messages = list(reversed(messages))
        
        serializer = MessageSerializer(
            messages, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'room_id': chat_room.id,
            'trip_id': trip.id,
            'trip_title': trip.title,
            'messages': serializer.data
        })

    def post(self, request, trip_id):
        """
        Send a new message via REST API (fallback for WebSocket).
        """
        trip = get_object_or_404(Trip, id=trip_id)
        chat_room, _ = ChatRoom.objects.get_or_create(trip=trip)
        
        serializer = MessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Create the message
        message = Message.objects.create(
            room=chat_room,
            sender=request.user,
            content=serializer.validated_data['content'],
            is_system=False
        )
        
        # Return the created message
        response_serializer = MessageSerializer(
            message,
            context={'request': request}
        )
        
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
