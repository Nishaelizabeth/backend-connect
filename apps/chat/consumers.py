"""
WebSocket consumer for real-time trip chat.
Handles connection, message sending, and group broadcasting.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from asgiref.sync import sync_to_async

from .models import ChatRoom, Message
from .permissions import is_accepted_trip_member


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for trip chat rooms.
    
    Connection: ws://localhost:8000/ws/trips/{trip_id}/chat/?token=<jwt>
    
    Inbound messages:
    {
        "type": "chat_message",
        "content": "Hello everyone!"
    }
    
    Outbound messages:
    {
        "type": "chat_message",
        "message": {
            "id": 1,
            "sender_id": 123,
            "sender_name": "John Doe",
            "sender_avatar": "http://...",
            "content": "Hello everyone!",
            "created_at": "2026-02-01T10:00:00Z",
            "is_system": false
        }
    }
    """
    
    async def connect(self):
        """
        Handle WebSocket connection.
        Validates user authentication and trip membership.
        """
        self.trip_id = self.scope['url_route']['kwargs']['trip_id']
        self.room_group_name = f'trip_{self.trip_id}'
        self.user = self.scope.get('user')
        
        # Reject anonymous users
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            await self.close(code=4001)  # Unauthorized
            return
        
        # Check if user is an accepted trip member
        is_member = await self.check_trip_membership()
        if not is_member:
            await self.close(code=4003)  # Forbidden
            return
        
        # Join the room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection success message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to chat',
            'user_id': self.user.id,
            'trip_id': self.trip_id
        }))
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        Leave the room group.
        """
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages.
        """
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
            return
        
        message_type = data.get('type', 'chat_message')
        
        if message_type == 'chat_message':
            await self.handle_chat_message(data)
        elif message_type == 'typing':
            await self.handle_typing(data)
        else:
            await self.send_error(f"Unknown message type: {message_type}")
    
    async def handle_chat_message(self, data):
        """
        Handle incoming chat messages.
        Save to database and broadcast to group.
        """
        content = data.get('content', '').strip()
        
        if not content:
            await self.send_error("Message content cannot be empty")
            return
        
        if len(content) > 2000:
            await self.send_error("Message too long (max 2000 characters)")
            return
        
        # Save message to database
        message = await self.save_message(content)
        
        if not message:
            await self.send_error("Failed to save message")
            return
        
        # Format message for broadcast
        message_data = await self.format_message(message)
        
        # Broadcast to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_data
            }
        )
    
    async def handle_typing(self, data):
        """
        Handle typing indicator (optional feature).
        """
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_typing',
                'user_id': self.user.id,
                'user_name': self.user.full_name,
                'is_typing': is_typing
            }
        )
    
    async def chat_message(self, event):
        """
        Send chat message to WebSocket.
        Called when a message is broadcast to the group.
        """
        message = event['message']
        
        # Add is_me flag for the recipient
        message['is_me'] = message.get('sender_id') == self.user.id
        
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message
        }))
    
    async def user_typing(self, event):
        """
        Send typing indicator to WebSocket.
        """
        # Don't send to the typing user themselves
        if event['user_id'] == self.user.id:
            return
        
        await self.send(text_data=json.dumps({
            'type': 'user_typing',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'is_typing': event['is_typing']
        }))
    
    async def system_message(self, event):
        """
        Send system message to WebSocket (join/leave notifications).
        """
        await self.send(text_data=json.dumps({
            'type': 'system_message',
            'message': event['message']
        }))
    
    async def send_error(self, error_message):
        """
        Send error message to the client.
        """
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))
    
    @database_sync_to_async
    def check_trip_membership(self):
        """
        Check if user is an accepted member of the trip.
        """
        return is_accepted_trip_member(self.user, self.trip_id)
    
    @database_sync_to_async
    def save_message(self, content):
        """
        Save a new message to the database.
        """
        try:
            # Get or create chat room
            from apps.trips.models import Trip
            trip = Trip.objects.get(id=self.trip_id)
            chat_room, _ = ChatRoom.objects.get_or_create(trip=trip)
            
            # Create message
            message = Message.objects.create(
                room=chat_room,
                sender=self.user,
                content=content,
                is_system=False
            )
            return message
        except Exception as e:
            print(f"Error saving message: {e}")
            return None
    
    @database_sync_to_async
    def format_message(self, message):
        """
        Format message object for JSON serialization.
        """
        return {
            'id': message.id,
            'sender_id': message.sender.id if message.sender else None,
            'sender_name': message.sender.full_name if message.sender else 'System',
            'sender_avatar': None,  # User model doesn't have avatar field
            'content': message.content,
            'created_at': message.created_at.isoformat(),
            'is_system': message.is_system
        }
