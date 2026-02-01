from django.db import models
from django.conf import settings


class ChatRoom(models.Model):
    """
    Chat room for each trip - one-to-one relationship with Trip.
    Auto-created via signal when a Trip is created.
    """
    trip = models.OneToOneField(
        'trips.Trip',
        on_delete=models.CASCADE,
        related_name='chat_room'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"ChatRoom for {self.trip.title}"


class Message(models.Model):
    """
    Individual chat message within a room.
    Can be a user message or system message (join/leave notifications).
    """
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        null=True,
        blank=True  # Null for system messages
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        if self.is_system:
            return f"[System] {self.content[:50]}"
        return f"{self.sender.full_name}: {self.content[:50]}"
