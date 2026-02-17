"""
Buddy Suggestions Service for AI Travel Assistant.

Provides buddy match suggestions with pagination support.
"""

import logging
from typing import Dict, List, Optional, Tuple
from django.db.models import Q

from apps.buddies.models import BuddyMatch, BuddyRequest

logger = logging.getLogger(__name__)

# Default batch size for buddy suggestions
DEFAULT_BATCH_SIZE = 3


def is_buddy_request(message: str) -> bool:
    """
    Detect if a user message is asking for buddy suggestions.
    
    Args:
        message: The user's message text
        
    Returns:
        True if the message is asking for buddy suggestions
    """
    message_lower = message.lower()
    
    # Initial buddy request keywords
    buddy_keywords = [
        'suggest buddies', 'suggest buddy', 'find buddy', 'find buddies',
        'recommend buddy', 'recommend buddies', 'travel buddy', 'travel buddies',
        'compatible buddy', 'compatible buddies', 'match buddy', 'buddy match',
        'buddy suggestion', 'buddy suggestions', 'who can i travel with',
        'find travel partner', 'travel companion', 'travel companions'
    ]
    
    return any(keyword in message_lower for keyword in buddy_keywords)


def is_more_buddies_request(message: str) -> bool:
    """
    Detect if user is asking for more buddy suggestions.
    
    Args:
        message: The user's message text
        
    Returns:
        True if the message is asking for more buddies
    """
    message_lower = message.lower()
    
    more_keywords = [
        'show more', 'more buddies', 'more suggestions', 'next buddies',
        'other buddies', 'more options', 'show others', 'any more',
        'more matches', 'other matches', 'next batch', 'continue'
    ]
    
    return any(keyword in message_lower for keyword in more_keywords)


def get_buddy_request_status(user, matched_user) -> str:
    """
    Get the buddy request status between two users.
    
    Args:
        user: Current authenticated user
        matched_user: Potential buddy
        
    Returns:
        Status string: 'none', 'pending_outgoing', 'pending_incoming', 'accepted'
    """
    # Check for existing BuddyMatch (connected/disconnected)
    buddy_match = BuddyMatch.objects.filter(
        (Q(user=user) & Q(matched_user=matched_user)) |
        (Q(user=matched_user) & Q(matched_user=user))
    ).first()
    
    if buddy_match and buddy_match.status == BuddyMatch.Status.CONNECTED:
        return 'accepted'
    
    # Check for buddy request
    buddy_req = BuddyRequest.objects.filter(
        (Q(sender=user) & Q(receiver=matched_user)) |
        (Q(sender=matched_user) & Q(receiver=user))
    ).first()
    
    if not buddy_req:
        return 'none'
    
    if buddy_req.status == BuddyRequest.Status.ACCEPTED:
        return 'accepted'
    
    if buddy_req.status == BuddyRequest.Status.PENDING:
        return 'pending_outgoing' if buddy_req.sender == user else 'pending_incoming'
    
    return 'none'


def get_ranked_buddy_matches(
    user,
    offset: int = 0,
    limit: int = DEFAULT_BATCH_SIZE
) -> Tuple[List[Dict], bool]:
    """
    Get ranked buddy matches for a user with pagination.
    
    Args:
        user: The authenticated user
        offset: Starting position for pagination
        limit: Maximum number of matches to return
        
    Returns:
        Tuple of (list of buddy match dicts, has_more flag)
    """
    # Get all matches sorted by score, excluding already connected users
    matches = BuddyMatch.objects.filter(
        user=user
    ).exclude(
        status=BuddyMatch.Status.DISCONNECTED
    ).order_by('-match_score').select_related('matched_user', 'matched_user__preferences')
    
    # Get total count
    total_count = matches.count()
    
    # Apply pagination
    paginated = matches[offset:offset + limit]
    
    # Check if there are more results
    has_more = (offset + limit) < total_count
    
    # Build response list
    buddy_list = []
    for match in paginated:
        matched_user = match.matched_user
        
        # Get user interests
        interests = []
        try:
            if hasattr(matched_user, 'preferences'):
                interests = list(
                    matched_user.preferences.interests.values_list('name', flat=True)[:5]
                )
        except Exception:
            pass
        
        # Get request status
        request_status = get_buddy_request_status(user, matched_user)
        
        buddy_list.append({
            'id': matched_user.id,
            'name': matched_user.full_name or matched_user.email.split('@')[0],
            'email': matched_user.email,
            'avatar': None,  # No avatar in current User model
            'match_score': round(match.match_score, 1),
            'tags': interests,
            'request_status': request_status,
        })
    
    return buddy_list, has_more


def build_buddy_response(
    user,
    conversation,
    is_more_request: bool = False
) -> Optional[Dict]:
    """
    Build a structured buddy suggestion response.
    
    Args:
        user: The authenticated user
        conversation: The ChatbotConversation instance
        is_more_request: Whether this is a "show more" request
        
    Returns:
        Structured response dict with buddy_cards, or None if not applicable
    """
    # Determine offset
    if is_more_request:
        offset = conversation.last_buddy_offset
    else:
        # Reset offset for new buddy request
        offset = 0
        conversation.last_buddy_offset = 0
    
    # Get buddy matches
    buddies, has_more = get_ranked_buddy_matches(user, offset=offset, limit=DEFAULT_BATCH_SIZE)
    
    # Update offset for next request
    if buddies:
        conversation.last_buddy_offset = offset + len(buddies)
        conversation.save()
    
    # Build reply text
    if not buddies:
        if offset == 0:
            reply_text = "I couldn't find any buddy matches for you yet. Make sure your travel preferences are set up, and try again later!"
        else:
            reply_text = "You've seen all your compatible travel buddies! Check back later for new matches, or explore your existing connections."
    elif is_more_request:
        reply_text = f"Here are more compatible travel buddies for you ({len(buddies)} more found):"
    else:
        reply_text = f"Based on your travel preferences, I found {len(buddies)} highly compatible travel buddies for you:"
    
    return {
        'reply_text': reply_text,
        'buddy_cards': buddies,
        'has_more': has_more,
    }
