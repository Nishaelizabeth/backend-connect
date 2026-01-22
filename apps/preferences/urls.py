from django.urls import path
from .views import UserPreferenceView, InterestListView

app_name = 'preferences'

urlpatterns = [
    path('me/', UserPreferenceView.as_view(), name='user-preferences'),
    path('', UserPreferenceView.as_view(), name='create-update-preferences'),
    path('interests/', InterestListView.as_view(), name='interest-list'),
]
