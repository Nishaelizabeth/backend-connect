"""
Buddies app URL configuration.
"""

from django.urls import path
from .views import (
    BuddyMatchListView,
    BuddyRequestListCreateView,
    BuddyRequestAcceptView,
    BuddyRequestRejectView,
    BuddyRequestCancelView,
    AcceptedBuddiesListView,
)

app_name = 'buddies'

urlpatterns = [
    # Matching endpoints
    path('matches/', BuddyMatchListView.as_view(), name='match-list'),
    
    # Request endpoints
    path('requests/', BuddyRequestListCreateView.as_view(), name='request-list-create'),
    path('requests/<int:pk>/accept/', BuddyRequestAcceptView.as_view(), name='request-accept'),
    path('requests/<int:pk>/reject/', BuddyRequestRejectView.as_view(), name='request-reject'),
    path('requests/<int:pk>/cancel/', BuddyRequestCancelView.as_view(), name='request-cancel'),
    
    # Accepted buddies
    path('accepted/', AcceptedBuddiesListView.as_view(), name='accepted-list'),
]
