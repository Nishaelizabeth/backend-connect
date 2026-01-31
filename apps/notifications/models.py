"""
Notifications app models.

This module defines the Notification model for user notifications.
"""

from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Model representing a user notification.
    
    Notifications are created for various events like buddy requests.
    """
    
    class NotificationType(models.TextChoices):
        BUDDY_REQUEST_SENT = 'buddy_request_sent', 'Buddy Request Sent'
        BUDDY_REQUEST_RECEIVED = 'buddy_request_received', 'Buddy Request Received'
        BUDDY_REQUEST_ACCEPTED = 'buddy_request_accepted', 'Buddy Request Accepted'
        BUDDY_REQUEST_REJECTED = 'buddy_request_rejected', 'Buddy Request Rejected'
        BUDDY_DISCONNECTED = 'buddy_disconnected', 'Buddy Disconnected'
        TRIP_INVITE_SENT = 'trip_invite_sent', 'Trip Invite Sent'
        TRIP_INVITE_RECEIVED = 'trip_invite_received', 'Trip Invite Received'
        TRIP_INVITE_ACCEPTED = 'trip_invite_accepted', 'Trip Invite Accepted'
        TRIP_INVITE_REJECTED = 'trip_invite_rejected', 'Trip Invite Rejected'
        DESTINATION_SAVED = 'destination_saved', 'Destination Saved'
        MEMBER_LEFT_TRIP = 'member_left_trip', 'Member Left Trip'
        TRIP_MEMBER_REMOVED = 'trip_member_removed', 'Trip Member Removed'
        TRIP_CANCELLED = 'trip_cancelled', 'Trip Cancelled'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text='User who receives this notification'
    )
    type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        help_text='Type of notification'
    )
    message = models.TextField(
        help_text='Notification message content'
    )
    is_read = models.BooleanField(
        default=False,
        help_text='Whether the notification has been read'
    )
    related_object_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='ID of the related object (e.g., BuddyRequest ID, Trip ID)'
    )
    metadata = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Additional metadata for the notification (e.g., sender_id, buddy_request_id)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the notification was created'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.user.email} - {self.type} - {self.created_at}"

    @classmethod
    def create_buddy_request_received(cls, receiver, sender, buddy_request_id):
        """Create notification for receiver when they get a buddy request."""
        return cls.objects.create(
            user=receiver,
            type=cls.NotificationType.BUDDY_REQUEST_RECEIVED,
            message=f"{sender.full_name} sent you a buddy request.",
            related_object_id=buddy_request_id,
            metadata={
                'buddy_request_id': buddy_request_id,
                'sender_id': sender.id,
            }
        )

    @classmethod
    def create_buddy_request_accepted(cls, sender, receiver, buddy_request_id):
        """Create notification for sender when their request is accepted."""
        return cls.objects.create(
            user=sender,
            type=cls.NotificationType.BUDDY_REQUEST_ACCEPTED,
            message=f"{receiver.full_name} accepted your buddy request.",
            related_object_id=buddy_request_id
        )

    @classmethod
    def create_buddy_request_rejected(cls, sender, receiver, buddy_request_id):
        """Create notification for sender when their request is rejected."""
        return cls.objects.create(
            user=sender,
            type=cls.NotificationType.BUDDY_REQUEST_REJECTED,
            message=f"{receiver.full_name} declined your buddy request.",
            related_object_id=buddy_request_id
        )

    @classmethod
    def create_buddy_disconnected(cls, disconnected_user, disconnector):
        """Create notification for user when a buddy disconnects from them."""
        return cls.objects.create(
            user=disconnected_user,
            type=cls.NotificationType.BUDDY_DISCONNECTED,
            message=f"{disconnector.full_name} disconnected from you.",
            metadata={
                'disconnector_id': disconnector.id,
            }
        )

    @classmethod
    def create_trip_invite_sent(cls, sender, receiver, trip):
        """Create notification for sender when they send a trip invite."""
        return cls.objects.create(
            user=sender,
            type=cls.NotificationType.TRIP_INVITE_SENT,
            message=f"You invited {receiver.full_name} to {trip.title}.",
            related_object_id=trip.id
        )

    @classmethod
    def create_trip_invite_received(cls, receiver, sender, trip):
        """Create notification for receiver when they get a trip invite."""
        return cls.objects.create(
            user=receiver,
            type=cls.NotificationType.TRIP_INVITE_RECEIVED,
            message=f"{sender.full_name} invited you to join {trip.title}.",
            related_object_id=trip.id
        )

    @classmethod
    def create_trip_invite_accepted(cls, sender, receiver, trip):
        """Create notification for sender (creator) when invite is accepted."""
        return cls.objects.create(
            user=sender,
            type=cls.NotificationType.TRIP_INVITE_ACCEPTED,
            message=f"{receiver.full_name} accepted your invitation to {trip.title}.",
            related_object_id=trip.id
        )

    @classmethod
    def create_trip_invite_rejected(cls, sender, receiver, trip):
        """Create notification for sender (creator) when invite is rejected."""
        return cls.objects.create(
            user=sender,
            type=cls.NotificationType.TRIP_INVITE_REJECTED,
            message=f"{receiver.full_name} declined your invitation to {trip.title}.",
            related_object_id=trip.id
        )

    @classmethod
    def create_destination_saved(cls, user, destination, trip):
        """Create notification for destination save event."""
        return cls.objects.create(
            user=user,
            type=cls.NotificationType.DESTINATION_SAVED,
            message=f"{destination.name} was added to {trip.title}.",
            related_object_id=destination.id
        )

    @classmethod
    def create_member_left_trip(cls, user, member_name, trip):
        """Create notification when a member leaves the trip."""
        return cls.objects.create(
            user=user,
            type=cls.NotificationType.MEMBER_LEFT_TRIP,
            message=f"{member_name} left {trip.title}.",
            related_object_id=trip.id
        )

    @classmethod
    def create_trip_member_removed(cls, user, trip):
        """Create notification for member removed from trip."""
        return cls.objects.create(
            user=user,
            type=cls.NotificationType.TRIP_MEMBER_REMOVED,
            message=f"You have been removed from the trip {trip.title}.",
            related_object_id=trip.id
        )

    @classmethod
    def create_trip_cancelled(cls, user, trip_title):
        """Create notification for trip cancellation."""
        return cls.objects.create(
            user=user,
            type=cls.NotificationType.TRIP_CANCELLED,
            message=f"The trip {trip_title} has been cancelled by the creator.",
            # No related object ID since trip is deleted
            related_object_id=None
        )
