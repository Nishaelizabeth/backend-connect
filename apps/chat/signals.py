from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.trips.models import Trip
from .models import ChatRoom


@receiver(post_save, sender=Trip)
def create_chat_room_for_trip(sender, instance, created, **kwargs):
    """
    Automatically create a ChatRoom when a new Trip is created.
    """
    if created:
        ChatRoom.objects.create(trip=instance)
