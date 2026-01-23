"""
Buddies app URL configuration.
"""

from django.urls import path
from .views import BuddyMatchListView

app_name = 'buddies'

urlpatterns = [
    path('matches/', BuddyMatchListView.as_view(), name='match-list'),
]
