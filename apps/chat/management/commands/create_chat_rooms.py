"""
Management command to create chat rooms for existing trips.
Run this after adding the chat app to ensure all trips have chat rooms.
"""
from django.core.management.base import BaseCommand
from apps.trips.models import Trip
from apps.chat.models import ChatRoom


class Command(BaseCommand):
    help = 'Create chat rooms for existing trips that do not have one'

    def handle(self, *args, **options):
        trips_without_chat = Trip.objects.filter(chat_room__isnull=True)
        count = trips_without_chat.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('All trips already have chat rooms.'))
            return
        
        self.stdout.write(f'Creating chat rooms for {count} trips...')
        
        for trip in trips_without_chat:
            ChatRoom.objects.create(trip=trip)
            self.stdout.write(f'  Created chat room for: {trip.title}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} chat rooms.'))
