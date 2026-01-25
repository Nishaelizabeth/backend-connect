from rest_framework import serializers
from .models import Destination, TripSavedDestination


class DestinationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Destination
        fields = [
            'id',
            'name',
            'city',
            'country',
            'category',
            'description',
            'image_url',
        ]


class TripSavedDestinationSerializer(serializers.ModelSerializer):
    destination = DestinationSerializer(read_only=True)
    saved_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TripSavedDestination
        fields = [
            'destination',
            'saved_by',
            'saved_at',
        ]


class SaveDestinationSerializer(serializers.Serializer):
    destination_id = serializers.IntegerField()

    def validate_destination_id(self, value):
        if not Destination.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Destination not found or inactive.")
        return value
