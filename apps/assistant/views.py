"""
AI Travel Assistant Views.
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import ChatbotConversation, ChatbotMessage
from .serializers import (
    AssistantChatRequestSerializer,
    AssistantChatResponseSerializer,
    ChatbotConversationSerializer,
    ChatbotMessageSerializer,
)
from .services.ollama_service import ollama_service
from .services.context_builder import build_full_prompt
from .services.buddy_suggestions import (
    is_buddy_request,
    is_more_buddies_request,
    build_buddy_response,
)
from .services.intent_detector import detect_intent, is_context_sufficient
from .services.hallucination_guard import validate_response

logger = logging.getLogger(__name__)

# Responses for insufficient database context
NO_DATA_RESPONSES = {
    'trips': "I don't see any trips in your account yet. Once you create trips, I can help you with planning and recommendations!",
    'buddies': "You don't have any connected travel buddies yet. Would you like me to help you find compatible travel companions?",
    'orders': "I don't see any orders in your purchase history yet. Feel free to explore our travel store!",
    'store': "Your cart and wishlist are currently empty. Browse our travel products and I can help you choose!",
    'preferences': "I don't have your travel preferences set up yet. You can update your profile to help me give better recommendations!",
    'destinations': "You haven't saved any destinations yet. Start exploring and save places you'd like to visit!",
    'account': "I don't see much data in your account yet. As you use Travel Buddy, I'll be able to provide more personalized assistance!",
    'general': "I don't see that information in your travel data yet."
}

# Fallback responses when Ollama is unavailable
FALLBACK_RESPONSES = {
    'plan': "I'd love to help you plan your trip! To get started, consider:\n\n• **Destination**: Where would you like to go?\n• **Duration**: How many days do you have?\n• **Budget**: What's your spending range?\n• **Activities**: What interests you most - adventure, culture, relaxation?\n\nOnce I know more, I can provide personalized recommendations!",
    'buddy': "Finding the perfect travel buddy is exciting! Based on your profile, I can suggest compatible matches. Here are some tips:\n\n• Look for buddies with similar travel styles\n• Consider budget compatibility\n• Shared interests make trips more enjoyable\n• Check their trip history for compatibility\n\nWould you like me to suggest some potential matches?",
    'itinerary': "Let me help optimize your itinerary! To create the best plan:\n\n• **Group nearby attractions** to minimize travel time\n• **Balance activities** with rest periods\n• **Consider travel times** between locations\n• **Leave buffer time** for unexpected discoveries\n\nShare your current itinerary and I'll suggest improvements!",
    'destination': "I'd be happy to recommend destinations! Consider these factors:\n\n• **Season**: Best time to visit matters\n• **Budget**: Some places offer better value\n• **Interests**: Adventure, beaches, culture, food?\n• **Duration**: Short trips vs extended stays\n\nWhat type of experience are you looking for?",
    'default': "Hello! I'm your Travel Buddy AI assistant. I can help you with:\n\n• 🗺️ **Trip Planning** - Create personalized itineraries\n• 👥 **Finding Buddies** - Match with compatible travelers\n• 📍 **Destinations** - Discover new places to explore\n• ⚡ **Optimization** - Make the most of your trips\n\nWhat would you like help with today?"
}


def get_fallback_response(message: str) -> str:
    """Get an appropriate fallback response based on the message content."""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['plan', 'planning', 'create trip', 'new trip']):
        return FALLBACK_RESPONSES['plan']
    elif any(word in message_lower for word in ['buddy', 'buddies', 'friend', 'partner', 'companion']):
        return FALLBACK_RESPONSES['buddy']
    elif any(word in message_lower for word in ['itinerary', 'optimize', 'schedule', 'order']):
        return FALLBACK_RESPONSES['itinerary']
    elif any(word in message_lower for word in ['destination', 'recommend', 'suggest', 'where', 'place']):
        return FALLBACK_RESPONSES['destination']
    else:
        return FALLBACK_RESPONSES['default']


class AssistantChatView(APIView):
    """
    POST /api/assistant/chat/
    
    Send a message to the AI travel assistant and receive a response.
    Maintains conversation history for context-aware responses.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AssistantChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_message = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id')
        
        # Get or create conversation
        conversation = None
        if conversation_id:
            try:
                conversation = ChatbotConversation.objects.get(
                    id=conversation_id,
                    user=request.user
                )
            except ChatbotConversation.DoesNotExist:
                pass
        
        if not conversation:
            # Create new conversation with title from first message
            title = user_message[:100] + "..." if len(user_message) > 100 else user_message
            conversation = ChatbotConversation.objects.create(
                user=request.user,
                title=title
            )
        
        # Save user message
        user_msg = ChatbotMessage.objects.create(
            conversation=conversation,
            role=ChatbotMessage.Role.USER,
            content=user_message
        )
        
        # Check if this is a buddy suggestion request
        buddy_request = is_buddy_request(user_message)
        more_buddies_request = is_more_buddies_request(user_message)
        
        if buddy_request or more_buddies_request:
            # Handle buddy suggestions - bypass Ollama
            buddy_response = build_buddy_response(
                user=request.user,
                conversation=conversation,
                is_more_request=more_buddies_request
            )
            
            # Save assistant response (text only for history)
            assistant_msg = ChatbotMessage.objects.create(
                conversation=conversation,
                role=ChatbotMessage.Role.ASSISTANT,
                content=buddy_response['reply_text']
            )
            
            # Update conversation timestamp
            conversation.save()
            
            return Response({
                'reply': buddy_response['reply_text'],
                'buddy_cards': buddy_response['buddy_cards'],
                'has_more_buddies': buddy_response['has_more'],
                'conversation_id': conversation.id,
                'message_id': assistant_msg.id
            }, status=status.HTTP_200_OK)
        
        # Detect intent - is this a database query or general knowledge?
        intent_type, intent_category = detect_intent(user_message)
        logger.info(f"Detected intent: {intent_type} (category: {intent_category})")
        
        # Build prompt with context
        system_prompt, full_prompt, structured_context = build_full_prompt(
            user=request.user,
            user_message=user_message,
            conversation=conversation
        )
        
        # ANTI-HALLUCINATION CHECK:
        # For database queries, check if we have sufficient context
        if intent_type == 'database_query':
            if not is_context_sufficient(structured_context, intent_category):
                # No data available - return direct response without calling LLM
                refusal_message = NO_DATA_RESPONSES.get(
                    intent_category,
                    NO_DATA_RESPONSES['general']
                )
                
                logger.info(f"Insufficient context for {intent_category} query, returning refusal")
                
                # Save assistant response
                assistant_msg = ChatbotMessage.objects.create(
                    conversation=conversation,
                    role=ChatbotMessage.Role.ASSISTANT,
                    content=refusal_message
                )
                
                # Update conversation timestamp
                conversation.save()
                
                return Response({
                    'reply': refusal_message,
                    'conversation_id': conversation.id,
                    'message_id': assistant_msg.id
                }, status=status.HTTP_200_OK)
        
        # Regular message - use Ollama or fallback
        # Generate AI response
        ai_response = None
        if ollama_service.is_available():
            ai_response = ollama_service.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
        
        # Use fallback if Ollama fails
        if not ai_response:
            logger.warning("Ollama unavailable, using fallback response")
            ai_response = get_fallback_response(user_message)
        
        # HALLUCINATION GUARD:
        # Validate the response for database queries
        if intent_type == 'database_query' and ai_response:
            is_valid, override_response = validate_response(
                response=ai_response,
                user_context=structured_context,
                intent_category=intent_category
            )
            
            if not is_valid and override_response:
                logger.warning(f"Hallucination detected, using override response")
                ai_response = override_response
        
        # Save assistant response
        assistant_msg = ChatbotMessage.objects.create(
            conversation=conversation,
            role=ChatbotMessage.Role.ASSISTANT,
            content=ai_response
        )
        
        # Update conversation timestamp
        conversation.save()  # Triggers updated_at
        
        return Response({
            'reply': ai_response,
            'conversation_id': conversation.id,
            'message_id': assistant_msg.id
        }, status=status.HTTP_200_OK)
        
        # Update conversation timestamp
        conversation.save()  # Triggers updated_at
        
        return Response({
            'reply': ai_response,
            'conversation_id': conversation.id,
            'message_id': assistant_msg.id
        }, status=status.HTTP_200_OK)


class AssistantConversationsView(APIView):
    """
    GET /api/assistant/conversations/
    
    List user's conversation history.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = ChatbotConversation.objects.filter(
            user=request.user
        ).prefetch_related('messages')[:20]
        
        serializer = ChatbotConversationSerializer(conversations, many=True)
        return Response({
            'count': len(conversations),
            'conversations': serializer.data
        })


class AssistantConversationDetailView(APIView):
    """
    GET /api/assistant/conversations/<id>/
    DELETE /api/assistant/conversations/<id>/
    
    Get or delete a specific conversation.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        try:
            conversation = ChatbotConversation.objects.prefetch_related(
                'messages'
            ).get(id=conversation_id, user=request.user)
        except ChatbotConversation.DoesNotExist:
            return Response(
                {'detail': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ChatbotConversationSerializer(conversation)
        return Response(serializer.data)

    def delete(self, request, conversation_id):
        try:
            conversation = ChatbotConversation.objects.get(
                id=conversation_id,
                user=request.user
            )
        except ChatbotConversation.DoesNotExist:
            return Response(
                {'detail': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssistantStatusView(APIView):
    """
    GET /api/assistant/status/
    
    Check if the AI assistant is available.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_available = ollama_service.is_available()
        return Response({
            'available': is_available,
            'model': ollama_service.model if is_available else None,
            'fallback_enabled': True
        })
