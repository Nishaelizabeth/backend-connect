from django.urls import path
from .views import ChatMessagesView, PollCreateView, PollVoteView, PollCloseView

app_name = 'chat'

urlpatterns = [
    path('<int:trip_id>/chat/messages/', ChatMessagesView.as_view(), name='chat-messages'),
    path('<int:trip_id>/chat/polls/', PollCreateView.as_view(), name='poll-create'),
    path('<int:trip_id>/chat/polls/<int:poll_id>/vote/', PollVoteView.as_view(), name='poll-vote'),
    path('<int:trip_id>/chat/polls/<int:poll_id>/close/', PollCloseView.as_view(), name='poll-close'),
]
