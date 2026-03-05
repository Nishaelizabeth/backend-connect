from django.urls import path
from . import views

app_name = 'adminpanel'

urlpatterns = [
    path('dashboard/', views.AdminDashboardView.as_view(), name='dashboard'),
    path('users/', views.AdminUserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.AdminUserDetailView.as_view(), name='user-detail'),
    path('trips/', views.AdminTripListView.as_view(), name='trip-list'),
    path('orders/', views.AdminOrderListView.as_view(), name='order-list'),
    path('chatrooms/', views.AdminChatRoomListView.as_view(), name='chatroom-list'),
    path('messages/', views.AdminMessageListView.as_view(), name='message-list'),
    path('notifications/', views.AdminNotificationListView.as_view(), name='notification-list'),
    path('categories/', views.AdminCategoryListView.as_view(), name='category-list'),
    path('products/', views.AdminProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', views.AdminProductDetailView.as_view(), name='product-detail'),
    path('buddies/', views.AdminBuddyListView.as_view(), name='buddy-list'),
]
