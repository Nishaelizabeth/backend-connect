"""
Management command to check Unsplash API status and optionally reset it.

Usage:
    python manage.py unsplash_status
    python manage.py unsplash_status --reset
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings


class Command(BaseCommand):
    help = 'Check Unsplash API status and optionally reset the disabled flag'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset the Unsplash disabled flag',
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test the Unsplash API with a simple query',
        )

    def handle(self, *args, **options):
        from apps.recommendations.services.unsplash import unsplash_service, UNSPLASH_DISABLED_KEY
        
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("UNSPLASH API STATUS"))
        self.stdout.write("="*80 + "\n")
        
        # Check API key
        api_key = getattr(settings, 'UNSPLASH_ACCESS_KEY', '')
        if api_key:
            self.stdout.write(self.style.SUCCESS(f"✓ API Key configured: {api_key[:10]}..."))
        else:
            self.stdout.write(self.style.ERROR("✗ API Key NOT configured"))
            return
        
        # Check disabled status
        is_disabled = cache.get(UNSPLASH_DISABLED_KEY)
        if is_disabled:
            self.stdout.write(self.style.WARNING("⚠ Unsplash API is currently DISABLED (due to 403 errors)"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ Unsplash API is ENABLED"))
        
        # Check cache stats
        from apps.recommendations.models import DestinationImageCache
        total_cached = DestinationImageCache.objects.count()
        unsplash_cached = DestinationImageCache.objects.filter(image_source='unsplash').count()
        fallback_cached = DestinationImageCache.objects.filter(image_source='fallback').count()
        
        self.stdout.write(f"\nCache Statistics:")
        self.stdout.write(f"  Total entries: {total_cached}")
        self.stdout.write(f"  From Unsplash: {unsplash_cached}")
        self.stdout.write(f"  Fallback: {fallback_cached}")
        
        # Reset if requested
        if options['reset']:
            cache.delete(UNSPLASH_DISABLED_KEY)
            self.stdout.write(self.style.SUCCESS("\n✓ Unsplash API has been RE-ENABLED"))
        
        # Test if requested
        if options['test']:
            self.stdout.write("\n" + "-"*80)
            self.stdout.write("Testing Unsplash API with query: 'beach'")
            self.stdout.write("-"*80)
            
            image_url = unsplash_service._search_unsplash('beach')
            
            if image_url:
                self.stdout.write(self.style.SUCCESS(f"✓ Test successful!"))
                self.stdout.write(f"  Image URL: {image_url[:60]}...")
            else:
                self.stdout.write(self.style.ERROR("✗ Test failed - check logs for details"))
                is_disabled = cache.get(UNSPLASH_DISABLED_KEY)
                if is_disabled:
                    self.stdout.write(self.style.WARNING("  API has been disabled due to errors"))
        
        self.stdout.write("\n" + "="*80 + "\n")
