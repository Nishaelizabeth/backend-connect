from rest_framework import serializers
from .models import ChatRoom, Message, Poll, PollOption, PollVote


class PollOptionSerializer(serializers.ModelSerializer):
    vote_count = serializers.SerializerMethodField()

    class Meta:
        model = PollOption
        fields = ['id', 'text', 'order', 'vote_count']

    def get_vote_count(self, obj):
        return obj.votes.count()


class PollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)
    total_votes = serializers.SerializerMethodField()
    user_vote_option_ids = serializers.SerializerMethodField()
    voters_per_option = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = [
            'id', 'question', 'allow_multiple', 'is_closed', 'expires_at',
            'options', 'total_votes', 'user_vote_option_ids', 'voters_per_option'
        ]

    def get_total_votes(self, obj):
        return obj.votes.values('voter').distinct().count()

    def get_user_vote_option_ids(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return list(obj.votes.filter(voter=request.user).values_list('option_id', flat=True))
        return []

    def get_voters_per_option(self, obj):
        result = {}
        for vote in obj.votes.select_related('option').all():
            opt_id = str(vote.option_id)
            if opt_id not in result:
                result[opt_id] = []
            result[opt_id].append(vote.voter_id)
        return result


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for chat messages.
    Includes sender details and optional poll data.
    """
    sender_id = serializers.IntegerField(source='sender.id', read_only=True, allow_null=True)
    sender_name = serializers.CharField(source='sender.full_name', read_only=True, allow_null=True)
    sender_avatar = serializers.SerializerMethodField()
    is_me = serializers.SerializerMethodField()
    poll = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id',
            'sender_id',
            'sender_name',
            'sender_avatar',
            'content',
            'message_type',
            'created_at',
            'is_system',
            'is_me',
            'poll',
        ]
        read_only_fields = ['id', 'created_at', 'is_system', 'message_type']

    def get_sender_avatar(self, obj):
        return None

    def get_is_me(self, obj):
        request = self.context.get('request')
        if request and request.user and obj.sender:
            return request.user.id == obj.sender.id
        return False

    def get_poll(self, obj):
        if obj.message_type == Message.MESSAGE_TYPE_POLL:
            try:
                return PollSerializer(obj.poll, context=self.context).data
            except Poll.DoesNotExist:
                return None
        return None


class MessageCreateSerializer(serializers.Serializer):
    """
    Serializer for creating new messages via REST API.
    """
    content = serializers.CharField(max_length=2000)


class ChatRoomSerializer(serializers.ModelSerializer):
    """
    Serializer for chat room details.
    """
    trip_id = serializers.IntegerField(source='trip.id', read_only=True)
    trip_title = serializers.CharField(source='trip.title', read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'trip_id', 'trip_title', 'created_at', 'message_count']
        read_only_fields = ['id', 'created_at']

    def get_message_count(self, obj):
        return obj.messages.count()
