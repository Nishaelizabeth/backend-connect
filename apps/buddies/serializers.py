"""
Buddies app serializers.

This module defines serializers for buddy matching API responses.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class MatchedUserSerializer(serializers.ModelSerializer):
    """
    Serializer for matched user basic information.
    """
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name']
        read_only_fields = fields


class BuddyMatchSerializer(serializers.Serializer):
    """
    Serializer for buddy match results.
    
    Represents a potential buddy match with compatibility score
    and shared interests.
    """
    matched_user_id = serializers.IntegerField(source='user.id')
    matched_user_name = serializers.CharField(source='user.full_name')
    matched_user_email = serializers.EmailField(source='user.email')
    shared_interests = serializers.ListField(
        child=serializers.CharField(),
        help_text='List of shared interest names'
    )
    match_score = serializers.FloatField(
        help_text='Compatibility score from 0-100'
    )

    class Meta:
        fields = [
            'matched_user_id',
            'matched_user_name',
            'matched_user_email',
            'shared_interests',
            'match_score',
        ]
