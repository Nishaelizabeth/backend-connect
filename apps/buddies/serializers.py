"""
Buddies app serializers.

This module defines serializers for buddy matching and buddy requests.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import get_user_model
from django.db import models
from .models import BuddyRequest

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
    request_status = serializers.SerializerMethodField(
        help_text='Current status of buddy request: none, pending_outgoing, pending_incoming, accepted, rejected'
    )
    request_id = serializers.SerializerMethodField(
        help_text='ID of the associated buddy request if any'
    )

    class Meta:
        fields = [
            'matched_user_id',
            'matched_user_name',
            'matched_user_email',
            'shared_interests',
            'match_score',
            'request_status',
            'request_id',
        ]

    def get_request_status(self, obj):
        request = self.context.get('request')
        if not request:
            return 'none'
        
        user = request.user
        matched_user = obj['user']
        
        # Check if they have a connected BuddyMatch
        from .models import BuddyRequest, BuddyMatch
        
        # Check for existing match (connected or disconnected)
        buddy_match = BuddyMatch.objects.filter(
            (models.Q(user=user) & models.Q(matched_user=matched_user)) |
            (models.Q(user=matched_user) & models.Q(matched_user=user))
        ).first()
        
        # If they have a connected match, return 'accepted'
        if buddy_match and buddy_match.status == BuddyMatch.Status.CONNECTED:
            return 'accepted'
        
        # If they were disconnected, treat as if no connection exists
        # Check for buddy requests
        buddy_req = BuddyRequest.objects.filter(
            (models.Q(sender=user) & models.Q(receiver=matched_user)) |
            (models.Q(sender=matched_user) & models.Q(receiver=user))
        ).first()
        
        if not buddy_req:
            return 'none'
            
        if buddy_req.status == BuddyRequest.Status.ACCEPTED:
            # They accepted but might have disconnected
            if buddy_match and buddy_match.status == BuddyMatch.Status.DISCONNECTED:
                return 'none'
            return 'accepted'
        if buddy_req.status == BuddyRequest.Status.REJECTED:
             return 'rejected' 
        
        if buddy_req.status == BuddyRequest.Status.PENDING:
            if buddy_req.sender == user:
                return 'pending_outgoing'
            return 'pending_incoming'
            
        return 'none'

    def get_request_id(self, obj):
        request = self.context.get('request')
        if not request:
            return None
            
        user = request.user
        matched_user = obj['user']
        
        from .models import BuddyRequest
        buddy_req = BuddyRequest.objects.filter(
            (models.Q(sender=user) & models.Q(receiver=matched_user)) |
            (models.Q(sender=matched_user) & models.Q(receiver=user))
        ).first()
        
        return buddy_req.id if buddy_req else None


class BuddyRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for buddy requests.
    
    Used for listing and creating buddy requests.
    """
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    receiver_id = serializers.IntegerField(source='receiver.id', read_only=True)
    receiver_name = serializers.CharField(source='receiver.full_name', read_only=True)
    receiver_email = serializers.EmailField(source='receiver.email', read_only=True)

    class Meta:
        model = BuddyRequest
        fields = [
            'id',
            'sender_id',
            'sender_name',
            'sender_email',
            'receiver_id',
            'receiver_name',
            'receiver_email',
            'status',
            'created_at',
        ]
        read_only_fields = ['id', 'sender_id', 'sender_name', 'sender_email', 'status', 'created_at']


class BuddyRequestCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a buddy request.
    """
    receiver_id = serializers.IntegerField(
        help_text='ID of the user to send the request to'
    )

    def validate_receiver_id(self, value):
        sender = self.context['request'].user
        
        # Check if receiver exists
        try:
            receiver = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        
        # Prevent self-request
        if sender.id == value:
            raise serializers.ValidationError("You cannot send a request to yourself.")
        
        # Check if they have a disconnected buddy match
        from .models import BuddyMatch
        buddy_match = BuddyMatch.objects.filter(
            (models.Q(user=sender) & models.Q(matched_user=receiver)) |
            (models.Q(user=receiver) & models.Q(matched_user=sender))
        ).first()
        
        # If they were connected before, check if they're disconnected now
        if buddy_match and buddy_match.status == BuddyMatch.Status.DISCONNECTED:
            # Delete old accepted request if exists, to allow new request
            BuddyRequest.objects.filter(
                (models.Q(sender=sender) & models.Q(receiver=receiver)) |
                (models.Q(sender=receiver) & models.Q(receiver=sender))
            ).delete()
            # Allow the new request
            return value
        
        # Check for existing request (in either direction)
        existing_request = BuddyRequest.objects.filter(
            sender=sender, receiver=receiver
        ).first()
        
        if existing_request:
            # Only block if the request is pending or accepted (and not disconnected)
            if existing_request.status == BuddyRequest.Status.PENDING:
                raise serializers.ValidationError(
                    f"You have already sent a request to this user. Status: {existing_request.status}"
                )
            elif existing_request.status == BuddyRequest.Status.ACCEPTED:
                # Check if they're still connected
                if buddy_match and buddy_match.status == BuddyMatch.Status.CONNECTED:
                    raise serializers.ValidationError(
                        f"You are already connected with this user."
                    )
                # If not connected, allow new request (shouldn't reach here due to earlier check)
        
        # Check for reverse request
        reverse_request = BuddyRequest.objects.filter(
            sender=receiver, receiver=sender
        ).first()
        
        if reverse_request and reverse_request.status == BuddyRequest.Status.PENDING:
            raise serializers.ValidationError(
                f"This user has already sent you a request. Please accept or reject it first."
            )
        
        return value

    def create(self, validated_data):
        sender = self.context['request'].user
        receiver = User.objects.get(id=validated_data['receiver_id'])
        
        return BuddyRequest.objects.create(
            sender=sender,
            receiver=receiver,
            status=BuddyRequest.Status.PENDING
        )


class BuddyRequestActionSerializer(serializers.Serializer):
    """
    Serializer for accepting or rejecting a buddy request.
    """
    action = serializers.ChoiceField(
        choices=['accept', 'reject'],
        help_text='Action to perform on the request'
    )

    def validate(self, attrs):
        request = self.context['buddy_request']
        user = self.context['request'].user
        
        # Only receiver can accept/reject
        if request.receiver != user:
            raise serializers.ValidationError(
                "Only the receiver can accept or reject this request."
            )
        
        # Check if already processed
        if request.status != BuddyRequest.Status.PENDING:
            raise serializers.ValidationError(
                f"This request has already been {request.status}."
            )
        
        return attrs

    def save(self):
        action = self.validated_data['action']
        buddy_request = self.context['buddy_request']
        
        if action == 'accept':
            buddy_request.status = BuddyRequest.Status.ACCEPTED
        else:
            buddy_request.status = BuddyRequest.Status.REJECTED
        
        buddy_request.save()
        return buddy_request
