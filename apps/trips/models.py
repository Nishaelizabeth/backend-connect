from django.db import models
from django.conf import settings


class Trip(models.Model):
    class Status(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        UPCOMING = 'upcoming', 'Upcoming'
        COMPLETED = 'completed', 'Completed'

    title = models.CharField(max_length=200)
    
    # Legacy field - deprecated, kept for backward compatibility
    destination = models.CharField(max_length=200, blank=True, default='')
    
    # New precise location fields
    city = models.CharField(max_length=100, blank=True, default='')
    region = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, default='')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    start_date = models.DateField()
    end_date = models.DateField()
    cover_image = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text='URL of the trip cover image'
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_trips'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return f"{self.title} ({self.start_date} → {self.end_date})"
    
    @property
    def display_destination(self) -> str:
        """Returns formatted destination string for display."""
        if self.city and self.country:
            if self.region:
                return f"{self.city}, {self.region}, {self.country}"
            return f"{self.city}, {self.country}"
        return self.destination or ''
    
    def save(self, *args, **kwargs):
        # Auto-populate legacy destination field for backward compatibility
        if self.city and self.country and not self.destination:
            self.destination = self.display_destination
        super().save(*args, **kwargs)


class TripMember(models.Model):
    class Role(models.TextChoices):
        CREATOR = 'creator', 'Creator'
        MEMBER = 'member', 'Member'

    class MembershipStatus(models.TextChoices):
        INVITED = 'invited', 'Invited'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trip_memberships'
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=20, choices=MembershipStatus.choices, default=MembershipStatus.INVITED)
    joined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('trip', 'user')

    def __str__(self):
        return f"{self.user} in {self.trip} ({self.status})"


class TripWeatherCache(models.Model):
    """
    Cached weather data for trips.
    Prevents excessive API calls by caching weather for configurable duration.
    """
    trip = models.OneToOneField(
        Trip,
        on_delete=models.CASCADE,
        related_name='weather_cache'
    )
    temperature = models.IntegerField(
        help_text='Temperature in Celsius'
    )
    condition = models.CharField(
        max_length=50,
        help_text='Weather condition (e.g., Clear, Clouds, Rain)'
    )
    description = models.CharField(
        max_length=100,
        help_text='Detailed weather description'
    )
    icon = models.CharField(
        max_length=10,
        help_text='OpenWeather icon code'
    )
    city_name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='City name from weather API'
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text='When the cache was last updated'
    )

    class Meta:
        verbose_name = 'Trip Weather Cache'
        verbose_name_plural = 'Trip Weather Caches'

    def __str__(self):
        return f"Weather for {self.trip.title}: {self.temperature}°C, {self.condition}"
