"""
Test script for Unsplash multi-step fallback strategy.

Run with: python manage.py shell < test_unsplash_fallback.py
"""

from apps.recommendations.services.unsplash import unsplash_service

print("\n" + "="*80)
print("TESTING UNSPLASH MULTI-STEP FALLBACK STRATEGY")
print("="*80 + "\n")

# Test cases covering different scenarios
test_cases = [
    {
        'name': 'Chapel Bridge',
        'city': 'Lucerne',
        'country': 'Switzerland',
        'category': 'culture',
        'description': 'Famous Swiss landmark'
    },
    {
        'name': 'Parakkadavu Block Office',
        'city': 'Kannur',
        'country': 'India',
        'category': 'culture',
        'description': 'Small local government office (should fallback)'
    },
    {
        'name': 'Calangute Beach',
        'city': 'Goa',
        'country': 'India',
        'category': 'nature',
        'description': 'Popular Goa beach'
    },
    {
        'name': 'Random Bridge XYZ',
        'city': 'Kerala',
        'country': 'India',
        'category': 'culture',
        'description': 'Non-existent place (should use fallback)'
    },
    {
        'name': 'Fort Kochi',
        'city': 'Kochi',
        'country': 'India',
        'category': 'culture',
        'description': 'Historic area in Kerala'
    },
]

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test['name']}")
    print("-" * 80)
    print(f"Location: {test['city']}, {test['country']}")
    print(f"Category: {test['category']}")
    print(f"Expected: {test['description']}")
    print()
    
    image_url, image_source = unsplash_service.get_place_image_with_fallback(
        place_name=test['name'],
        city=test['city'],
        country=test['country'],
        category=test['category']
    )
    
    print(f"✓ Image URL: {image_url[:80]}...")
    print(f"✓ Source: {image_source}")
    
print("\n" + "="*80)
print("TEST COMPLETED")
print("="*80 + "\n")

# Show cache statistics
from apps.recommendations.models import DestinationImageCache
cache_count = DestinationImageCache.objects.count()
unsplash_count = DestinationImageCache.objects.filter(image_source='unsplash').count()
fallback_count = DestinationImageCache.objects.filter(image_source='fallback').count()

print(f"\nCache Statistics:")
print(f"Total cached entries: {cache_count}")
print(f"  - From Unsplash: {unsplash_count}")
print(f"  - Fallback images: {fallback_count}")
print()
