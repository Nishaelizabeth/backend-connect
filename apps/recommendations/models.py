from django.db import models
from django.contrib.auth import get_user_model
from apps.trips.models import Trip

User = get_user_model()


class Destination(models.Model):
    """
    Cached destination data from OpenTripMap or manual entry.
    """
    class Category(models.TextChoices):
        NATURE = 'nature', 'Nature'
        CULTURE = 'culture', 'Culture'
        ADVENTURE = 'adventure', 'Adventure'
        FOOD = 'food', 'Food'
        LEISURE = 'leisure', 'Leisure'

    # OpenTripMap identifier (unique for API-sourced destinations)
    xid = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, blank=True, default='')
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(blank=True, default='')
    image_url = models.URLField(max_length=500, null=True, blank=True)
    
    # Coordinates
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    
    # Metadata
    kinds = models.CharField(max_length=500, blank=True, default='', help_text='OpenTripMap kinds/tags')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.city})"
    
    @classmethod
    def get_or_create_from_opentripmap(cls, data: dict) -> 'Destination':
        """
        Get or create a destination from OpenTripMap data.
        
        Args:
            data: Dictionary with xid, name, image, category, lat, lon, etc.
            
        Returns:
            Destination instance
        """
        xid = data.get('xid')
        if not xid:
            raise ValueError("xid is required for OpenTripMap destinations")
        
        destination, created = cls.objects.update_or_create(
            xid=xid,
            defaults={
                'name': data.get('name', 'Unknown'),
                'city': data.get('city', ''),
                'category': data.get('category', 'culture'),
                'description': data.get('short_description', ''),
                'image_url': data.get('image', ''),
                'lat': data.get('lat'),
                'lon': data.get('lon'),
                'kinds': data.get('kinds', ''),
            }
        )
        return destination


class TripSavedDestination(models.Model):
    """
    Junction table for destinations saved to trips.
    """
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
    
    # Optional: order for itinerary
    order = models.PositiveIntegerField(null=True, blank=True)
    
    # Optional: notes from the user who saved it
    notes = models.TextField(blank=True, default='')

    class Meta:
        unique_together = ('trip', 'destination')
        ordering = ['order', '-saved_at']

    def __str__(self):
        return f"{self.destination.name} saved in {self.trip.title}"


class DestinationImageCache(models.Model):
    """
    Cache for Unsplash image lookups to avoid repeated API calls.
    Stores the resolved image URL for a given search query.
    """
    query = models.CharField(
        max_length=500,
        unique=True,
        db_index=True,
        help_text='Search query used for Unsplash lookup'
    )
    image_url = models.URLField(
        max_length=1000,
        help_text='Resolved image URL from Unsplash'
    )
    image_source = models.CharField(
        max_length=20,
        default='unsplash',
        help_text='Source of the image: unsplash or fallback'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Destination Image Cache'
        verbose_name_plural = 'Destination Image Caches'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Cache: {self.query[:50]}"
