"""
Notifications app views.

This module defines API views for notifications.
"""

from rest_framework import views, status, permissions
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(views.APIView):
    """
    GET /api/notifications/
    
    Returns notifications for the authenticated user.
    Ordered by newest first.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        
        return Response({
            'count': notifications.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class MarkAllNotificationsReadView(views.APIView):
    """
    POST /api/notifications/mark-all-read/
    
    Marks all notifications as read for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        
        return Response({
            'message': 'All notifications marked as read.',
            'updated_count': updated_count
        }, status=status.HTTP_200_OK)
