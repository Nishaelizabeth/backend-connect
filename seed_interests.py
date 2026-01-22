import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.preferences.models import Interest

INTERESTS = [
    'Beaches', 'Mountains', 'Food', 'Culture', 'Adventure', 
    'Nature', 'Heritage', 'Nightlife', 'Shopping', 'Wellness',
    'Road Trips', 'Photography', 'Art', 'History', 'Luxury'
]

created_count = 0
for name in INTERESTS:
    interest, created = Interest.objects.get_or_create(name=name, defaults={'is_active': True})
    if created:
        created_count += 1
        print(f"Created interest: {name}")
    else:
        print(f"Interest already exists: {name}")

print(f"\nTotal new interests created: {created_count}")
