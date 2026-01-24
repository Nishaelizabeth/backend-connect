from django.contrib import admin
from .models import Trip, TripMember


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('title', 'destination', 'creator', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'start_date')
    search_fields = ('title', 'destination', 'creator__email')


@admin.register(TripMember)
class TripMemberAdmin(admin.ModelAdmin):
    list_display = ('trip', 'user', 'role', 'status')
    list_filter = ('role', 'status')
    search_fields = ('trip__title', 'user__email')
