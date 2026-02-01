from django.urls import path
from .views import ChatMessagesView

app_name = 'chat'

urlpatterns = [
    path('<int:trip_id>/chat/messages/', ChatMessagesView.as_view(), name='chat-messages'),
]
