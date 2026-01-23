"""
Buddies app admin configuration.
"""

from django.contrib import admin
from .models import BuddyMatch, BuddyRequest


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


@admin.register(BuddyRequest)
class BuddyRequestAdmin(admin.ModelAdmin):
    """
    Admin configuration for BuddyRequest model.
    """
    list_display = [
        'id',
        'sender',
        'receiver',
        'status',
        'created_at',
        'updated_at',
    ]
    list_filter = [
        'status',
        'created_at',
        'updated_at',
    ]
    search_fields = [
        'sender__email',
        'sender__full_name',
        'receiver__email',
        'receiver__full_name',
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    list_editable = ['status']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('sender', 'receiver', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
