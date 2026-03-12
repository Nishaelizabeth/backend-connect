"""
Management command to seed realistic demo data for Travel Buddy.

Usage:
    python manage.py seed_demo_data
"""

import random
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.accounts.models import User
from apps.preferences.models import Interest, Preference, PreferenceInterest
from apps.buddies.models import BuddyMatch, BuddyRequest
from apps.trips.models import Trip, TripMember, TripImage, TripWeatherCache
from apps.store.models import (
    ProductCategory, Product, Wishlist, Cart, CartItem, Order, OrderItem,
)

PASSWORD = "College@123"

# ── Users ───────────────────────────────────────────────────────────
USER_DATA = [
    {"email": "alex@travelbuddy.com", "full_name": "Alex Turner", "bio": "Adventure lover exploring mountains and valleys."},
    {"email": "maria@travelbuddy.com", "full_name": "Maria Santos", "bio": "Food explorer searching for local cuisine worldwide."},
    {"email": "rahul@travelbuddy.com", "full_name": "Rahul Sharma", "bio": "Backpacker discovering hidden places across Asia."},
    {"email": "sara@travelbuddy.com", "full_name": "Sara Johnson", "bio": "Luxury traveler enjoying premium stays and fine dining."},
    {"email": "john@travelbuddy.com", "full_name": "John Mitchell", "bio": "Travel photographer capturing landscapes and cultures."},
    {"email": "priya@travelbuddy.com", "full_name": "Priya Patel", "bio": "Solo traveler who loves sunrise hikes and temple visits."},
    {"email": "david@travelbuddy.com", "full_name": "David Kim", "bio": "Tech nomad working remotely from cafés around the world."},
    {"email": "ananya@travelbuddy.com", "full_name": "Ananya Gupta", "bio": "Wildlife enthusiast chasing safaris and nature trails."},
    {"email": "carlos@travelbuddy.com", "full_name": "Carlos Rivera", "bio": "Surfing and beach life advocate from coast to coast."},
    {"email": "emi@travelbuddy.com", "full_name": "Emi Tanaka", "bio": "Cultural explorer diving into traditions and festivals."},
    {"email": "arjun@travelbuddy.com", "full_name": "Arjun Nair", "bio": "Road trip fanatic who has driven across three continents."},
    {"email": "olivia@travelbuddy.com", "full_name": "Olivia Brown", "bio": "Museum lover and art history buff on every vacation."},
    {"email": "vikram@travelbuddy.com", "full_name": "Vikram Singh", "bio": "Camping under the stars and living off the grid."},
    {"email": "nina@travelbuddy.com", "full_name": "Nina Petrova", "bio": "Nightlife explorer who finds the best rooftop bars."},
    {"email": "leo@travelbuddy.com", "full_name": "Leo Martinez", "bio": "Mountain biker tackling trails in every new country."},
    {"email": "meera@travelbuddy.com", "full_name": "Meera Reddy", "bio": "Yoga retreat seeker and spiritual journeyer."},
    {"email": "james@travelbuddy.com", "full_name": "James O'Brien", "bio": "History nerd visiting battlefields and ancient ruins."},
    {"email": "aisha@travelbuddy.com", "full_name": "Aisha Khan", "bio": "Shopping addict exploring bazaars and boutiques."},
    {"email": "lucas@travelbuddy.com", "full_name": "Lucas Fischer", "bio": "Scuba diver exploring coral reefs and underwater caves."},
    {"email": "divya@travelbuddy.com", "full_name": "Divya Menon", "bio": "Budget traveler proving you can see the world for less."},
    {"email": "ethan@travelbuddy.com", "full_name": "Ethan Clark", "bio": "Ski season chaser hopping between alpine resorts."},
    {"email": "fatima@travelbuddy.com", "full_name": "Fatima Al-Hassan", "bio": "Desert explorer fascinated by dunes and oases."},
    {"email": "rohan@travelbuddy.com", "full_name": "Rohan Desai", "bio": "Food vlogger documenting street food around India."},
    {"email": "chloe@travelbuddy.com", "full_name": "Chloe Martin", "bio": "Eco traveler supporting sustainable tourism projects."},
    {"email": "sanjay@travelbuddy.com", "full_name": "Sanjay Iyer", "bio": "Paragliding and adventure sports enthusiast."},
    {"email": "lena@travelbuddy.com", "full_name": "Lena Johansson", "bio": "Northern lights chaser and Arctic explorer."},
    {"email": "akash@travelbuddy.com", "full_name": "Akash Verma", "bio": "Train journey lover crisscrossing India by rail."},
    {"email": "sophie@travelbuddy.com", "full_name": "Sophie Dubois", "bio": "Wine-country wanderer touring vineyards and châteaux."},
    {"email": "ravi@travelbuddy.com", "full_name": "Ravi Kumar", "bio": "Trekker who summited Everest Base Camp twice."},
    {"email": "mia@travelbuddy.com", "full_name": "Mia Chen", "bio": "Digital artist sketching skylines in every city she visits."},
]

PORTRAIT_URLS = [
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1552058544-f2b08422138a?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1519345182560-3f2917c472ef?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1463453091185-61582044d556?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1542206395-9feb3edaa68d?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1504257432389-52343af06ae3?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1558898479-33c0057a5d12?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1500917293891-ef795e70e1f6?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1546961342-ea5f71b193f3?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1535930749574-1399327ce78f?w=200&h=200&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1544723795-3fb6469f5b39?w=200&h=200&fit=crop&crop=face",
]

# ── Interests ───────────────────────────────────────────────────────
DEFAULT_INTERESTS = [
    "Beaches", "Mountains", "Hiking", "Adventure Sports", "Camping",
    "Road Trips", "Photography", "Food", "Nightlife", "Culture",
    "Temples", "Wildlife", "Shopping", "Museums", "Nature",
]

BUDGETS = ["low", "medium", "high"]
STYLES = ["solo", "group", "family", "adventure", "leisure"]
DURATIONS = ["weekend", "short", "long"]

# ── Trips ───────────────────────────────────────────────────────────
TRIP_DESTINATIONS = [
    {"title": "Manali Mountain Escape", "city": "Manali", "region": "Himachal Pradesh", "country": "India", "lat": 32.2396, "lng": 77.1887},
    {"title": "Goa Beach Getaway", "city": "Goa", "region": "Goa", "country": "India", "lat": 15.2993, "lng": 74.1240},
    {"title": "Royal Jaipur Tour", "city": "Jaipur", "region": "Rajasthan", "country": "India", "lat": 26.9124, "lng": 75.7873},
    {"title": "Kerala Backwater Cruise", "city": "Alleppey", "region": "Kerala", "country": "India", "lat": 9.4981, "lng": 76.3388},
    {"title": "Leh Ladakh Adventure", "city": "Leh", "region": "Ladakh", "country": "India", "lat": 34.1526, "lng": 77.5771},
    {"title": "Delhi Heritage Walk", "city": "Delhi", "region": "Delhi", "country": "India", "lat": 28.6139, "lng": 77.2090},
    {"title": "Rishikesh Rafting Camp", "city": "Rishikesh", "region": "Uttarakhand", "country": "India", "lat": 30.0869, "lng": 78.2676},
    {"title": "Bali Paradise Retreat", "city": "Bali", "region": "Bali", "country": "Indonesia", "lat": -8.3405, "lng": 115.0920},
    {"title": "Kyoto Cultural Journey", "city": "Kyoto", "region": "Kyoto", "country": "Japan", "lat": 35.0116, "lng": 135.7681},
    {"title": "Phuket Island Hopping", "city": "Phuket", "region": "Phuket", "country": "Thailand", "lat": 7.8804, "lng": 98.3923},
    {"title": "Coorg Coffee Trail", "city": "Coorg", "region": "Karnataka", "country": "India", "lat": 12.3375, "lng": 75.8069},
    {"title": "Udaipur Lake City Vibes", "city": "Udaipur", "region": "Rajasthan", "country": "India", "lat": 24.5854, "lng": 73.7125},
]

COVER_IMAGES = [
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1587474260584-136574528ed5?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1583309219338-a582f1f9ca6b?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1589394815804-964ed0be2eb5?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1506461883276-594a12b11cf3?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1568495248636-6432b97bd949?w=800&h=400&fit=crop",
]

TRIP_IMAGE_URLS = [
    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1506197603052-3cc9c3a201bd?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1530789253388-582c481c54b0?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1433838552652-f9a46b332c40?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1549144511-f099e773c147?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1512100356356-de1b84283e18?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1470770903676-69b98201ea1c?w=600&h=400&fit=crop",
]

TRIP_CAPTIONS = [
    "Beautiful mountain sunrise",
    "Beach sunset vibes",
    "City skyline at night",
    "Temple architecture",
    "Lush green landscapes",
    "Golden hour by the lake",
    "Street food adventures",
    "Local market colors",
    "Misty morning trails",
    "Riverside camping spot",
]

WEATHER_DATA = [
    {"temp": 18, "condition": "Clouds", "desc": "scattered clouds", "icon": "03d", "city": "Manali"},
    {"temp": 32, "condition": "Clear", "desc": "clear sky", "icon": "01d", "city": "Goa"},
    {"temp": 35, "condition": "Haze", "desc": "haze", "icon": "50d", "city": "Jaipur"},
    {"temp": 28, "condition": "Rain", "desc": "moderate rain", "icon": "10d", "city": "Alleppey"},
    {"temp": 8, "condition": "Clear", "desc": "clear sky", "icon": "01d", "city": "Leh"},
    {"temp": 30, "condition": "Haze", "desc": "haze", "icon": "50d", "city": "Delhi"},
    {"temp": 22, "condition": "Clouds", "desc": "few clouds", "icon": "02d", "city": "Rishikesh"},
    {"temp": 29, "condition": "Clouds", "desc": "broken clouds", "icon": "04d", "city": "Bali"},
    {"temp": 20, "condition": "Rain", "desc": "light rain", "icon": "10d", "city": "Kyoto"},
    {"temp": 31, "condition": "Clear", "desc": "clear sky", "icon": "01d", "city": "Phuket"},
    {"temp": 24, "condition": "Mist", "desc": "mist", "icon": "50d", "city": "Coorg"},
    {"temp": 33, "condition": "Clear", "desc": "clear sky", "icon": "01d", "city": "Udaipur"},
]

# ── Store ───────────────────────────────────────────────────────────
CATEGORY_DATA = [
    {"name": "Travel Bags", "icon": "luggage"},
    {"name": "Camping Gear", "icon": "tent"},
    {"name": "Travel Accessories", "icon": "compass"},
    {"name": "Photography Gear", "icon": "camera"},
    {"name": "Travel Clothing", "icon": "shirt"},
]

PRODUCT_DATA = [
    {"name": "Hiking Backpack 50L", "desc": "Durable 50-litre hiking backpack with rain cover and multiple compartments.", "price": 3499, "cat": "Travel Bags", "img": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop"},
    {"name": "Portable Travel Pillow", "desc": "Memory foam neck pillow for comfortable flights and long journeys.", "price": 899, "cat": "Travel Accessories", "img": "https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?w=400&h=400&fit=crop"},
    {"name": "Waterproof Phone Pouch", "desc": "Universal waterproof phone case for beaches and water activities.", "price": 499, "cat": "Travel Accessories", "img": "https://images.unsplash.com/photo-1601784551446-20c9e07cdbdb?w=400&h=400&fit=crop"},
    {"name": "Travel Camera Tripod", "desc": "Lightweight aluminium tripod perfect for travel photography.", "price": 2199, "cat": "Photography Gear", "img": "https://images.unsplash.com/photo-1617575521317-d2974f3b56d2?w=400&h=400&fit=crop"},
    {"name": "Compact Sleeping Bag", "desc": "Ultra-light sleeping bag rated for 0°C, packs down small.", "price": 2799, "cat": "Camping Gear", "img": "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=400&h=400&fit=crop"},
    {"name": "Travel Organizer Kit", "desc": "6-piece packing cube set for efficient suitcase organization.", "price": 1299, "cat": "Travel Accessories", "img": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop"},
    {"name": "Adventure Daypack 25L", "desc": "Compact daypack for city walks and short hikes.", "price": 1899, "cat": "Travel Bags", "img": "https://images.unsplash.com/photo-1622560480605-d83c853bc5c3?w=400&h=400&fit=crop"},
    {"name": "Headlamp 600 Lumens", "desc": "Rechargeable headlamp with red-light mode for night trekking.", "price": 1499, "cat": "Camping Gear", "img": "https://images.unsplash.com/photo-1525385133512-2f3bdd039054?w=400&h=400&fit=crop"},
    {"name": "Quick-Dry Travel Towel", "desc": "Microfiber towel that dries 3x faster than cotton.", "price": 699, "cat": "Travel Accessories", "img": "https://images.unsplash.com/photo-1600269452121-4f2416e55c28?w=400&h=400&fit=crop"},
    {"name": "UV Protection Sunglasses", "desc": "Polarized adventure sunglasses with UV400 protection.", "price": 1599, "cat": "Travel Clothing", "img": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400&h=400&fit=crop"},
    {"name": "Trekking Poles (Pair)", "desc": "Collapsible carbon-fibre trekking poles with cork grips.", "price": 2499, "cat": "Camping Gear", "img": "https://images.unsplash.com/photo-1551632811-561732d1e306?w=400&h=400&fit=crop"},
    {"name": "Action Camera Mount Kit", "desc": "Universal mount kit compatible with GoPro and action cameras.", "price": 1799, "cat": "Photography Gear", "img": "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=400&h=400&fit=crop"},
    {"name": "Insulated Water Bottle 1L", "desc": "Double-wall vacuum bottle keeps drinks cold 24h or hot 12h.", "price": 999, "cat": "Travel Accessories", "img": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400&h=400&fit=crop"},
    {"name": "Rain Jacket – Ultralight", "desc": "Packable rain jacket weighing only 180g with sealed seams.", "price": 2999, "cat": "Travel Clothing", "img": "https://images.unsplash.com/photo-1545594861-3bef43ff2fc8?w=400&h=400&fit=crop"},
    {"name": "Dry Bag 20L", "desc": "Roll-top dry bag for kayaking, rafting, and beach trips.", "price": 799, "cat": "Travel Bags", "img": "https://images.unsplash.com/photo-1530789253388-582c481c54b0?w=400&h=400&fit=crop"},
    {"name": "Multi-tool Travel Knife", "desc": "14-function stainless steel multi-tool with belt pouch.", "price": 1199, "cat": "Camping Gear", "img": "https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?w=400&h=400&fit=crop"},
    {"name": "Camera Lens Cleaning Kit", "desc": "Professional lens cleaning set with blower, pen and cloths.", "price": 599, "cat": "Photography Gear", "img": "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=400&h=400&fit=crop"},
    {"name": "Travel Hammock", "desc": "Lightweight parachute-nylon hammock with tree straps.", "price": 1699, "cat": "Camping Gear", "img": "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400&h=400&fit=crop"},
    {"name": "Convertible Travel Pants", "desc": "Zip-off cargo pants that convert to shorts — wrinkle free.", "price": 1899, "cat": "Travel Clothing", "img": "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=400&h=400&fit=crop"},
    {"name": "Solar Power Bank 20000mAh", "desc": "Rugged solar charger with dual USB and LED flashlight.", "price": 2499, "cat": "Travel Accessories", "img": "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=400&h=400&fit=crop"},
]

SHIPPING_ADDRESSES = [
    "42 MG Road, Bengaluru, Karnataka 560001",
    "15 Park Street, Kolkata, West Bengal 700016",
    "8 Marine Drive, Mumbai, Maharashtra 400020",
    "23 Connaught Place, New Delhi, Delhi 110001",
    "56 Anna Salai, Chennai, Tamil Nadu 600002",
    "77 Banjara Hills, Hyderabad, Telangana 500034",
    "3 Residency Road, Pune, Maharashtra 411001",
    "19 Civil Lines, Jaipur, Rajasthan 302006",
    "101 MG Road, Kochi, Kerala 682011",
    "5 Hazratganj, Lucknow, Uttar Pradesh 226001",
]


class Command(BaseCommand):
    help = "Seed realistic demo data for the Travel Buddy platform."

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("  Travel Buddy — Demo Data Seeder")
        self.stdout.write("=" * 60)

        with transaction.atomic():
            users = self._create_users()
            interests = self._create_interests()
            self._create_preferences(users, interests)
            self._create_buddy_connections(users)
            trips = self._create_trips(users)
            self._create_trip_members(trips, users)
            self._create_trip_invitations(trips, users)
            self._create_trip_images(trips)
            self._create_weather_cache(trips)
            categories, products = self._create_store()
            self._create_wishlists(users, products)
            self._create_carts(users, products)
            self._create_orders(users, products)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✓ Demo data seeding completed successfully."))
        self.stdout.write("=" * 60)

    # ── Users ───────────────────────────────────────────────────────
    def _create_users(self):
        self.stdout.write("\nCreating users...")
        users = []
        for i, data in enumerate(USER_DATA):
            user, created = User.objects.get_or_create(
                email=data["email"],
                defaults={
                    "full_name": data["full_name"],
                    "bio": data["bio"],
                    "auth_provider": "email",
                    "google_picture_url": PORTRAIT_URLS[i % len(PORTRAIT_URLS)],
                },
            )
            if created:
                user.set_password(PASSWORD)
                user.save()
                self.stdout.write(f"  + {user.email}")
            else:
                self.stdout.write(f"  · {user.email} (exists)")
            users.append(user)
        self.stdout.write(self.style.SUCCESS(f"  → {len(users)} users ready."))
        return users

    # ── Interests ───────────────────────────────────────────────────
    def _create_interests(self):
        self.stdout.write("\nCreating interests...")
        interests = []
        for name in DEFAULT_INTERESTS:
            obj, created = Interest.objects.get_or_create(
                name=name,
                is_default=True,
                defaults={"is_active": True},
            )
            interests.append(obj)
            if created:
                self.stdout.write(f"  + {name}")
        self.stdout.write(self.style.SUCCESS(f"  → {len(interests)} interests ready."))
        return interests

    # ── Preferences ─────────────────────────────────────────────────
    def _create_preferences(self, users, interests):
        self.stdout.write("\nCreating preferences...")
        count = 0
        for user in users:
            pref, created = Preference.objects.get_or_create(
                user=user,
                defaults={
                    "budget_range": random.choice(BUDGETS),
                    "travel_style": random.choice(STYLES),
                    "preferred_trip_duration": random.choice(DURATIONS),
                },
            )
            if created:
                chosen = random.sample(interests, k=random.randint(3, 6))
                for interest in chosen:
                    PreferenceInterest.objects.get_or_create(
                        preference=pref,
                        interest=interest,
                    )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"  → {count} new preferences created."))

    # ── Buddy Connections ───────────────────────────────────────────
    def _create_buddy_connections(self, users):
        self.stdout.write("\nCreating buddy connections...")
        pairs_created = 0
        requests_created = 0
        attempted = set()

        # Create ~40 buddy relationships
        while pairs_created < 40 and len(attempted) < len(users) * (len(users) - 1):
            u1, u2 = random.sample(users, 2)
            pair = (min(u1.id, u2.id), max(u1.id, u2.id))
            if pair in attempted:
                continue
            attempted.add(pair)

            score = round(random.uniform(40, 95), 1)
            _, c1 = BuddyMatch.objects.get_or_create(
                user=u1, matched_user=u2,
                defaults={"match_score": score, "status": "connected"},
            )
            _, c2 = BuddyMatch.objects.get_or_create(
                user=u2, matched_user=u1,
                defaults={"match_score": score, "status": "connected"},
            )
            if c1 or c2:
                pairs_created += 1

            # Also create a BuddyRequest for some
            status = random.choice(["accepted", "accepted", "pending"])
            _, rc = BuddyRequest.objects.get_or_create(
                sender=u1, receiver=u2,
                defaults={"status": status},
            )
            if rc:
                requests_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"  → {pairs_created} buddy pairs, {requests_created} requests created."
        ))

    # ── Trips ───────────────────────────────────────────────────────
    def _create_trips(self, users):
        self.stdout.write("\nCreating trips...")
        now = timezone.now().date()
        trips = []

        status_pool = (
            ["planned"] * 4 + ["upcoming"] * 4 + ["completed"] * 4
        )
        random.shuffle(status_pool)

        for i, dest in enumerate(TRIP_DESTINATIONS):
            s = status_pool[i]
            if s == "planned":
                start = now + timedelta(days=random.randint(35, 90))
            elif s == "upcoming":
                start = now + timedelta(days=random.randint(3, 18))
            else:
                start = now - timedelta(days=random.randint(10, 120))
            end = start + timedelta(days=random.randint(3, 10))

            trip, created = Trip.objects.get_or_create(
                title=dest["title"],
                defaults={
                    "city": dest["city"],
                    "region": dest["region"],
                    "country": dest["country"],
                    "latitude": dest["lat"],
                    "longitude": dest["lng"],
                    "start_date": start,
                    "end_date": end,
                    "cover_image": COVER_IMAGES[i % len(COVER_IMAGES)],
                    "creator": random.choice(users),
                    "status": s,
                },
            )
            trips.append(trip)
            if created:
                self.stdout.write(f"  + {trip.title} ({trip.status})")
            else:
                self.stdout.write(f"  · {trip.title} (exists)")

        self.stdout.write(self.style.SUCCESS(f"  → {len(trips)} trips ready."))
        return trips

    # ── Trip Members ────────────────────────────────────────────────
    def _create_trip_members(self, trips, users):
        self.stdout.write("\nCreating trip members...")
        count = 0
        for trip in trips:
            # Creator membership
            _, created = TripMember.objects.get_or_create(
                trip=trip, user=trip.creator,
                defaults={
                    "role": "creator",
                    "status": "accepted",
                    "joined_at": timezone.now() - timedelta(days=random.randint(1, 30)),
                },
            )
            if created:
                count += 1

            # Pick 3-6 random members (excluding creator)
            candidates = [u for u in users if u.id != trip.creator_id]
            members = random.sample(candidates, k=min(random.randint(3, 6), len(candidates)))
            for m in members:
                status = random.choices(
                    ["accepted", "invited", "rejected", "left"],
                    weights=[60, 20, 10, 10],
                )[0]
                joined = timezone.now() - timedelta(days=random.randint(1, 20)) if status == "accepted" else None
                _, created = TripMember.objects.get_or_create(
                    trip=trip, user=m,
                    defaults={
                        "role": "member",
                        "status": status,
                        "joined_at": joined,
                    },
                )
                if created:
                    count += 1
        self.stdout.write(self.style.SUCCESS(f"  → {count} trip memberships created."))

    # ── Trip Invitations (via TripMember INVITED) ───────────────────
    def _create_trip_invitations(self, trips, users):
        self.stdout.write("\nCreating trip invitations...")
        count = 0
        for trip in random.sample(trips, k=min(8, len(trips))):
            candidates = [u for u in users if u.id != trip.creator_id]
            invitees = random.sample(candidates, k=min(random.randint(2, 4), len(candidates)))
            for invitee in invitees:
                _, created = TripMember.objects.get_or_create(
                    trip=trip, user=invitee,
                    defaults={
                        "role": "member",
                        "status": "invited",
                    },
                )
                if created:
                    count += 1
        self.stdout.write(self.style.SUCCESS(f"  → {count} invitations created."))

    # ── Trip Images ─────────────────────────────────────────────────
    def _create_trip_images(self, trips):
        self.stdout.write("\nCreating trip images...")
        count = 0
        for trip in trips:
            if trip.images.exists():
                continue
            num_images = random.randint(3, 5)
            for pos in range(num_images):
                url = random.choice(TRIP_IMAGE_URLS)
                TripImage.objects.create(
                    trip=trip,
                    image_data=url,
                    content_type="image/jpeg",
                    caption=random.choice(TRIP_CAPTIONS),
                    position=pos,
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"  → {count} trip images created."))

    # ── Weather Cache ───────────────────────────────────────────────
    def _create_weather_cache(self, trips):
        self.stdout.write("\nCreating weather cache...")
        count = 0
        for i, trip in enumerate(trips):
            if hasattr(trip, 'weather_cache') and TripWeatherCache.objects.filter(trip=trip).exists():
                continue
            w = WEATHER_DATA[i % len(WEATHER_DATA)]
            TripWeatherCache.objects.create(
                trip=trip,
                temperature=w["temp"],
                condition=w["condition"],
                description=w["desc"],
                icon=w["icon"],
                city_name=w["city"],
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"  → {count} weather caches created."))

    # ── Store ───────────────────────────────────────────────────────
    def _create_store(self):
        self.stdout.write("\nCreating store categories & products...")
        categories = {}
        for cd in CATEGORY_DATA:
            cat, _ = ProductCategory.objects.get_or_create(
                name=cd["name"],
                defaults={"icon": cd["icon"]},
            )
            categories[cd["name"]] = cat

        products = []
        for pd in PRODUCT_DATA:
            product, created = Product.objects.get_or_create(
                name=pd["name"],
                defaults={
                    "description": pd["desc"],
                    "price": Decimal(str(pd["price"])),
                    "stock_quantity": random.randint(10, 100),
                    "image": pd["img"],
                    "category": categories.get(pd["cat"]),
                    "rating": Decimal(str(round(random.uniform(3.5, 4.9), 1))),
                    "is_active": True,
                },
            )
            products.append(product)
            if created:
                self.stdout.write(f"  + {product.name}")
        self.stdout.write(self.style.SUCCESS(
            f"  → {len(categories)} categories, {len(products)} products ready."
        ))
        return categories, products

    # ── Wishlists ───────────────────────────────────────────────────
    def _create_wishlists(self, users, products):
        self.stdout.write("\nCreating wishlists...")
        count = 0
        for user in users:
            items = random.sample(products, k=random.randint(1, 4))
            for prod in items:
                _, created = Wishlist.objects.get_or_create(user=user, product=prod)
                if created:
                    count += 1
        self.stdout.write(self.style.SUCCESS(f"  → {count} wishlist items created."))

    # ── Carts ───────────────────────────────────────────────────────
    def _create_carts(self, users, products):
        self.stdout.write("\nCreating carts...")
        count = 0
        for user in users:
            cart, _ = Cart.objects.get_or_create(user=user)
            if cart.items.exists():
                continue
            items = random.sample(products, k=random.randint(1, 3))
            for prod in items:
                CartItem.objects.get_or_create(
                    cart=cart, product=prod,
                    defaults={"quantity": random.randint(1, 3)},
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"  → {count} cart items created."))

    # ── Orders ──────────────────────────────────────────────────────
    def _create_orders(self, users, products):
        self.stdout.write("\nCreating orders...")
        count = 0
        buyer_pool = random.sample(users, k=min(10, len(users)))
        statuses = ["paid", "paid", "paid", "paid", "pending", "pending", "pending", "cancelled", "cancelled", "cancelled"]
        random.shuffle(statuses)

        for idx, buyer in enumerate(buyer_pool):
            status = statuses[idx % len(statuses)]
            order_products = random.sample(products, k=random.randint(1, 4))
            total = sum(p.price * random.randint(1, 2) for p in order_products)

            # Check if user already has an order with the same status created by seed
            if Order.objects.filter(user=buyer).count() >= 2:
                continue

            order = Order.objects.create(
                user=buyer,
                total_amount=total,
                status=status,
                shipping_address=random.choice(SHIPPING_ADDRESSES),
            )
            for prod in order_products:
                qty = random.randint(1, 2)
                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    product_name=prod.name,
                    quantity=qty,
                    price=prod.price,
                )
            count += 1
            self.stdout.write(f"  + Order #{order.id} ({status}) for {buyer.email}")

        self.stdout.write(self.style.SUCCESS(f"  → {count} orders created."))
