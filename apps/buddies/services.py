"""
Buddies app services.

This module contains the business logic for computing buddy matches
using rule-based matching algorithms.
"""

from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from apps.preferences.models import Preference, Interest

User = get_user_model()


# Matching weights (must sum to 1.0)
INTEREST_WEIGHT = 0.50
BUDGET_WEIGHT = 0.20
TRAVEL_STYLE_WEIGHT = 0.20
DURATION_WEIGHT = 0.10


class BuddyMatchingService:
    """
    Service class for computing buddy compatibility scores.
    
    Uses rule-based matching with weighted scoring:
    - Interest overlap: 50%
    - Budget range match: 20%
    - Travel style match: 20%
    - Trip duration match: 10%
    """

    def __init__(self, user):
        """
        Initialize the matching service for a specific user.
        
        Args:
            user: The User instance seeking matches
        """
        self.user = user
        self.user_preferences = self._get_user_preferences(user)

    def _get_user_preferences(self, user):
        """
        Fetch user preferences with related interests.
        
        Args:
            user: User instance
            
        Returns:
            Preference instance or None if not exists
        """
        try:
            return Preference.objects.prefetch_related('interests').get(user=user)
        except Preference.DoesNotExist:
            return None

    def _calculate_interest_score(self, user_interests, other_interests):
        """
        Calculate interest overlap score.
        
        Uses Jaccard similarity coefficient:
        intersection / union * 100
        
        Args:
            user_interests: Set of interest IDs for the user
            other_interests: Set of interest IDs for the other user
            
        Returns:
            Float score from 0-100
        """
        if not user_interests and not other_interests:
            return 50.0  # Neutral score if both have no interests
        
        if not user_interests or not other_interests:
            return 0.0
        
        intersection = user_interests & other_interests
        union = user_interests | other_interests
        
        if not union:
            return 0.0
        
        return (len(intersection) / len(union)) * 100

    def _calculate_exact_match_score(self, value1, value2):
        """
        Calculate score for exact match fields.
        
        Args:
            value1: First value to compare
            value2: Second value to compare
            
        Returns:
            100.0 if match, 0.0 otherwise
        """
        if value1 == value2:
            return 100.0
        return 0.0

    def _calculate_budget_score(self, budget1, budget2):
        """
        Calculate budget compatibility score.
        
        Adjacent budget ranges get partial credit.
        
        Args:
            budget1: First budget range
            budget2: Second budget range
            
        Returns:
            Float score from 0-100
        """
        budget_order = ['low', 'medium', 'high']
        
        if budget1 == budget2:
            return 100.0
        
        try:
            idx1 = budget_order.index(budget1)
            idx2 = budget_order.index(budget2)
            diff = abs(idx1 - idx2)
            
            # Adjacent budgets get 50 points
            if diff == 1:
                return 50.0
            return 0.0
        except ValueError:
            return 0.0

    def _calculate_match_score(self, other_preferences):
        """
        Calculate overall match score between the user and another user.
        
        Args:
            other_preferences: Preference instance of the other user
            
        Returns:
            Tuple of (score, shared_interests_list)
        """
        if not self.user_preferences or not other_preferences:
            return 0.0, []

        # Get interest IDs
        user_interest_ids = set(
            self.user_preferences.interests.values_list('id', flat=True)
        )
        other_interest_ids = set(
            other_preferences.interests.values_list('id', flat=True)
        )

        # Calculate individual scores
        interest_score = self._calculate_interest_score(
            user_interest_ids, other_interest_ids
        )
        budget_score = self._calculate_budget_score(
            self.user_preferences.budget_range,
            other_preferences.budget_range
        )
        style_score = self._calculate_exact_match_score(
            self.user_preferences.travel_style,
            other_preferences.travel_style
        )
        duration_score = self._calculate_exact_match_score(
            self.user_preferences.preferred_trip_duration,
            other_preferences.preferred_trip_duration
        )

        # Calculate weighted total
        total_score = (
            interest_score * INTEREST_WEIGHT +
            budget_score * BUDGET_WEIGHT +
            style_score * TRAVEL_STYLE_WEIGHT +
            duration_score * DURATION_WEIGHT
        )

        # Get shared interest names
        shared_interest_ids = user_interest_ids & other_interest_ids
        shared_interests = list(
            Interest.objects.filter(id__in=shared_interest_ids).values_list('name', flat=True)
        )

        return round(total_score, 1), shared_interests

    def get_matches(self, limit=10, min_score=0.0):
        """
        Get ranked list of potential buddy matches for the user.
        
        Args:
            limit: Maximum number of matches to return
            min_score: Minimum match score threshold
            
        Returns:
            List of dicts with match information
        """
        if not self.user_preferences:
            return []

        # Get all users with preferences, excluding current user
        other_users_with_prefs = Preference.objects.select_related('user').prefetch_related(
            'interests'
        ).exclude(user=self.user)

        matches = []
        for other_pref in other_users_with_prefs:
            score, shared_interests = self._calculate_match_score(other_pref)
            
            if score >= min_score:
                matches.append({
                    'user': other_pref.user,
                    'match_score': score,
                    'shared_interests': shared_interests,
                })

        # Sort by score descending
        matches.sort(key=lambda x: x['match_score'], reverse=True)

        return matches[:limit]


def get_buddy_matches(user, limit=10, min_score=0.0):
    """
    Convenience function to get buddy matches for a user.
    
    Args:
        user: User instance
        limit: Maximum number of matches
        min_score: Minimum score threshold
        
    Returns:
        List of match dictionaries
    """
    service = BuddyMatchingService(user)
    return service.get_matches(limit=limit, min_score=min_score)
