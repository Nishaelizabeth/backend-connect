from rest_framework import serializers
from .models import Preference, Interest, PreferenceInterest

class InterestSerializer(serializers.ModelSerializer):
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Interest
        fields = ['id', 'name', 'is_active', 'is_default', 'is_mine']
        read_only_fields = ['id', 'is_active', 'is_default', 'is_mine']

    def get_is_mine(self, obj):
        """Returns True if this interest was created by the requesting user."""
        request = self.context.get('request')
        if request and not obj.is_default:
            return obj.created_by_id == request.user.id
        return False

class PreferenceSerializer(serializers.ModelSerializer):
    interest_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of interest IDs to associate with the preference"
    )

    class Meta:
        model = Preference
        fields = [
            'id', 
            'budget_range', 
            'travel_style', 
            'preferred_trip_duration', 
            'interest_ids'
        ]
        read_only_fields = ['id', 'user']

    def validate_interest_ids(self, value):
        """
        Validate that all provided interest IDs exist and are accessible by this user.
        An interest is accessible if it is a default interest or was created by this user.
        """
        request = self.context.get('request')
        user = request.user if request else None
        from django.db.models import Q
        accessible = Interest.objects.filter(
            Q(is_default=True) | Q(created_by=user),
            id__in=value,
            is_active=True
        )
        if accessible.count() != len(set(value)):
            raise serializers.ValidationError(
                "One or more interest IDs are invalid, inactive, or not accessible."
            )
        return value

    def create(self, validated_data):
        interest_ids = validated_data.pop('interest_ids', [])
        user = self.context['request'].user
        
        # Ensure user doesn't already have preferences (though view should handle this too)
        if Preference.objects.filter(user=user).exists():
             raise serializers.ValidationError("Preferences already exist for this user.")

        preference = Preference.objects.create(user=user, **validated_data)
        
        # Create M2M relations
        for interest_id in interest_ids:
            PreferenceInterest.objects.create(
                preference=preference,
                interest_id=interest_id
            )
        
        return preference

    def update(self, instance, validated_data):
        interest_ids = validated_data.pop('interest_ids', None)
        
        # Update standard fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update interests if provided
        if interest_ids is not None:
            # Clear existing interests
            instance.interests.clear()
            # Add new interests
            for interest_id in interest_ids:
                PreferenceInterest.objects.create(
                    preference=instance,
                    interest_id=interest_id
                )
                
        return instance

class PreferenceDetailSerializer(serializers.ModelSerializer):
    interests = InterestSerializer(many=True, read_only=True)

    class Meta:
        model = Preference
        fields = [
            'id',
            'user',
            'budget_range',
            'travel_style',
            'preferred_trip_duration',
            'interests',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
