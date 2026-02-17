"""
AI Travel Assistant Serializers.
"""

from rest_framework import serializers
from .models import ChatbotConversation, ChatbotMessage


class ChatbotMessageSerializer(serializers.ModelSerializer):
    """Serializer for assistant chat messages."""
    
    class Meta:
        model = ChatbotMessage
        fields = ['id', 'role', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']


class ChatbotConversationSerializer(serializers.ModelSerializer):
    """Serializer for assistant conversations with recent messages."""
    messages = ChatbotMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatbotConversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'message_count', 'messages']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()


class AssistantChatRequestSerializer(serializers.Serializer):
    """Serializer for incoming chat requests."""
    message = serializers.CharField(
        max_length=4000,
        help_text='User message to the assistant'
    )
    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='Optional: continue existing conversation'
    )


class AssistantChatResponseSerializer(serializers.Serializer):
    """Serializer for chat response."""
    reply = serializers.CharField()
    conversation_id = serializers.IntegerField()
    message_id = serializers.IntegerField()
