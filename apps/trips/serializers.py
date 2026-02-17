from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers

from .models import Trip, TripMember
from apps.buddies.models import BuddyRequest
from apps.notifications.models import Notification

User = get_user_model()


class TripMemberNestedSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField(source='id')
    id = serializers.IntegerField(source='user.id')
    full_name = serializers.CharField(source='user.full_name')
    email = serializers.EmailField(source='user.email')
    role = serializers.CharField()
    status = serializers.CharField()
    joined_at = serializers.DateTimeField(allow_null=True)


class TripCreateSerializer(serializers.ModelSerializer):
    invited_user_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    city = serializers.CharField(max_length=100, required=True)
    region = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    country = serializers.CharField(max_length=100, required=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = Trip
        fields = (
            'id', 'title', 'city', 'region', 'country', 
            'latitude', 'longitude', 'start_date', 'end_date', 
            'invited_user_ids', 'cover_image'
        )

    def validate(self, data):
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end and start >= end:
            raise serializers.ValidationError('start_date must be before end_date')

        # Validate invited users are connected buddies
        invited = data.get('invited_user_ids', [])
        request = self.context.get('request')
        creator = request.user if request else None

        if invited and creator:
            for uid in set(invited):
                if uid == getattr(creator, 'id'):
                    raise serializers.ValidationError('Creator cannot be invited')

                connected = BuddyRequest.objects.filter(
                    (Q(sender=creator) & Q(receiver_id=uid) | Q(sender_id=uid) & Q(receiver=creator))
                    & Q(status=BuddyRequest.Status.ACCEPTED)
                ).exists()
                if not connected:
                    raise serializers.ValidationError(f'User {uid} is not a connected buddy')

        return data

    def create(self, validated_data):
        invited = validated_data.pop('invited_user_ids', [])
        request = self.context.get('request')
        creator = request.user
        
        # Build destination string for backward compatibility
        city = validated_data.get('city', '')
        region = validated_data.get('region', '')
        country = validated_data.get('country', '')
        
        if region:
            validated_data['destination'] = f"{city}, {region}, {country}"
        else:
            validated_data['destination'] = f"{city}, {country}"

        trip = Trip.objects.create(creator=creator, **validated_data)

        # Creator as accepted member
        TripMember.objects.create(
            trip=trip,
            user=creator,
            role=TripMember.Role.CREATOR,
            status=TripMember.MembershipStatus.ACCEPTED,
            joined_at=timezone.now()
        )

        # Invite other members
        for uid in set(invited):
            try:
                user = User.objects.get(id=uid)
            except User.DoesNotExist:
                continue

            TripMember.objects.create(
                trip=trip,
                user=user,
                role=TripMember.Role.MEMBER,
                status=TripMember.MembershipStatus.INVITED
            )

            # Notification: trip invitation sent (for creator)
            Notification.create_trip_invite_sent(
                sender=creator,
                receiver=user,
                trip=trip
            )

            # Notification: trip invitation received (for invited user)
            Notification.create_trip_invite_received(
                receiver=user,
                sender=creator,
                trip=trip
            )

        return trip


class TripListSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    creator_id = serializers.IntegerField(source='creator.id', read_only=True)
    destination = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = (
            'id', 'title', 'destination', 'city', 'region', 'country',
            'latitude', 'longitude', 'start_date', 'end_date', 
            'status', 'member_count', 'cover_image', 'creator_id'
        )

    def get_member_count(self, obj):
        return obj.members.filter(status=TripMember.MembershipStatus.ACCEPTED).count()
    
    def get_destination(self, obj):
        return obj.display_destination or obj.destination
    
    def get_status(self, obj):
        """Calculate status based on trip dates"""
        from datetime import date
        today = date.today()
        
        # If end date has passed, mark as completed
        if obj.end_date < today:
            return 'completed'
        
        # If start date is in the future, mark as upcoming
        if obj.start_date > today:
            return 'upcoming'
        
        # If currently on the trip (between start and end dates)
        return 'planned'


class TripDetailSerializer(serializers.ModelSerializer):
    members = TripMemberNestedSerializer(many=True)
    creator_id = serializers.IntegerField(source='creator.id', read_only=True)
    destination = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = (
            'id', 'title', 'destination', 'city', 'region', 'country',
            'latitude', 'longitude', 'start_date', 'end_date', 
            'status', 'created_at', 'members', 'cover_image', 'creator_id'
        )
    
    def get_destination(self, obj):
        return obj.display_destination or obj.destination
    
    def get_status(self, obj):
        """Calculate status based on trip dates"""
        from datetime import date
        today = date.today()
        
        # If end date has passed, mark as completed
        if obj.end_date < today:
            return 'completed'
        
        # If start date is in the future, mark as upcoming
        if obj.start_date > today:
            return 'upcoming'
        
        # If currently on the trip (between start and end dates)
        return 'planned'


class TripInvitationSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField(source='id')
    trip_id = serializers.IntegerField(source='trip.id')
    title = serializers.CharField(source='trip.title')
    destination = serializers.SerializerMethodField()
    city = serializers.CharField(source='trip.city')
    region = serializers.CharField(source='trip.region')
    country = serializers.CharField(source='trip.country')
    start_date = serializers.DateField(source='trip.start_date')
    end_date = serializers.DateField(source='trip.end_date')
    creator_id = serializers.IntegerField(source='trip.creator.id')
    creator_name = serializers.CharField(source='trip.creator.full_name')
    status = serializers.CharField()
    joined_at = serializers.DateTimeField(allow_null=True)
    
    def get_destination(self, obj):
        return obj.trip.display_destination or obj.trip.destination


# =============================================================================
# ITINERARY SERIALIZERS
# =============================================================================

class ItineraryDestinationSerializer(serializers.Serializer):
    """Nested destination info for itinerary items."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    city = serializers.CharField()
    country = serializers.CharField()
    category = serializers.CharField()
    image_url = serializers.URLField(allow_null=True)
    lat = serializers.FloatField(allow_null=True)
    lon = serializers.FloatField(allow_null=True)


class ItineraryItemSerializer(serializers.Serializer):
    """Serializer for itinerary items."""
    id = serializers.IntegerField()
    destination = ItineraryDestinationSerializer()
    added_by_id = serializers.IntegerField(source='saved_by.id')
    added_by_name = serializers.CharField(source='saved_by.full_name')
    notes = serializers.CharField(allow_blank=True)
    position = serializers.IntegerField(source='order', allow_null=True)
    saved_at = serializers.DateTimeField()


class AddToItinerarySerializer(serializers.Serializer):
    """Serializer for adding a destination to itinerary."""
    destination_id = serializers.IntegerField()
    notes = serializers.CharField(allow_blank=True, required=False, default='')


class ReorderItinerarySerializer(serializers.Serializer):
    """Serializer for reordering itinerary items."""
    items = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),
        help_text='List of {id, position} objects'
    )
    
    def validate_items(self, value):
        for item in value:
            if 'id' not in item or 'position' not in item:
                raise serializers.ValidationError(
                    'Each item must have "id" and "position" fields'
                )
        return value


class UpdateItineraryNotesSerializer(serializers.Serializer):
    """Serializer for updating itinerary item notes."""
    notes = serializers.CharField(allow_blank=True)
