from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from apps.trips.models import Trip
from .models import ChatRoom, Message, Poll, PollOption, PollVote
from .serializers import MessageSerializer, MessageCreateSerializer, PollSerializer
from .permissions import IsTripMemberAccepted


def _serialize_poll_for_ws(poll):
    """Format poll data for WebSocket broadcast (no user-specific vote data)."""
    voters_per_option = {}
    for vote in poll.votes.select_related('option').all():
        opt_id = str(vote.option_id)
        if opt_id not in voters_per_option:
            voters_per_option[opt_id] = []
        voters_per_option[opt_id].append(vote.voter_id)
    return {
        'id': poll.id,
        'message_id': poll.message_id,
        'question': poll.question,
        'allow_multiple': poll.allow_multiple,
        'is_closed': poll.is_closed,
        'options': [
            {'id': o.id, 'text': o.text, 'order': o.order, 'vote_count': o.votes.count()}
            for o in poll.options.all()
        ],
        'total_votes': poll.votes.values('voter').distinct().count(),
        'voters_per_option': voters_per_option,
    }


def _broadcast_poll_update(trip_id, poll):
    """Broadcast poll update to all connected WebSocket clients."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'trip_{trip_id}',
        {'type': 'poll_update', 'poll': _serialize_poll_for_ws(poll)}
    )


class ChatMessagesView(APIView):
    """
    GET: Retrieve last 50 messages for a trip's chat room.
    POST: Send a new message (REST fallback for WebSocket).
    """
    permission_classes = [IsAuthenticated, IsTripMemberAccepted]

    def get(self, request, trip_id):
        """Get the most recent 50 messages for the trip chat."""
        trip = get_object_or_404(Trip, id=trip_id)
        chat_room, _ = ChatRoom.objects.get_or_create(trip=trip)
        messages = (
            chat_room.messages
            .select_related('sender', 'poll')
            .prefetch_related('poll__options__votes', 'poll__votes')
            .order_by('-created_at')[:50]
        )
        messages = list(reversed(messages))
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response({
            'room_id': chat_room.id,
            'trip_id': trip.id,
            'trip_title': trip.title,
            'messages': serializer.data
        })

    def post(self, request, trip_id):
        """Send a new message via REST API (fallback for WebSocket)."""
        trip = get_object_or_404(Trip, id=trip_id)
        chat_room, _ = ChatRoom.objects.get_or_create(trip=trip)
        serializer = MessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        message = Message.objects.create(
            room=chat_room,
            sender=request.user,
            content=serializer.validated_data['content'],
            is_system=False
        )
        response_serializer = MessageSerializer(message, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class PollCreateView(APIView):
    """
    POST: Create a new poll inside the trip chat.
    Any accepted member can create a poll.
    """
    permission_classes = [IsAuthenticated, IsTripMemberAccepted]

    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        chat_room, _ = ChatRoom.objects.get_or_create(trip=trip)

        question = request.data.get('question', '').strip()
        options_data = request.data.get('options', [])
        allow_multiple = bool(request.data.get('allow_multiple', False))

        if not question:
            return Response({'error': 'Question is required'}, status=status.HTTP_400_BAD_REQUEST)
        if len(options_data) < 2:
            return Response({'error': 'At least 2 options are required'}, status=status.HTTP_400_BAD_REQUEST)
        if len(options_data) > 10:
            return Response({'error': 'Maximum 10 options allowed'}, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(
            room=chat_room,
            sender=request.user,
            content=f"\U0001f4ca {question}",
            message_type=Message.MESSAGE_TYPE_POLL,
            is_system=False
        )
        poll = Poll.objects.create(message=message, question=question, allow_multiple=allow_multiple)
        for i, opt_text in enumerate(options_data):
            text = str(opt_text).strip()
            if text:
                PollOption.objects.create(poll=poll, text=text, order=i)

        # Broadcast new poll message to WS group
        poll_ws_data = _serialize_poll_for_ws(poll)
        poll_ws_data['user_vote_option_ids'] = []
        message_data = {
            'id': message.id,
            'sender_id': request.user.id,
            'sender_name': request.user.full_name,
            'sender_avatar': None,
            'content': message.content,
            'message_type': 'poll',
            'created_at': message.created_at.isoformat(),
            'is_system': False,
            'is_me': False,
            'poll': poll_ws_data,
        }
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'trip_{trip_id}',
            {'type': 'chat_message', 'message': message_data}
        )

        serializer = MessageSerializer(message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PollVoteView(APIView):
    """
    POST: Cast or update vote on a poll.
    DELETE: Remove all votes from a poll.
    """
    permission_classes = [IsAuthenticated, IsTripMemberAccepted]

    def post(self, request, trip_id, poll_id):
        poll = get_object_or_404(Poll, id=poll_id, message__room__trip_id=trip_id)
        if poll.is_closed:
            return Response({'error': 'This poll is closed'}, status=status.HTTP_400_BAD_REQUEST)

        option_ids = request.data.get('option_ids', [])
        if not option_ids:
            return Response({'error': 'No options selected'}, status=status.HTTP_400_BAD_REQUEST)
        if not poll.allow_multiple and len(option_ids) > 1:
            return Response({'error': 'This poll only allows one choice'}, status=status.HTTP_400_BAD_REQUEST)

        options = PollOption.objects.filter(id__in=option_ids, poll=poll)
        if options.count() != len(option_ids):
            return Response({'error': 'Invalid option IDs'}, status=status.HTTP_400_BAD_REQUEST)

        PollVote.objects.filter(poll=poll, voter=request.user).delete()
        for option in options:
            PollVote.objects.create(poll=poll, option=option, voter=request.user)

        _broadcast_poll_update(trip_id, poll)
        serializer = PollSerializer(poll, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, trip_id, poll_id):
        poll = get_object_or_404(Poll, id=poll_id, message__room__trip_id=trip_id)
        PollVote.objects.filter(poll=poll, voter=request.user).delete()
        _broadcast_poll_update(trip_id, poll)
        serializer = PollSerializer(poll, context={'request': request})
        return Response(serializer.data)


class PollCloseView(APIView):
    """POST: Close a poll. Only the poll creator can close it."""
    permission_classes = [IsAuthenticated, IsTripMemberAccepted]

    def post(self, request, trip_id, poll_id):
        poll = get_object_or_404(Poll, id=poll_id, message__room__trip_id=trip_id)
        if poll.message.sender_id != request.user.id:
            return Response(
                {'error': 'Only the poll creator can close it'},
                status=status.HTTP_403_FORBIDDEN
            )
        poll.is_closed = True
        poll.save()
        _broadcast_poll_update(trip_id, poll)
        serializer = PollSerializer(poll, context={'request': request})
        return Response(serializer.data)
