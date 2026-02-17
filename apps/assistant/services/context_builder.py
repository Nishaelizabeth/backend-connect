"""
Context Builder for AI Travel Assistant.

Builds personalized context from user's database information
for RAG-style (Retrieval-Augmented Generation) responses.
"""

import logging
from typing import Optional
from django.db.models import Q

logger = logging.getLogger(__name__)

# System prompt template
SYSTEM_PROMPT = """You are Travel Buddy AI, an intelligent and friendly travel assistant.

Your capabilities:
- Help users plan trips and create itineraries
- Suggest travel buddies based on compatibility
- Recommend destinations based on preferences
- Provide travel advice and tips
- Optimize travel plans and itineraries

Guidelines:
- Be concise but helpful
- Use the provided user context when relevant
- Give personalized suggestions when user data is available
- Be encouraging and positive about travel adventures
- If you don't have specific information, provide general travel advice
- Format responses nicely with bullet points when listing things"""


def build_user_context(user) -> str:
    """
    Build a context string from user's database information.
    
    Args:
        user: The authenticated user object
        
    Returns:
        Formatted context string with user's travel data
    """
    context_parts = []
    
    # User basic info
    context_parts.append(f"User: {user.full_name}")
    
    # User preferences
    try:
        if hasattr(user, 'preferences'):
            pref = user.preferences
            pref_info = []
            
            if pref.budget_range:
                budget_display = {
                    'low': 'Budget-friendly ($0-$1000)',
                    'medium': 'Medium ($1000-$3000)',
                    'high': 'Luxury ($3000+)'
                }.get(pref.budget_range, pref.budget_range)
                pref_info.append(f"Budget: {budget_display}")
            
            if pref.travel_style:
                pref_info.append(f"Travel Style: {pref.travel_style.title()}")
            
            if pref.preferred_trip_duration:
                duration_display = {
                    'weekend': 'Weekend trips (2-3 days)',
                    'short': 'Short trips (4-7 days)',
                    'long': 'Long trips (1-2+ weeks)'
                }.get(pref.preferred_trip_duration, pref.preferred_trip_duration)
                pref_info.append(f"Preferred Duration: {duration_display}")
            
            # Get interests
            interests = list(pref.interests.values_list('name', flat=True))
            if interests:
                pref_info.append(f"Interests: {', '.join(interests)}")
            
            if pref_info:
                context_parts.append("Travel Preferences:\n- " + "\n- ".join(pref_info))
    except Exception as e:
        logger.warning(f"Failed to fetch preferences: {e}")
    
    # User's trips
    try:
        from apps.trips.models import Trip, TripMember
        
        # Get trips where user is creator or accepted member
        trips = Trip.objects.filter(
            Q(creator=user) | 
            Q(members__user=user, members__status=TripMember.MembershipStatus.ACCEPTED)
        ).distinct().select_related('creator').prefetch_related('members__user')[:5]
        
        if trips:
            trip_info = []
            for trip in trips:
                member_count = trip.members.filter(status='accepted').count()
                trip_str = f"{trip.title} - {trip.destination or trip.display_destination}"
                trip_str += f" ({trip.start_date.strftime('%b %d')} - {trip.end_date.strftime('%b %d, %Y')})"
                trip_str += f" [{trip.status}, {member_count} members]"
                trip_info.append(trip_str)
            
            context_parts.append("Current/Recent Trips:\n- " + "\n- ".join(trip_info))
    except Exception as e:
        logger.warning(f"Failed to fetch trips: {e}")
    
    # Saved destinations (itinerary items)
    try:
        from apps.recommendations.models import TripSavedDestination
        
        saved = TripSavedDestination.objects.filter(
            saved_by=user
        ).select_related('destination', 'trip')[:10]
        
        if saved:
            dest_info = []
            for item in saved:
                dest = item.destination
                dest_str = f"{dest.name} ({dest.city})"
                if item.trip:
                    dest_str += f" - saved in '{item.trip.title}'"
                dest_info.append(dest_str)
            
            context_parts.append("Saved Destinations:\n- " + "\n- ".join(dest_info))
    except Exception as e:
        logger.warning(f"Failed to fetch saved destinations: {e}")
    
    # Buddy matches
    try:
        from apps.buddies.models import BuddyRequest
        
        # Get accepted buddy connections
        accepted_buddies = BuddyRequest.objects.filter(
            Q(sender=user, status=BuddyRequest.Status.ACCEPTED) |
            Q(receiver=user, status=BuddyRequest.Status.ACCEPTED)
        ).select_related('sender', 'receiver')[:5]
        
        if accepted_buddies:
            buddy_info = []
            for req in accepted_buddies:
                buddy = req.receiver if req.sender == user else req.sender
                buddy_info.append(buddy.full_name)
            
            context_parts.append(f"Connected Buddies: {', '.join(buddy_info)}")
    except Exception as e:
        logger.warning(f"Failed to fetch buddies: {e}")
    
    # Weather information for upcoming/active trips
    try:
        from datetime import date
        from apps.trips.models import Trip, TripMember
        from apps.trips.services.weather_service import weather_service
        
        # Get trips that are upcoming or currently active
        today = date.today()
        weather_trips = Trip.objects.filter(
            Q(creator=user) | 
            Q(members__user=user, members__status=TripMember.MembershipStatus.ACCEPTED)
        ).filter(
            end_date__gte=today  # Not yet ended
        ).distinct()[:3]
        
        weather_info = []
        for trip in weather_trips:
            weather_data = weather_service.get_weather_for_trip(trip)
            if weather_data:
                city = weather_data.get('city_name', trip.city or trip.destination)
                temp = weather_data.get('temperature')
                condition = weather_data.get('description', weather_data.get('condition', ''))
                weather_info.append(f"{trip.title} ({city}): {temp}°C, {condition}")
        
        if weather_info:
            context_parts.append("Current Weather at Destinations:\n- " + "\n- ".join(weather_info))
    except Exception as e:
        logger.warning(f"Failed to fetch weather: {e}")
    
    # Combine all context
    if context_parts:
        return "USER CONTEXT:\n" + "\n\n".join(context_parts)
    
    return "USER CONTEXT: No additional information available."


def build_conversation_history(conversation, limit: int = 5) -> str:
    """
    Build conversation history string from recent messages.
    
    Args:
        conversation: ChatbotConversation instance
        limit: Maximum number of previous messages to include
        
    Returns:
        Formatted conversation history string
    """
    if not conversation:
        return ""
    
    messages = conversation.messages.order_by('-created_at')[:limit]
    messages = list(reversed(messages))  # Oldest first
    
    if not messages:
        return ""
    
    history_parts = ["CONVERSATION HISTORY:"]
    for msg in messages:
        role_label = "User" if msg.role == 'user' else "Assistant"
        # Truncate long messages in history
        content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
        history_parts.append(f"{role_label}: {content}")
    
    return "\n".join(history_parts)


def build_full_prompt(
    user,
    user_message: str,
    conversation=None
) -> tuple[str, str]:
    """
    Build the complete prompt for the AI assistant.
    
    Args:
        user: The authenticated user
        user_message: The user's current message
        conversation: Optional existing conversation for history
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # Build user context from database
    user_context = build_user_context(user)
    
    # Build conversation history
    history = build_conversation_history(conversation, limit=5)
    
    # Combine into full prompt
    prompt_parts = [user_context]
    
    if history:
        prompt_parts.append(history)
    
    prompt_parts.append(f"User: {user_message}")
    prompt_parts.append("Assistant:")
    
    full_prompt = "\n\n".join(prompt_parts)
    
    return SYSTEM_PROMPT, full_prompt
