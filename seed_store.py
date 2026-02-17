"""
Seed script for Travel Store.

Run: python manage.py shell < seed_store.py
Or: python seed_store.py (with Django setup)
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.store.models import ProductCategory, Product

# Sample categories
CATEGORIES = [
    {'name': 'Luggage', 'icon': 'luggage'},
    {'name': 'Backpacks', 'icon': 'backpack'},
    {'name': 'Travel Accessories', 'icon': 'briefcase'},
    {'name': 'Electronics', 'icon': 'smartphone'},
    {'name': 'Outdoor Gear', 'icon': 'tent'},
    {'name': 'Travel Clothing', 'icon': 'shirt'},
]

# Sample products
PRODUCTS = [
    {
        'name': 'Premium Travel Backpack 40L',
        'description': 'Durable, water-resistant backpack perfect for weekend getaways. Features multiple compartments, laptop sleeve, and comfortable padded straps.',
        'price': 89.99,
        'stock_quantity': 50,
        'image': 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400',
        'category': 'Backpacks',
        'rating': 4.5,
    },
    {
        'name': 'Hard Shell Carry-On Suitcase',
        'description': 'Lightweight 20" carry-on with TSA-approved lock, spinner wheels, and expandable design. Perfect for short trips.',
        'price': 149.99,
        'stock_quantity': 30,
        'image': 'https://images.unsplash.com/photo-1565026057447-bc90a3dceb87?w=400',
        'category': 'Luggage',
        'rating': 4.7,
    },
    {
        'name': 'Noise-Cancelling Travel Headphones',
        'description': 'Premium wireless headphones with 30-hour battery life, active noise cancellation, and foldable design for travel.',
        'price': 199.99,
        'stock_quantity': 25,
        'image': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400',
        'category': 'Electronics',
        'rating': 4.8,
    },
    {
        'name': 'Universal Travel Adapter',
        'description': 'Works in 150+ countries with 4 USB ports and 1 USB-C port. Compact design with surge protection.',
        'price': 34.99,
        'stock_quantity': 100,
        'image': 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400',
        'category': 'Electronics',
        'rating': 4.6,
    },
    {
        'name': 'Compression Packing Cubes Set',
        'description': 'Set of 6 packing cubes in various sizes. Keep your luggage organized and save space with compression zippers.',
        'price': 29.99,
        'stock_quantity': 75,
        'image': 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400',
        'category': 'Travel Accessories',
        'rating': 4.4,
    },
    {
        'name': 'Portable Power Bank 20000mAh',
        'description': 'High-capacity power bank with fast charging. Charge your phone up to 5 times. LED display shows remaining power.',
        'price': 44.99,
        'stock_quantity': 60,
        'image': 'https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=400',
        'category': 'Electronics',
        'rating': 4.5,
    },
    {
        'name': 'Quick-Dry Travel Towel',
        'description': 'Microfiber towel that dries 3x faster than cotton. Compact, lightweight, and comes with a carrying pouch.',
        'price': 19.99,
        'stock_quantity': 80,
        'image': 'https://images.unsplash.com/photo-1571902943202-507ec2618e8f?w=400',
        'category': 'Travel Accessories',
        'rating': 4.3,
    },
    {
        'name': 'Ultralight Camping Tent 2-Person',
        'description': 'Weighs only 3.5 lbs! Easy setup, waterproof, and perfect for backpacking adventures.',
        'price': 179.99,
        'stock_quantity': 20,
        'image': 'https://images.unsplash.com/photo-1478131143081-80f7f84ca84d?w=400',
        'category': 'Outdoor Gear',
        'rating': 4.6,
    },
    {
        'name': 'Travel Neck Pillow Memory Foam',
        'description': 'Ergonomic memory foam neck pillow with adjustable clasp. Machine washable cover included.',
        'price': 24.99,
        'stock_quantity': 90,
        'image': 'https://images.unsplash.com/photo-1520923179278-0ea1bbb3bf96?w=400',
        'category': 'Travel Accessories',
        'rating': 4.2,
    },
    {
        'name': 'Waterproof Hiking Boots',
        'description': 'Breathable, waterproof hiking boots with excellent ankle support. Perfect for all terrains.',
        'price': 129.99,
        'stock_quantity': 35,
        'image': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400',
        'category': 'Travel Clothing',
        'rating': 4.7,
    },
    {
        'name': 'Foldable Daypack',
        'description': 'Ultra-lightweight packable daypack. Folds into a tiny pouch when not in use. Great for day trips.',
        'price': 22.99,
        'stock_quantity': 65,
        'image': 'https://images.unsplash.com/photo-1622560480605-d83c853bc5c3?w=400',
        'category': 'Backpacks',
        'rating': 4.1,
    },
    {
        'name': 'RFID Blocking Travel Wallet',
        'description': 'Slim travel wallet with RFID protection. Fits passport, cards, and cash. Premium leather construction.',
        'price': 39.99,
        'stock_quantity': 55,
        'image': 'https://images.unsplash.com/photo-1627123424574-724758594e93?w=400',
        'category': 'Travel Accessories',
        'rating': 4.5,
    },
]


def seed_store():
    """Seed the store with categories and products."""
    print("Seeding Travel Store...")
    
    # Create categories
    category_map = {}
    for cat_data in CATEGORIES:
        category, created = ProductCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={'icon': cat_data['icon']}
        )
        category_map[cat_data['name']] = category
        status = 'Created' if created else 'Exists'
        print(f"  Category: {cat_data['name']} - {status}")
    
    # Create products
    for prod_data in PRODUCTS:
        category_name = prod_data.pop('category')
        category = category_map.get(category_name)
        
        product, created = Product.objects.get_or_create(
            name=prod_data['name'],
            defaults={
                **prod_data,
                'category': category
            }
        )
        status = 'Created' if created else 'Exists'
        print(f"  Product: {prod_data['name']} - {status}")
    
    print(f"\nDone! {ProductCategory.objects.count()} categories, {Product.objects.count()} products in store.")


if __name__ == '__main__':
    seed_store()
