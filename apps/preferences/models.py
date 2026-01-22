from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Interest(models.Model):
    """
    Represents a specific travel interest (e.g., Beaches, Mountains, Food).
    """
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Interest')
        verbose_name_plural = _('Interests')

    def __str__(self):
        return self.name

class Preference(models.Model):
    """
    Stores user travel preferences.
    One-to-One relationship with the User model.
    """
    class BudgetRange(models.TextChoices):
        LOW = 'low', _('Low ($0 - $1000)')
        MEDIUM = 'medium', _('Medium ($1000 - $3000)')
        HIGH = 'high', _('High ($3000+)')

    class TravelStyle(models.TextChoices):
        SOLO = 'solo', _('Solo')
        GROUP = 'group', _('Group')
        FAMILY = 'family', _('Family')
        ADVENTURE = 'adventure', _('Adventure')
        LEISURE = 'leisure', _('Leisure')

    class Duration(models.TextChoices):
        WEEKEND = 'weekend', _('Weekend (2-3 days)')
        SHORT = 'short', _('Short (4-7 days)')
        LONG = 'long', _('Long (1-2 weeks+)')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferences'
    )
    budget_range = models.CharField(
        max_length=20,
        choices=BudgetRange.choices,
        help_text=_('Preferred budget range for trips')
    )
    travel_style = models.CharField(
        max_length=20,
        choices=TravelStyle.choices,
        help_text=_('Preferred travel style')
    )
    preferred_trip_duration = models.CharField(
        max_length=20,
        choices=Duration.choices,
        help_text=_('Preferred duration of trips')
    )
    interests = models.ManyToManyField(
        Interest,
        through='PreferenceInterest',
        related_name='preferences',
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('User Preference')
        verbose_name_plural = _('User Preferences')

    def __str__(self):
        return f"Preferences for {self.user.email}"

class PreferenceInterest(models.Model):
    """
    Through model for mapping Preferences to Interests.
    Allows for future scalability (e.g., adding weights/scores to interests).
    """
    preference = models.ForeignKey(Preference, on_delete=models.CASCADE)
    interest = models.ForeignKey(Interest, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('preference', 'interest')
        verbose_name = _('Preference Interest')
        verbose_name_plural = _('Preference Interests')

    def __str__(self):
        return f"{self.preference.user.email} - {self.interest.name}"
