"""
Hallucination Guard Service.

Post-processes AI responses to detect and prevent hallucinated information
about user's trips, buddies, orders, and other database-backed data.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Suspicious patterns that might indicate hallucination
SUSPICIOUS_PATTERNS = {
    'specific_names': [
        # Phrases that suggest fabricated names
        r'\b(Alex|John|Sarah|Mike|Emily|David|Lisa|James|Maria|Tom|Jane)\b',
        # Pattern: "trip to X with Y" where Y might be fabricated
        r'\btrip to .+ with \b[A-Z][a-z]+\b',
    ],
    'specific_dates': [
        # Dates that weren't in context (e.g., "your trip on January 15th")
        r'\bon (January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}(st|nd|rd|th)?\b',
        r'\b\d{1,2}/(0?[1-9]|1[0-2])/\d{2,4}\b',
    ],
    'specific_trips': [
        # Trip references with specific details
        r'\byour trip to [A-Z][a-z]+( [A-Z][a-z]+)?\b',
        r'\b(booked|planned|scheduled) .+ trip\b',
    ],
    'specific_products': [
        # Product references
        r'\b(ordered|bought|purchased) .+ (bag|backpack|luggage|suitcase|camera)\b',
        r'\byour order of\b',
    ],
    'specific_numbers': [
        # Specific quantities that might be fabricated
        r'\b\$\d+\.?\d* (order|purchase)\b',
        r'\b\d+ items in your cart\b',
        r'\b\d+ buddies\b',
    ]
}

# Safe refusal response
REFUSAL_RESPONSE = (
    "I don't see that information in your travel data yet. "
    "I can only provide accurate information based on your actual trips, "
    "buddies, and orders in the Travel Buddy system."
)


def validate_response(
    response: str,
    user_context: dict,
    intent_category: str
) -> tuple[bool, Optional[str]]:
    """
    Validate an AI response against user context to detect hallucinations.
    
    Args:
        response: The AI-generated response to validate
        user_context: Dictionary with actual user data from database
        intent_category: The detected intent category (trips, buddies, orders, etc.)
        
    Returns:
        Tuple of (is_valid, override_response)
        - is_valid: True if response seems grounded, False if hallucination detected
        - override_response: Optional replacement response if hallucination detected
    """
    # If it's a general knowledge query, don't validate
    if intent_category == 'general':
        return True, None
    
    # Check for suspicious patterns
    suspicion_score = 0
    detected_issues = []
    
    for category, patterns in SUSPICIOUS_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, response, re.IGNORECASE):
                suspicion_score += 1
                detected_issues.append(category)
    
    # If multiple suspicious patterns detected, flag as potential hallucination
    if suspicion_score >= 2:
        logger.warning(
            f"Potential hallucination detected. "
            f"Suspicion score: {suspicion_score}, Issues: {detected_issues}"
        )
        return False, REFUSAL_RESPONSE
    
    # Category-specific validation
    if intent_category == 'trips':
        if not user_context.get('trips'):
            # No trips in context, but response mentions trips
            if re.search(r'\byour trip(s)?\b', response, re.IGNORECASE):
                return False, "I don't see any trips in your account yet."
    
    elif intent_category == 'buddies':
        if not user_context.get('buddies'):
            # No buddies in context, but response mentions buddies
            if re.search(r'\b(buddy|buddies|friend|companion)\b', response, re.IGNORECASE):
                return False, "You don't have any connected travel buddies yet."
    
    elif intent_category == 'orders':
        if not user_context.get('orders'):
            # No orders in context, but response mentions orders
            if re.search(r'\b(order|purchase|bought)\b', response, re.IGNORECASE):
                return False, "I don't see any orders in your purchase history."
    
    elif intent_category == 'store':
        cart_items = user_context.get('cart_items', [])
        wishlist = user_context.get('wishlist', [])
        if not cart_items and not wishlist:
            # No cart/wishlist items, but response mentions them
            if re.search(r'\b(cart|wishlist|saved item)\b', response, re.IGNORECASE):
                return False, "Your cart and wishlist are currently empty."
    
    # Response seems valid
    return True, None


def extract_known_entities(user_context: dict) -> dict:
    """
    Extract known entity names from user context for validation.
    
    Args:
        user_context: Dictionary with user data
        
    Returns:
        Dictionary with known entity names (trips, buddies, products, etc.)
    """
    entities = {
        'trip_names': [],
        'buddy_names': [],
        'destinations': [],
        'products': []
    }
    
    # Extract trip names
    if 'trips' in user_context:
        for trip in user_context['trips']:
            if hasattr(trip, 'title'):
                entities['trip_names'].append(trip.title)
    
    # Extract buddy names
    if 'buddies' in user_context:
        for buddy in user_context['buddies']:
            if hasattr(buddy, 'full_name'):
                entities['buddy_names'].append(buddy.full_name)
    
    # Extract destinations
    if 'saved_destinations' in user_context:
        for dest in user_context['saved_destinations']:
            if hasattr(dest, 'destination') and hasattr(dest.destination, 'name'):
                entities['destinations'].append(dest.destination.name)
    
    # Extract products
    if 'orders' in user_context:
        for order in user_context['orders']:
            if hasattr(order, 'items'):
                for item in order.items.all():
                    if hasattr(item, 'product') and hasattr(item.product, 'name'):
                        entities['products'].append(item.product.name)
    
    return entities


def check_entity_hallucination(response: str, known_entities: dict) -> bool:
    """
    Check if the response mentions entities not present in known_entities.
    
    Args:
        response: The AI response
        known_entities: Dictionary of known entity names
        
    Returns:
        True if no hallucination detected, False otherwise
    """
    # This is a simple implementation
    # In production, you might use NER (Named Entity Recognition) for better detection
    
    # For now, we trust that if the response references specific things,
    # those references should match our known entities
    
    # Extract potential trip references
    trip_mentions = re.findall(r'trip (?:to |named )?["\']?([A-Za-z ]+)["\']?', response, re.IGNORECASE)
    
    for mention in trip_mentions:
        mention = mention.strip()
        if mention and mention not in known_entities.get('trip_names', []):
            # Found a trip mention that's not in known trips
            logger.warning(f"Unknown trip mentioned: {mention}")
            return False
    
    return True
