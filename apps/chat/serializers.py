from rest_framework import serializers
from .models import ChatRoom, Message


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for chat messages.
    Includes sender details for display.
    """
    sender_id = serializers.IntegerField(source='sender.id', read_only=True, allow_null=True)
    sender_name = serializers.CharField(source='sender.full_name', read_only=True, allow_null=True)
    sender_avatar = serializers.SerializerMethodField()
    is_me = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id',
            'sender_id',
            'sender_name',
            'sender_avatar',
            'content',
            'created_at',
            'is_system',
            'is_me',
        ]
        read_only_fields = ['id', 'created_at', 'is_system']

    def get_sender_avatar(self, obj):
        # User model doesn't have avatar_url field
        # Return None for now - can be extended later
        return None

    def get_is_me(self, obj):
        request = self.context.get('request')
        if request and request.user and obj.sender:
            return request.user.id == obj.sender.id
        return False


class MessageCreateSerializer(serializers.Serializer):
    """
    Serializer for creating new messages via REST API.
    """
    content = serializers.CharField(max_length=2000)


class ChatRoomSerializer(serializers.ModelSerializer):
    """
    Serializer for chat room details.
    """
    trip_id = serializers.IntegerField(source='trip.id', read_only=True)
    trip_title = serializers.CharField(source='trip.title', read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'trip_id', 'trip_title', 'created_at', 'message_count']
        read_only_fields = ['id', 'created_at']

    def get_message_count(self, obj):
        return obj.messages.count()
