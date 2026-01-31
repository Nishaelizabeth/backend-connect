"""
Buddies app models.

This module defines the BuddyMatch model for storing computed
compatibility scores between users.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class BuddyMatch(models.Model):
    """
    Represents a computed compatibility match between two users.
    
    This model stores the match score between a user and a potential
    travel buddy. Scores are computed based on shared interests,
    budget range, travel style, and trip duration preferences.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matches_as_user',
        help_text=_('The user seeking matches')
    )
    matched_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matches_as_matched_user',
        help_text=_('The matched potential buddy')
    )
    match_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text=_('Compatibility score from 0 to 100')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Buddy Match')
        verbose_name_plural = _('Buddy Matches')
        unique_together = ('user', 'matched_user')
        ordering = ['-match_score', '-created_at']

    def __str__(self):
        return f"{self.user.email} → {self.matched_user.email} ({self.match_score:.1f}%)"


class BuddyRequest(models.Model):
    """
    Represents a buddy request between two users.
    
    Allows users to send connection requests to potential travel buddies.
    Receivers can accept or reject the request.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        ACCEPTED = 'accepted', _('Accepted')
        REJECTED = 'rejected', _('Rejected')
    
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_buddy_requests',
        help_text=_('User who sent the request')
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_buddy_requests',
        help_text=_('User who received the request')
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=_('Current status of the request')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Buddy Request')
        verbose_name_plural = _('Buddy Requests')
        unique_together = ('sender', 'receiver')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender.email} → {self.receiver.email} ({self.status})"

