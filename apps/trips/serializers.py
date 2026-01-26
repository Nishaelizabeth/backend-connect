from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers

from .models import Trip, TripMember
from apps.buddies.models import BuddyRequest
from apps.notifications.models import Notification

User = get_user_model()


class TripMemberNestedSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='user.id')
    full_name = serializers.CharField(source='user.full_name')
    email = serializers.EmailField(source='user.email')
    role = serializers.CharField()
    status = serializers.CharField()
    joined_at = serializers.DateTimeField(allow_null=True)


class TripCreateSerializer(serializers.ModelSerializer):
    invited_user_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = Trip
    class Meta:
        model = Trip
        fields = ('id', 'title', 'destination', 'start_date', 'end_date', 'invited_user_ids', 'cover_image')

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

            # Notification: trip invitation
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

    class Meta:
        model = Trip
    class Meta:
        model = Trip
        fields = ('id', 'title', 'destination', 'start_date', 'end_date', 'status', 'member_count', 'cover_image', 'creator_id')

    def get_member_count(self, obj):
        return obj.members.filter(status=TripMember.MembershipStatus.ACCEPTED).count()


class TripDetailSerializer(serializers.ModelSerializer):
    members = TripMemberNestedSerializer(many=True)

    class Meta:
        model = Trip
    class Meta:
        model = Trip
        fields = ('id', 'title', 'destination', 'start_date', 'end_date', 'status', 'created_at', 'members', 'cover_image')


class TripInvitationSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField(source='id')
    trip_id = serializers.IntegerField(source='trip.id')
    title = serializers.CharField(source='trip.title')
    destination = serializers.CharField(source='trip.destination')
    start_date = serializers.DateField(source='trip.start_date')
    end_date = serializers.DateField(source='trip.end_date')
    creator_id = serializers.IntegerField(source='trip.creator.id')
    creator_name = serializers.CharField(source='trip.creator.full_name')
    status = serializers.CharField()
    joined_at = serializers.DateTimeField(allow_null=True)
