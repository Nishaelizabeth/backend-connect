from django.urls import path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    path('ws/trips/<int:trip_id>/chat/', ChatConsumer.as_asgi()),
]
