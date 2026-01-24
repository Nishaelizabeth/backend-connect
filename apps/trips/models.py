from django.db import models
from django.conf import settings


class Trip(models.Model):
    class Status(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        UPCOMING = 'upcoming', 'Upcoming'
        COMPLETED = 'completed', 'Completed'

    title = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_trips'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return f"{self.title} ({self.start_date} → {self.end_date})"


class TripMember(models.Model):
    class Role(models.TextChoices):
        CREATOR = 'creator', 'Creator'
        MEMBER = 'member', 'Member'

    class MembershipStatus(models.TextChoices):
        INVITED = 'invited', 'Invited'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trip_memberships'
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=20, choices=MembershipStatus.choices, default=MembershipStatus.INVITED)
    joined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('trip', 'user')

    def __str__(self):
        return f"{self.user} in {self.trip} ({self.status})"
