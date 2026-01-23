"""
Buddies app configuration.
"""

from django.apps import AppConfig


class BuddiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.buddies'
    verbose_name = 'Buddy Matching'
