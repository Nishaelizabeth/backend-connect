"""
AI Travel Assistant URLs.
"""

from django.urls import path
from .views import (
    AssistantChatView,
    AssistantConversationsView,
    AssistantConversationDetailView,
    AssistantStatusView,
)

app_name = 'assistant'

urlpatterns = [
    path('chat/', AssistantChatView.as_view(), name='chat'),
    path('status/', AssistantStatusView.as_view(), name='status'),
    path('conversations/', AssistantConversationsView.as_view(), name='conversations'),
    path('conversations/<int:conversation_id>/', AssistantConversationDetailView.as_view(), name='conversation-detail'),
]
