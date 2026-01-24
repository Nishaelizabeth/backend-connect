from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    path('', views.TripListCreateAPIView.as_view(), name='trip-list-create'),
    path('invitations/', views.InvitationsListAPIView.as_view(), name='invitations-list'),
    path('<int:pk>/accept/', views.AcceptTripAPIView.as_view(), name='trip-accept'),
    path('<int:pk>/reject/', views.RejectTripAPIView.as_view(), name='trip-reject'),
]
