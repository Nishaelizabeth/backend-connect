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
        help_text='ID of the related object (e.g., BuddyRequest ID)'
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
            related_object_id=buddy_request_id
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
