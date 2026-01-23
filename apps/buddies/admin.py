"""
Buddies app admin configuration.
"""

from django.contrib import admin
from .models import BuddyMatch


@admin.register(BuddyMatch)
class BuddyMatchAdmin(admin.ModelAdmin):
    """
    Admin configuration for BuddyMatch model.
    """
    list_display = [
        'id',
        'user',
        'matched_user',
        'match_score',
        'created_at',
        'updated_at',
    ]
    list_filter = [
        'created_at',
        'updated_at',
    ]
    search_fields = [
        'user__email',
        'user__full_name',
        'matched_user__email',
        'matched_user__full_name',
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-match_score', '-created_at']
    
    fieldsets = (
        ('Match Information', {
            'fields': ('user', 'matched_user', 'match_score')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
