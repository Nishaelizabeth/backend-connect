"""
Serializers for User authentication.

Handles validation and serialization for:
- User registration
- User login (JWT token generation)
- User profile retrieval
- Google OAuth authentication
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    
    Validates email uniqueness, password strength, and creates a new user
    with the 'email' auth provider.
    """
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text='Password must meet Django password validation requirements.'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Must match the password field.'
    )

    class Meta:
        model = User
        fields = ['email', 'full_name', 'password', 'password_confirm']
        extra_kwargs = {
            'email': {'required': True},
            'full_name': {'required': True},
        }

    def validate_email(self, value):
        """Ensure email is lowercase and unique."""
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return email

    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Password fields do not match.'
            })
        return attrs

    def create(self, validated_data):
        """Create and return the new user."""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            auth_provider=User.AuthProvider.EMAIL
        )
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    
    Validates credentials and returns JWT access and refresh tokens.
    """
    
    email = serializers.EmailField(
        required=True,
        help_text='User email address.'
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate_email(self, value):
        """Normalize email to lowercase."""
        return value.lower()

    def validate(self, attrs):
        """Validate user credentials."""
        email = attrs.get('email')
        password = attrs.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'email': 'No account found with this email address.'
            })

        # Check if the user registered with a different auth provider
        if user.auth_provider != User.AuthProvider.EMAIL:
            raise serializers.ValidationError({
                'email': f'This account uses {user.auth_provider} authentication. '
                        f'Please login with {user.auth_provider}.'
            })

        if not user.check_password(password):
            raise serializers.ValidationError({
                'password': 'Incorrect password.'
            })

        if not user.is_active:
            raise serializers.ValidationError({
                'email': 'This account has been deactivated.'
            })

        attrs['user'] = user
        return attrs

    def get_tokens(self, user):
        """Generate JWT tokens for the user."""
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class UserSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for user profile data.
    """
    has_preferences = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'full_name',
            'bio',
            'profile_picture',
            'profile_picture_url',
            'google_picture_url',
            'is_active',
            'is_staff',
            'date_joined',
            'auth_provider',
            'has_preferences',
        ]
        read_only_fields = fields

    def get_has_preferences(self, obj):
        """Check if the user has created preferences."""
        return hasattr(obj, 'preferences')

    def get_profile_picture_url(self, obj):
        """
        Returns the best available profile picture URL:
        uploaded picture > google picture url > None (frontend uses initial letter fallback)
        """
        request = self.context.get('request')
        if obj.profile_picture:
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        if obj.google_picture_url:
            return obj.google_picture_url
        return None


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile: full_name, bio and profile picture.
    Supports removing the profile picture by passing remove_picture=true.
    """
    remove_picture = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = User
        fields = ['full_name', 'bio', 'profile_picture', 'remove_picture']

    def update(self, instance, validated_data):
        remove_picture = validated_data.pop('remove_picture', False)
        if remove_picture:
            if instance.profile_picture:
                instance.profile_picture.delete(save=False)
            instance.profile_picture = None
        if 'full_name' in validated_data:
            instance.full_name = validated_data['full_name']
        bio = validated_data.get('bio', None)
        if bio is not None:
            instance.bio = bio
        if 'profile_picture' in validated_data and validated_data['profile_picture']:
            if instance.profile_picture:
                instance.profile_picture.delete(save=False)
            instance.profile_picture = validated_data['profile_picture']
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """
    Validate and apply a password change.
    Requires the current password for security.
    """
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True, write_only=True, validators=[validate_password]
    )
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match.'}
            )
        return attrs


class UpdateEmailSerializer(serializers.Serializer):
    """
    Validate and apply an email change.
    Requires the current password for security.
    """
    new_email = serializers.EmailField(required=True)
    current_password = serializers.CharField(required=True, write_only=True)

    def validate_new_email(self, value):
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('This email is already in use.')
        return email


class GoogleAuthSerializer(serializers.Serializer):
    """
    Serializer for Google OAuth authentication.
    
    Validates the Google Access Token, extracts user info, and either
    logs in an existing user or creates a new one.
    """
    
    access_token = serializers.CharField(
        required=True,
        help_text='Google Access Token from the frontend.'
    )

    def validate_access_token(self, value):
        """
        Verify the Google Access Token and extract user information.
        """
        import requests
        from django.conf import settings

        try:
            # Verify the token and get user info
            response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                params={'access_token': value}
            )

            if not response.ok:
                raise serializers.ValidationError('Invalid Google access token.')

            user_info = response.json()
            
            # Optional: Check audience if you want to be extra secure using tokeninfo endpoint
            # For now, userinfo availability implies validity of the token for the user

            if 'email' not in user_info:
                raise serializers.ValidationError('Token does not contain email.')

            return {
                'email': user_info.get('email'),
                'full_name': user_info.get('name', ''),
                'google_id': user_info.get('sub'),
                'picture_url': user_info.get('picture', ''),
            }

        except Exception as e:
            raise serializers.ValidationError(f'Invalid Google token: {str(e)}')

    def create(self, validated_data):
        """
        Get or create a user based on Google account information.
        """
        google_data = validated_data['access_token']
        email = google_data['email'].lower()

        try:
            user = User.objects.get(email=email)
            # Update Google picture if not already set
            if google_data.get('picture_url') and not user.google_picture_url:
                user.google_picture_url = google_data['picture_url']
                user.save(update_fields=['google_picture_url'])
        except User.DoesNotExist:
            # Create new user from Google data
            user = User.objects.create_user(
                email=email,
                full_name=google_data['full_name'],
                auth_provider=User.AuthProvider.GOOGLE,
                google_picture_url=google_data.get('picture_url', '')
            )

        return user

    def get_tokens(self, user):
        """Generate JWT tokens for the user."""
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
