"""
AI Travel Assistant Models.

Stores conversation history for the AI assistant.
"""

from django.db import models
from django.conf import settings


class ChatbotConversation(models.Model):
    """
    Represents a conversation session between a user and the AI assistant.
    A user can have multiple conversations over time.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assistant_conversations',
        help_text='The user this conversation belongs to'
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text='Auto-generated title based on first message'
    )
    last_buddy_offset = models.IntegerField(
        default=0,
        help_text='Pagination offset for buddy suggestions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Assistant Conversation'
        verbose_name_plural = 'Assistant Conversations'

    def __str__(self):
        return f"Conversation {self.id} - {self.user.email}"


class ChatbotMessage(models.Model):
    """
    Individual message within an assistant conversation.
    Stores both user messages and AI assistant responses.
    """
    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'

    conversation = models.ForeignKey(
        ChatbotConversation,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text='The conversation this message belongs to'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        help_text='Whether this message is from the user or assistant'
    )
    content = models.TextField(
        help_text='The message content'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Assistant Message'
        verbose_name_plural = 'Assistant Messages'

    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"[{self.role}] {preview}"
