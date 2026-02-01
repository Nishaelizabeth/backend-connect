from rest_framework import serializers
from .models import Destination, TripSavedDestination


class DestinationSerializer(serializers.ModelSerializer):
    """Serializer for saved/cached Destination model."""
    class Meta:
        model = Destination
        fields = [
            'id',
            'xid',
            'name',
            'city',
            'country',
            'category',
            'description',
            'image_url',
            'lat',
            'lon',
        ]


class RecommendedDestinationSerializer(serializers.Serializer):
    """
    Serializer for OpenTripMap recommendations (non-model).
    Used for API responses before destinations are saved.
    """
    xid = serializers.CharField()
    name = serializers.CharField()
    city = serializers.CharField(allow_blank=True, required=False, default='')
    image = serializers.CharField(allow_blank=True, required=False)
    image_source = serializers.CharField(
        allow_blank=True, 
        required=False,
        help_text='Source of image: opentripmap, unsplash, or fallback'
    )
    short_description = serializers.CharField(allow_blank=True, required=False)
    category = serializers.ChoiceField(
        choices=['nature', 'adventure', 'culture', 'food', 'gastronomy', 'leisure']
    )
    lat = serializers.FloatField(allow_null=True, required=False)
    lon = serializers.FloatField(allow_null=True, required=False)
    kinds = serializers.CharField(allow_blank=True, required=False)
    wikipedia = serializers.CharField(allow_blank=True, required=False)
    address = serializers.DictField(required=False)


class TripSavedDestinationSerializer(serializers.ModelSerializer):
    """Serializer for saved trip destinations."""
    destination = DestinationSerializer(read_only=True)
    saved_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TripSavedDestination
        fields = [
            'id',
            'destination',
            'saved_by',
            'saved_at',
            'order',
            'notes',
        ]


class SaveDestinationSerializer(serializers.Serializer):
    """Serializer for saving a destination by ID (legacy support)."""
    destination_id = serializers.IntegerField()

    def validate_destination_id(self, value):
        if not Destination.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Destination not found or inactive.")
        return value


class SaveDestinationFromAPISerializer(serializers.Serializer):
    """
    Serializer for saving a destination from OpenTripMap API data.
    Creates or gets the destination, then saves it to the trip.
    """
    xid = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=200)
    image = serializers.URLField(max_length=500, allow_blank=True, required=False)
    category = serializers.ChoiceField(
        choices=['nature', 'adventure', 'culture', 'food', 'leisure']
    )
    short_description = serializers.CharField(allow_blank=True, required=False, default='')
    lat = serializers.FloatField(allow_null=True, required=False)
    lon = serializers.FloatField(allow_null=True, required=False)
    kinds = serializers.CharField(max_length=500, allow_blank=True, required=False, default='')
    city = serializers.CharField(max_length=100, allow_blank=True, required=False, default='')
    notes = serializers.CharField(allow_blank=True, required=False, default='')
    
    def create_destination(self, validated_data: dict) -> Destination:
        """
        Get or create a destination from the validated data.
        """
        return Destination.get_or_create_from_opentripmap(validated_data)
