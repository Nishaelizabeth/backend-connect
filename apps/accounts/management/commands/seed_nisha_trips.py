"""
Management command to seed trips and invitations for jacobnisha923@gmail.com.

Usage:
    python manage.py seed_nisha_trips
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.accounts.models import User
from apps.trips.models import Trip, TripMember, TripImage, TripWeatherCache


# ── Trip definitions for Nisha ──────────────────────────────────────
NISHA_TRIPS = [
    # ── COMPLETED trips ──
    {
        "title": "Shimla Winter Wonderland",
        "city": "Shimla",
        "region": "Himachal Pradesh",
        "country": "India",
        "lat": 31.1048,
        "lng": 77.1734,
        "status": "completed",
        "days_ago_start": 90,
        "duration": 5,
        "cover": "https://images.unsplash.com/photo-1597074866923-dc0589150a32?w=800&h=400&fit=crop",
        "weather": {"temp": 5, "condition": "Snow", "desc": "light snow", "icon": "13d"},
    },
    {
        "title": "Hampi Heritage Exploration",
        "city": "Hampi",
        "region": "Karnataka",
        "country": "India",
        "lat": 15.3350,
        "lng": 76.4600,
        "status": "completed",
        "days_ago_start": 60,
        "duration": 4,
        "cover": "https://images.unsplash.com/photo-1590050752117-238cb20e10f4?w=800&h=400&fit=crop",
        "weather": {"temp": 34, "condition": "Clear", "desc": "clear sky", "icon": "01d"},
    },
    {
        "title": "Andaman Beach Holiday",
        "city": "Port Blair",
        "region": "Andaman and Nicobar",
        "country": "India",
        "lat": 11.6234,
        "lng": 92.7265,
        "status": "completed",
        "days_ago_start": 40,
        "duration": 7,
        "cover": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&h=400&fit=crop",
        "weather": {"temp": 29, "condition": "Clouds", "desc": "scattered clouds", "icon": "03d"},
    },
    {
        "title": "Varanasi Spiritual Journey",
        "city": "Varanasi",
        "region": "Uttar Pradesh",
        "country": "India",
        "lat": 25.3176,
        "lng": 82.9739,
        "status": "completed",
        "days_ago_start": 25,
        "duration": 3,
        "cover": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=800&h=400&fit=crop",
        "weather": {"temp": 22, "condition": "Haze", "desc": "haze", "icon": "50d"},
    },
    # ── UPCOMING trips ──
    {
        "title": "Meghalaya Cloud Chase",
        "city": "Shillong",
        "region": "Meghalaya",
        "country": "India",
        "lat": 25.5788,
        "lng": 91.8933,
        "status": "upcoming",
        "days_ahead_start": 5,
        "duration": 6,
        "cover": "https://images.unsplash.com/photo-1506461883276-594a12b11cf3?w=800&h=400&fit=crop",
        "weather": {"temp": 18, "condition": "Rain", "desc": "moderate rain", "icon": "10d"},
    },
    {
        "title": "Darjeeling Tea Trail",
        "city": "Darjeeling",
        "region": "West Bengal",
        "country": "India",
        "lat": 27.0360,
        "lng": 88.2627,
        "status": "upcoming",
        "days_ahead_start": 10,
        "duration": 4,
        "cover": "https://images.unsplash.com/photo-1566837945700-30057527ade0?w=800&h=400&fit=crop",
        "weather": {"temp": 12, "condition": "Mist", "desc": "mist", "icon": "50d"},
    },
    {
        "title": "Dubai Desert Safari",
        "city": "Dubai",
        "region": "Dubai",
        "country": "UAE",
        "lat": 25.2048,
        "lng": 55.2708,
        "status": "upcoming",
        "days_ahead_start": 15,
        "duration": 5,
        "cover": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=800&h=400&fit=crop",
        "weather": {"temp": 38, "condition": "Clear", "desc": "clear sky", "icon": "01d"},
    },
    # ── PLANNED trips ──
    {
        "title": "Swiss Alps Adventure",
        "city": "Interlaken",
        "region": "Bern",
        "country": "Switzerland",
        "lat": 46.6863,
        "lng": 7.8632,
        "status": "planned",
        "days_ahead_start": 45,
        "duration": 8,
        "cover": "https://images.unsplash.com/photo-1531366936337-7c912a4589a7?w=800&h=400&fit=crop",
        "weather": {"temp": 6, "condition": "Clouds", "desc": "overcast clouds", "icon": "04d"},
    },
    {
        "title": "Vietnam Backpacking",
        "city": "Hanoi",
        "region": "Hanoi",
        "country": "Vietnam",
        "lat": 21.0278,
        "lng": 105.8342,
        "status": "planned",
        "days_ahead_start": 60,
        "duration": 10,
        "cover": "https://images.unsplash.com/photo-1528127269322-539801943592?w=800&h=400&fit=crop",
        "weather": {"temp": 26, "condition": "Rain", "desc": "light rain", "icon": "10d"},
    },
    {
        "title": "Ladakh Bike Expedition",
        "city": "Leh",
        "region": "Ladakh",
        "country": "India",
        "lat": 34.1526,
        "lng": 77.5771,
        "status": "planned",
        "days_ahead_start": 75,
        "duration": 12,
        "cover": "https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?w=800&h=400&fit=crop",
        "weather": {"temp": 10, "condition": "Clear", "desc": "clear sky", "icon": "01d"},
    },
    {
        "title": "Ooty Hill Station Retreat",
        "city": "Ooty",
        "region": "Tamil Nadu",
        "country": "India",
        "lat": 11.4102,
        "lng": 76.6950,
        "status": "planned",
        "days_ahead_start": 50,
        "duration": 4,
        "cover": "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=800&h=400&fit=crop",
        "weather": {"temp": 15, "condition": "Mist", "desc": "mist", "icon": "50d"},
    },
]

# ── Trip images ─────────────────────────────────────────────────────
IMAGE_POOL = [
    ("https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=600&h=400&fit=crop", "Majestic mountain peaks at dawn"),
    ("https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=600&h=400&fit=crop", "Serene valley landscape"),
    ("https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=600&h=400&fit=crop", "Golden sunlight through the trees"),
    ("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=600&h=400&fit=crop", "Crystal clear beach waters"),
    ("https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=600&h=400&fit=crop", "Breathtaking lake view"),
    ("https://images.unsplash.com/photo-1530789253388-582c481c54b0?w=600&h=400&fit=crop", "Sunset over the ocean"),
    ("https://images.unsplash.com/photo-1549144511-f099e773c147?w=600&h=400&fit=crop", "Ancient temple corridors"),
    ("https://images.unsplash.com/photo-1512100356356-de1b84283e18?w=600&h=400&fit=crop", "Tropical paradise vibes"),
    ("https://images.unsplash.com/photo-1470770903676-69b98201ea1c?w=600&h=400&fit=crop", "Misty morning meadow"),
    ("https://images.unsplash.com/photo-1433838552652-f9a46b332c40?w=600&h=400&fit=crop", "Countryside road stretching ahead"),
    ("https://images.unsplash.com/photo-1506197603052-3cc9c3a201bd?w=600&h=400&fit=crop", "Vibrant street market"),
    ("https://images.unsplash.com/photo-1519681393784-d120267933ba?w=600&h=400&fit=crop", "Starry night over mountains"),
    ("https://images.unsplash.com/photo-1544735716-392fe2489ffa?w=600&h=400&fit=crop", "Traditional boat on calm waters"),
    ("https://images.unsplash.com/photo-1502301103665-0b95cc738daf?w=600&h=400&fit=crop", "Campfire under the night sky"),
    ("https://images.unsplash.com/photo-1596402184320-417e7178b2cd?w=600&h=400&fit=crop", "Colourful local architecture"),
    ("https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=600&h=400&fit=crop", "Resort with an infinity pool"),
    ("https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=600&h=400&fit=crop", "Camping spot by the river"),
    ("https://images.unsplash.com/photo-1551632811-561732d1e306?w=600&h=400&fit=crop", "Trekking trail through the hills"),
]

# ── Invitation data ─────────────────────────────────────────────────
# "target" = email of user being invited, "status" = member status after invite
INVITATION_SPECS = [
    # Nisha invites others to her NEW trips
    {"trip": "Meghalaya Cloud Chase", "inviter": "jacobnisha923@gmail.com", "invitees": [
        ("alex@travelbuddy.com", "accepted"),
        ("maria@travelbuddy.com", "invited"),
        ("priya@travelbuddy.com", "accepted"),
        ("david@travelbuddy.com", "invited"),
    ]},
    {"trip": "Darjeeling Tea Trail", "inviter": "jacobnisha923@gmail.com", "invitees": [
        ("sara@travelbuddy.com", "accepted"),
        ("ananya@travelbuddy.com", "invited"),
        ("rohan@travelbuddy.com", "accepted"),
    ]},
    {"trip": "Dubai Desert Safari", "inviter": "jacobnisha923@gmail.com", "invitees": [
        ("carlos@travelbuddy.com", "accepted"),
        ("emi@travelbuddy.com", "accepted"),
        ("fatima@travelbuddy.com", "invited"),
        ("john@travelbuddy.com", "invited"),
        ("nina@travelbuddy.com", "accepted"),
    ]},
    {"trip": "Swiss Alps Adventure", "inviter": "jacobnisha923@gmail.com", "invitees": [
        ("lena@travelbuddy.com", "accepted"),
        ("sophie@travelbuddy.com", "accepted"),
        ("ethan@travelbuddy.com", "invited"),
        ("leo@travelbuddy.com", "invited"),
    ]},
    {"trip": "Vietnam Backpacking", "inviter": "jacobnisha923@gmail.com", "invitees": [
        ("rahul@travelbuddy.com", "accepted"),
        ("divya@travelbuddy.com", "accepted"),
        ("akash@travelbuddy.com", "invited"),
        ("mia@travelbuddy.com", "accepted"),
    ]},
    {"trip": "Ladakh Bike Expedition", "inviter": "jacobnisha923@gmail.com", "invitees": [
        ("arjun@travelbuddy.com", "accepted"),
        ("vikram@travelbuddy.com", "accepted"),
        ("sanjay@travelbuddy.com", "accepted"),
        ("ravi@travelbuddy.com", "invited"),
        ("lucas@travelbuddy.com", "invited"),
    ]},
    {"trip": "Ooty Hill Station Retreat", "inviter": "jacobnisha923@gmail.com", "invitees": [
        ("meera@travelbuddy.com", "accepted"),
        ("aisha@travelbuddy.com", "invited"),
        ("chloe@travelbuddy.com", "accepted"),
    ]},
    # Others invite Nisha to their trips
    {"trip": "Manali Mountain Escape", "inviter": None, "invitees": [
        ("jacobnisha923@gmail.com", "accepted"),
    ]},
    {"trip": "Goa Beach Getaway", "inviter": None, "invitees": [
        ("jacobnisha923@gmail.com", "accepted"),
    ]},
    {"trip": "Kyoto Cultural Journey", "inviter": None, "invitees": [
        ("jacobnisha923@gmail.com", "invited"),
    ]},
    {"trip": "Phuket Island Hopping", "inviter": None, "invitees": [
        ("jacobnisha923@gmail.com", "accepted"),
    ]},
    {"trip": "Bali Paradise Retreat", "inviter": None, "invitees": [
        ("jacobnisha923@gmail.com", "invited"),
    ]},
    # Also add extra invitations among other seeded users for existing trips
    {"trip": "Manali Mountain Escape", "inviter": None, "invitees": [
        ("priya@travelbuddy.com", "accepted"),
        ("rohan@travelbuddy.com", "invited"),
        ("fatima@travelbuddy.com", "rejected"),
    ]},
    {"trip": "Goa Beach Getaway", "inviter": None, "invitees": [
        ("carlos@travelbuddy.com", "accepted"),
        ("nina@travelbuddy.com", "invited"),
        ("divya@travelbuddy.com", "accepted"),
    ]},
    {"trip": "Royal Jaipur Tour", "inviter": None, "invitees": [
        ("james@travelbuddy.com", "accepted"),
        ("olivia@travelbuddy.com", "invited"),
        ("aisha@travelbuddy.com", "accepted"),
    ]},
    {"trip": "Kerala Backwater Cruise", "inviter": None, "invitees": [
        ("meera@travelbuddy.com", "accepted"),
        ("sophie@travelbuddy.com", "invited"),
        ("lena@travelbuddy.com", "accepted"),
        ("ethan@travelbuddy.com", "invited"),
    ]},
    {"trip": "Delhi Heritage Walk", "inviter": None, "invitees": [
        ("rahul@travelbuddy.com", "accepted"),
        ("akash@travelbuddy.com", "invited"),
        ("mia@travelbuddy.com", "rejected"),
    ]},
    {"trip": "Rishikesh Rafting Camp", "inviter": None, "invitees": [
        ("leo@travelbuddy.com", "accepted"),
        ("sanjay@travelbuddy.com", "accepted"),
        ("vikram@travelbuddy.com", "invited"),
    ]},
]


class Command(BaseCommand):
    help = "Seed trips and invitations for jacobnisha923@gmail.com."

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("  Seed Nisha Trips & Invitations")
        self.stdout.write("=" * 60)

        nisha = User.objects.filter(email="jacobnisha923@gmail.com").first()
        if not nisha:
            self.stderr.write(self.style.ERROR("User jacobnisha923@gmail.com not found!"))
            return

        with transaction.atomic():
            trips = self._create_trips(nisha)
            self._create_trip_members(trips, nisha)
            self._create_trip_images(trips)
            self._create_weather_cache(trips)
            self._create_invitations()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✓ Nisha trips & invitations seeded successfully."))
        self.stdout.write("=" * 60)

    # ── Trips ───────────────────────────────────────────────────────
    def _create_trips(self, nisha):
        self.stdout.write("\nCreating trips for Nisha...")
        now = timezone.now().date()
        trips = []

        for td in NISHA_TRIPS:
            if td["status"] == "completed":
                start = now - timedelta(days=td["days_ago_start"])
            elif td["status"] == "upcoming":
                start = now + timedelta(days=td["days_ahead_start"])
            else:
                start = now + timedelta(days=td["days_ahead_start"])
            end = start + timedelta(days=td["duration"])

            trip, created = Trip.objects.get_or_create(
                title=td["title"],
                defaults={
                    "city": td["city"],
                    "region": td["region"],
                    "country": td["country"],
                    "latitude": td["lat"],
                    "longitude": td["lng"],
                    "start_date": start,
                    "end_date": end,
                    "cover_image": td["cover"],
                    "creator": nisha,
                    "status": td["status"],
                },
            )
            trips.append(trip)
            if created:
                self.stdout.write(f"  + {trip.title}  [{trip.status}]  {trip.start_date} → {trip.end_date}")
            else:
                self.stdout.write(f"  · {trip.title} (exists)")

        self.stdout.write(self.style.SUCCESS(f"  → {len(trips)} trips ready."))
        return trips

    # ── Trip Members (creator + random members) ─────────────────────
    def _create_trip_members(self, trips, nisha):
        self.stdout.write("\nCreating trip members...")
        other_users = list(User.objects.exclude(id=nisha.id).order_by('?'))
        count = 0

        for trip in trips:
            # Creator membership
            _, created = TripMember.objects.get_or_create(
                trip=trip, user=nisha,
                defaults={
                    "role": "creator",
                    "status": "accepted",
                    "joined_at": timezone.now() - timedelta(days=random.randint(1, 30)),
                },
            )
            if created:
                count += 1

            # Add 3-5 accepted members
            members = random.sample(other_users, k=min(random.randint(3, 5), len(other_users)))
            for m in members:
                joined = timezone.now() - timedelta(days=random.randint(1, 15))
                _, created = TripMember.objects.get_or_create(
                    trip=trip, user=m,
                    defaults={
                        "role": "member",
                        "status": "accepted",
                        "joined_at": joined,
                    },
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(f"  → {count} memberships created."))

    # ── Trip Images ─────────────────────────────────────────────────
    def _create_trip_images(self, trips):
        self.stdout.write("\nCreating trip images...")
        count = 0
        for trip in trips:
            if trip.images.exists():
                self.stdout.write(f"  · {trip.title} images exist")
                continue
            chosen = random.sample(IMAGE_POOL, k=random.randint(4, 5))
            for pos, (url, caption) in enumerate(chosen):
                TripImage.objects.create(
                    trip=trip,
                    image_data=url,
                    content_type="image/jpeg",
                    caption=caption,
                    position=pos,
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"  → {count} trip images created."))

    # ── Weather Cache ───────────────────────────────────────────────
    def _create_weather_cache(self, trips):
        self.stdout.write("\nCreating weather cache...")
        count = 0
        for trip_def, trip in zip(NISHA_TRIPS, trips):
            if TripWeatherCache.objects.filter(trip=trip).exists():
                continue
            w = trip_def["weather"]
            TripWeatherCache.objects.create(
                trip=trip,
                temperature=w["temp"],
                condition=w["condition"],
                description=w["desc"],
                icon=w["icon"],
                city_name=trip_def["city"],
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"  → {count} weather caches created."))

    # ── Invitations ─────────────────────────────────────────────────
    def _create_invitations(self):
        self.stdout.write("\nCreating trip invitations...")
        count = 0
        for spec in INVITATION_SPECS:
            trip = Trip.objects.filter(title=spec["trip"]).first()
            if not trip:
                self.stdout.write(f"  ! Trip '{spec['trip']}' not found, skipping")
                continue

            for email, status in spec["invitees"]:
                user = User.objects.filter(email=email).first()
                if not user:
                    continue

                joined = timezone.now() - timedelta(days=random.randint(1, 10)) if status == "accepted" else None
                _, created = TripMember.objects.get_or_create(
                    trip=trip, user=user,
                    defaults={
                        "role": "member",
                        "status": status,
                        "joined_at": joined,
                    },
                )
                if created:
                    count += 1
                    self.stdout.write(f"  + {email} → {trip.title} ({status})")

        self.stdout.write(self.style.SUCCESS(f"  → {count} invitations created."))
