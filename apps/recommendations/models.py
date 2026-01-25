from django.db import models
from django.contrib.auth import get_user_model
from apps.trips.models import Trip

User = get_user_model()


class Destination(models.Model):
    class Category(models.TextChoices):
        NATURE = 'nature', 'Nature'
        CULTURE = 'culture', 'Culture'
        ADVENTURE = 'adventure', 'Adventure'
        FOOD = 'food', 'Food'
        LEISURE = 'leisure', 'Leisure'

    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField()
    image_url = models.URLField(max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.city}, {self.country})"


class TripSavedDestination(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='saved_destinations'
    )
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name='trip_saves'
    )
    saved_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_destinations'
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trip', 'destination')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.destination.name} saved in {self.trip.title}"
