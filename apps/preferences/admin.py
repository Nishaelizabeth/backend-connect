from django.contrib import admin
from .models import Preference, Interest, PreferenceInterest

class PreferenceInterestInline(admin.TabularInline):
    model = PreferenceInterest
    extra = 1

@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_active',)

@admin.register(Preference)
class PreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'budget_range', 'travel_style', 'preferred_trip_duration', 'created_at')
    search_fields = ('user__email', 'user__full_name')
    list_filter = ('budget_range', 'travel_style', 'preferred_trip_duration')
    inlines = [PreferenceInterestInline]
