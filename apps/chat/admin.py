from django.contrib import admin
from .models import ChatRoom, Message, Poll, PollOption, PollVote


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'trip', 'created_at', 'message_count']
    list_filter = ['created_at']
    search_fields = ['trip__title']
    readonly_fields = ['created_at']

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'room', 'sender', 'message_type', 'content_preview', 'is_system', 'created_at']
    list_filter = ['is_system', 'message_type', 'created_at', 'room']
    search_fields = ['content', 'sender__full_name', 'room__trip__title']
    readonly_fields = ['created_at']
    raw_id_fields = ['sender', 'room']

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 2
    fields = ['text', 'order']


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ['id', 'question_preview', 'allow_multiple', 'is_closed', 'vote_count', 'created_at']
    list_filter = ['is_closed', 'allow_multiple', 'created_at']
    search_fields = ['question', 'message__room__trip__title']
    readonly_fields = ['created_at']
    inlines = [PollOptionInline]

    def question_preview(self, obj):
        return obj.question[:60] + '...' if len(obj.question) > 60 else obj.question
    question_preview.short_description = 'Question'

    def vote_count(self, obj):
        return obj.votes.values('voter').distinct().count()
    vote_count.short_description = 'Unique Voters'


@admin.register(PollVote)
class PollVoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'poll', 'option', 'voter', 'created_at']
    list_filter = ['created_at']
    search_fields = ['voter__full_name', 'poll__question']
    readonly_fields = ['created_at']
