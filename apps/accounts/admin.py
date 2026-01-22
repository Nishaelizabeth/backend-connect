"""
Admin configuration for custom User model.

Provides a clean admin interface for managing users with:
- List view with key fields
- Search functionality
- Proper fieldsets for editing
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin configuration for the User model.
    
    Adapts Django's UserAdmin for email-based authentication.
    """
    
    # List display configuration
    list_display = (
        'email',
        'full_name',
        'auth_provider',
        'is_active',
        'is_staff',
        'date_joined',
    )
    list_filter = (
        'is_active',
        'is_staff',
        'is_superuser',
        'auth_provider',
        'date_joined',
    )
    search_fields = ('email', 'full_name')
    ordering = ('-date_joined',)
    
    # Fieldsets for the change user form
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        (_('Personal Info'), {
            'fields': ('full_name',)
        }),
        (_('Authentication'), {
            'fields': ('auth_provider',)
        }),
        (_('Permissions'), {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            ),
        }),
        (_('Important Dates'), {
            'fields': ('last_login', 'date_joined'),
        }),
    )
    
    # Fieldsets for the add user form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'full_name',
                'password1',
                'password2',
                'auth_provider',
                'is_active',
                'is_staff',
            ),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')
