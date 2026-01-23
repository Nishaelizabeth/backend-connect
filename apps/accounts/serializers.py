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
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'full_name',
            'is_active',
            'date_joined',
            'auth_provider',
            'has_preferences',
        ]
        read_only_fields = fields

    has_preferences = serializers.SerializerMethodField()

    def get_has_preferences(self, obj):
        """Check if the user has created preferences."""
        return hasattr(obj, 'preferences')


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
            # Update user info if they're logging in with Google for the first time
            if user.auth_provider == User.AuthProvider.EMAIL:
                # User originally registered with email, now linking Google
                pass
        except User.DoesNotExist:
            # Create new user from Google data
            user = User.objects.create_user(
                email=email,
                full_name=google_data['full_name'],
                auth_provider=User.AuthProvider.GOOGLE
            )

        return user

    def get_tokens(self, user):
        """Generate JWT tokens for the user."""
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
