"""
Intent Detection Service.

Detects whether a user query requires database information
or can be answered with general travel knowledge.
"""

import re
import logging
from typing import Literal

logger = logging.getLogger(__name__)

# Intent types
IntentType = Literal['database_query', 'general_knowledge']

# Keywords that indicate database queries
DATABASE_KEYWORDS = {
    'trips': [
        r'\bmy trip(s)?\b',
        r'\bour trip(s)?\b',
        r'\bmy itinerary\b',
        r'\bmy plan(s)?\b',
        r'\bcurrent trip(s)?\b',
        r'\bupcoming trip(s)?\b',
    ],
    'buddies': [
        r'\bmy budd(y|ies)\b',
        r'\bmy friend(s)?\b',
        r'\bmy travel (partner|companion)(s)?\b',
        r'\bconnected budd(y|ies)\b',
        r'\btravel mate(s)?\b',
    ],
    'orders': [
        r'\bmy order(s)?\b',
        r'\bmy purchase(s)?\b',
        r'\border history\b',
        r'\bwhat (i |I )bought\b',
        r'\bwhat (i|I)\'ve ordered\b',
    ],
    'store': [
        r'\bmy (cart|basket)\b',
        r'\bmy wishlist\b',
        r'\bsaved item(s)?\b',
        r'\bin my cart\b',
    ],
    'preferences': [
        r'\bmy preference(s)?\b',
        r'\bmy (travel )?style\b',
        r'\bmy budget\b',
        r'\bmy interest(s)?\b',
    ],
    'destinations': [
        r'\bmy destination(s)?\b',
        r'\bsaved destination(s)?\b',
        r'\bsaved place(s)?\b',
        r'\bmy saved\b',
    ],
    'account': [
        r'\bmy account\b',
        r'\bmy profile\b',
        r'\bmy (travel )?history\b',
    ]
}

# Keywords that indicate general knowledge queries
GENERAL_KEYWORDS = [
    r'\bwhat (to|should I) pack\b',
    r'\bhow to\b',
    r'\bwhat is\b',
    r'\btell me about\b',
    r'\brecommend .+ (in|for|at)\b',
    r'\bbest time to visit\b',
    r'\bwhat\'s the weather (like )?(in|at)\b',
    r'\bthings to (do|see)\b',
    r'\bfamous (for|places)\b',
    r'\bculture (of|in)\b',
    r'\btips for\b',
    r'\badvice (for|about)\b',
]


def detect_intent(message: str) -> tuple[IntentType, str]:
    """
    Detect the intent of a user message.
    
    Args:
        message: The user's message
        
    Returns:
        Tuple of (intent_type, detected_category)
        - intent_type: 'database_query' or 'general_knowledge'
        - detected_category: The specific category detected (e.g., 'trips', 'buddies')
    """
    message_lower = message.lower()
    
    # Check for database query patterns
    for category, patterns in DATABASE_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                logger.info(f"Detected database intent: {category}")
                return 'database_query', category
    
    # Check for explicit general knowledge patterns
    for pattern in GENERAL_KEYWORDS:
        if re.search(pattern, message_lower):
            logger.info("Detected general knowledge intent")
            return 'general_knowledge', 'general'
    
    # Default to general knowledge if no database keywords found
    # This prevents hallucination - if we're not sure, treat it as general
    logger.info("No specific intent detected, defaulting to general knowledge")
    return 'general_knowledge', 'general'


def requires_database_context(message: str) -> bool:
    """
    Quick check if a message requires database context.
    
    Args:
        message: The user's message
        
    Returns:
        True if database context is needed, False otherwise
    """
    intent_type, _ = detect_intent(message)
    return intent_type == 'database_query'


def is_context_sufficient(context_dict: dict, category: str) -> bool:
    """
    Check if the retrieved context is sufficient to answer the query.
    
    Args:
        context_dict: Dictionary with context data (trips, buddies, orders, etc.)
        category: The detected category (trips, buddies, orders, etc.)
        
    Returns:
        True if context is sufficient, False otherwise
    """
    # Map categories to context keys
    category_mapping = {
        'trips': 'trips',
        'buddies': 'buddies',
        'orders': 'orders',
        'store': ['cart_items', 'wishlist'],
        'preferences': 'preferences',
        'destinations': 'saved_destinations',
        'account': ['trips', 'buddies', 'preferences']  # General account info
    }
    
    required_keys = category_mapping.get(category, [])
    if isinstance(required_keys, str):
        required_keys = [required_keys]
    
    # Check if at least one required key has data
    for key in required_keys:
        if key in context_dict and context_dict[key]:
            # Check if it's a list/queryset with items, or a non-empty dict
            data = context_dict[key]
            if isinstance(data, (list, tuple)):
                if len(data) > 0:
                    return True
            elif isinstance(data, dict):
                if data:  # Non-empty dict
                    return True
            elif data:  # Other truthy value
                return True
    
    # No sufficient data found
    logger.warning(f"Insufficient context for category: {category}")
    return False
