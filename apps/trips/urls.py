from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    path('', views.TripListCreateAPIView.as_view(), name='trip-list-create'),
    path('<int:pk>/', views.TripDetailAPIView.as_view(), name='trip-detail'),
    path('<int:pk>/delete/', views.DeleteTripAPIView.as_view(), name='trip-delete'),
    path('<int:pk>/remove-member/<int:member_id>/', views.RemoveMemberAPIView.as_view(), name='trip-remove-member'),
    path('<int:pk>/invite/', views.InviteToTripAPIView.as_view(), name='trip-invite'),
    path('invitations/', views.InvitationsListAPIView.as_view(), name='invitations-list'),
    path('<int:pk>/accept/', views.AcceptTripAPIView.as_view(), name='trip-accept'),
    path('<int:pk>/reject/', views.RejectTripAPIView.as_view(), name='trip-reject'),
    path('<int:pk>/leave/', views.LeaveTripAPIView.as_view(), name='trip-leave'),
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    
    # Itinerary endpoints
    path('<int:trip_id>/itinerary/', views.TripItineraryListCreateView.as_view(), name='trip-itinerary-list-create'),
    path('<int:trip_id>/itinerary/<int:item_id>/', views.TripItineraryDetailView.as_view(), name='trip-itinerary-detail'),
    path('<int:trip_id>/itinerary/reorder/', views.TripItineraryReorderView.as_view(), name='trip-itinerary-reorder'),
]

