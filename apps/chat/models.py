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
    Can be a text message, system message, or poll message.
    """
    MESSAGE_TYPE_TEXT = 'text'
    MESSAGE_TYPE_POLL = 'poll'
    MESSAGE_TYPES = [
        (MESSAGE_TYPE_TEXT, 'Text'),
        (MESSAGE_TYPE_POLL, 'Poll'),
    ]

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
    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPES,
        default=MESSAGE_TYPE_TEXT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        if self.is_system:
            return f"[System] {self.content[:50]}"
        return f"{self.sender.full_name}: {self.content[:50]}"


class Poll(models.Model):
    """
    A poll attached to a chat message.
    Any accepted trip member can create a poll.
    """
    message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name='poll'
    )
    question = models.CharField(max_length=500)
    allow_multiple = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question[:50]


class PollOption(models.Model):
    """A single option within a poll."""
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text


class PollVote(models.Model):
    """A single vote cast by a user for a poll option."""
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes')
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='poll_votes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('poll', 'option', 'voter')]

    def __str__(self):
        return f"{self.voter.full_name} → {self.option.text}"
