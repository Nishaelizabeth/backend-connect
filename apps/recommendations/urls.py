from django.urls import path
from .views import (
    TripRecommendationsView,
    SaveDestinationView,
    TripSavedDestinationsView,
)

app_name = 'recommendations'

urlpatterns = [
    path(
        '<int:trip_id>/recommendations/',
        TripRecommendationsView.as_view(),
        name='trip-recommendations'
    ),
    path(
        '<int:trip_id>/save-destination/',
        SaveDestinationView.as_view(),
        name='save-destination'
    ),
    path(
        '<int:trip_id>/saved-destinations/',
        TripSavedDestinationsView.as_view(),
        name='saved-destinations'
    ),
]
