from django.contrib import admin
from .models import Destination, TripSavedDestination, DestinationImageCache, TripRecommendationCache


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'country', 'category', 'is_active']
    list_filter = ['category', 'is_active', 'country']
    search_fields = ['name', 'city', 'country']
    ordering = ['name']


@admin.register(TripSavedDestination)
class TripSavedDestinationAdmin(admin.ModelAdmin):
    list_display = ['trip', 'destination', 'saved_by', 'saved_at']
    list_filter = ['saved_at']
    search_fields = ['trip__title', 'destination__name', 'saved_by__email']
    ordering = ['-saved_at']
    raw_id_fields = ['trip', 'destination', 'saved_by']


@admin.register(DestinationImageCache)
class DestinationImageCacheAdmin(admin.ModelAdmin):
    list_display = ['query', 'image_source', 'created_at']
    list_filter = ['image_source', 'created_at']
    search_fields = ['query']
    ordering = ['-created_at']
    readonly_fields = ['created_at']


@admin.register(TripRecommendationCache)
class TripRecommendationCacheAdmin(admin.ModelAdmin):
    list_display = ['trip', 'status', 'last_generated', 'expires_at', 'is_expired']
    list_filter = ['status', 'last_generated', 'expires_at']
    search_fields = ['trip__title', 'trip__city']
    ordering = ['-last_generated']
    readonly_fields = ['created_at', 'last_generated']
    
    def is_expired(self, obj):
        """Display if cache is expired."""
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
