"""
Trip Conflict Detection and Resolution Service.

Handles detection of overlapping trips when a user accepts an invitation,
and performs atomic resolution (leave old trip, join new trip, post system message).
"""

import logging
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.trips.models import Trip, TripMember
from apps.chat.models import ChatRoom, Message
from apps.notifications.models import Notification

logger = logging.getLogger(__name__)


def detect_conflicts(user, trip):
    """
    Check whether *user* already belongs to a trip whose dates overlap
    with *trip*.

    Returns a list of dicts, one per conflicting trip:
        [{
            "id": 12,
            "name": "Manali Adventure",
            "creator": "Rahul",
            "start_date": "2026-03-05",
            "end_date": "2026-03-07",
        }]

    An empty list means no conflict.
    """
    overlapping = (
        Trip.objects
        .filter(
            Q(creator=user)
            | Q(
                members__user=user,
                members__status=TripMember.MembershipStatus.ACCEPTED,
            ),
        )
        .exclude(pk=trip.pk)
        .filter(
            start_date__lte=trip.end_date,
            end_date__gte=trip.start_date,
        )
        .distinct()
        .select_related("creator")
    )

    return [
        {
            "id": t.id,
            "name": t.title,
            "creator": t.creator.full_name or t.creator.email,
            "start_date": str(t.start_date),
            "end_date": str(t.end_date),
        }
        for t in overlapping
    ]


@transaction.atomic
def accept_with_conflict_resolution(user, new_trip, conflicting_trip_ids=None):
    """
    Accept the invitation to *new_trip* while atomically leaving every
    conflicting trip.

    Steps (inside a single DB transaction):
    1.  Identify the conflicting trips (or use *conflicting_trip_ids*).
    2.  For each conflicting trip:
        a.  Mark the user's membership as ``left``.
        b.  Post a system chat message in that trip's room.
        c.  Notify the trip creator.
    3.  Accept the invitation (mark membership as ``accepted``).

    Returns the updated ``TripMember`` for *new_trip*.

    Raises ``TripMember.DoesNotExist`` if the user has no pending
    invitation for *new_trip*.
    """

    # 1. Resolve conflicting trips -------------------------------------------
    if conflicting_trip_ids is None:
        conflicts = detect_conflicts(user, new_trip)
        conflicting_trip_ids = [c["id"] for c in conflicts]

    user_display = user.full_name or user.email

    for old_trip_id in conflicting_trip_ids:
        try:
            old_trip = Trip.objects.select_related("creator").get(pk=old_trip_id)
        except Trip.DoesNotExist:
            continue

        membership_qs = TripMember.objects.filter(
            trip=old_trip,
            user=user,
            status=TripMember.MembershipStatus.ACCEPTED,
        )
        if not membership_qs.exists():
            # User might be the creator – mark as left as well
            membership_qs = TripMember.objects.filter(
                trip=old_trip,
                user=user,
            ).exclude(status=TripMember.MembershipStatus.LEFT)

        updated = membership_qs.update(status=TripMember.MembershipStatus.LEFT)

        if updated:
            # 2b. System message in old trip chat --------------------------------
            _post_system_message(
                old_trip,
                f"{user_display} left the trip and joined another trip. See you later!",
            )

            # 2c. Notify old trip creator ----------------------------------------
            if old_trip.creator != user:
                Notification.create_member_left_trip(
                    user=old_trip.creator,
                    member_name=user_display,
                    trip=old_trip,
                )

    # 3. Accept the new invitation -------------------------------------------
    membership = TripMember.objects.get(
        trip=new_trip,
        user=user,
        status=TripMember.MembershipStatus.INVITED,
    )
    membership.status = TripMember.MembershipStatus.ACCEPTED
    membership.joined_at = timezone.now()
    membership.save()

    # Notify new trip creator
    Notification.create_trip_invite_accepted(
        sender=new_trip.creator,
        receiver=user,
        trip=new_trip,
    )

    return membership


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post_system_message(trip, content):
    """
    Create a system ``Message`` in the trip's chat room and broadcast it
    over the WebSocket channel layer (if available).
    """
    try:
        room = ChatRoom.objects.get(trip=trip)
    except ChatRoom.DoesNotExist:
        logger.warning("No chat room for trip %s – skipping system message.", trip.id)
        return

    message = Message.objects.create(
        room=room,
        sender=None,
        content=content,
        is_system=True,
    )

    # Best-effort WebSocket broadcast (works only when channel layer is up)
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"trip_{trip.id}",
                {
                    "type": "system_message",
                    "message": {
                        "id": message.id,
                        "content": message.content,
                        "created_at": message.created_at.isoformat(),
                        "is_system": True,
                        "sender_id": None,
                        "sender_name": "System",
                    },
                },
            )
    except Exception as exc:
        logger.warning("Failed to broadcast system message for trip %s: %s", trip.id, exc)
