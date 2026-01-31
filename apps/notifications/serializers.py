"""
Notifications app serializers.

This module defines serializers for the Notification model.
"""

from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model.
    
    Used for listing notifications.
    """
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'type',
            'message',
            'is_read',
            'related_object_id',
            'metadata',
            'created_at',
        ]
        read_only_fields = fields
