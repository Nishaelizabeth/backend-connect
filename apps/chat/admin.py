from django.contrib import admin
from .models import ChatRoom, Message


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
    list_display = ['id', 'room', 'sender', 'content_preview', 'is_system', 'created_at']
    list_filter = ['is_system', 'created_at', 'room']
    search_fields = ['content', 'sender__full_name', 'room__trip__title']
    readonly_fields = ['created_at']
    raw_id_fields = ['sender', 'room']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
