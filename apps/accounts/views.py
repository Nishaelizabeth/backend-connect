"""
API Views for User authentication.

Provides endpoints for:
- User registration
- User login (JWT)
- User profile retrieval
- Google OAuth authentication
"""

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    GoogleAuthSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer,
    UpdateEmailSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    
    Register a new user with email and password.
    
    Request Body:
        - email (string, required): User's email address
        - password (string, required): User's password
        - password_confirm (string, required): Password confirmation
        - full_name (string, required): User's full name
    
    Response (201 Created):
        - user: User object (id, email, full_name)
        - tokens: { access, refresh }
        - message: Success message
    """
    
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens for immediate login after registration
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            'message': 'Registration successful.',
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    POST /api/auth/login/
    
    Authenticate a user with email and password.
    
    Request Body:
        - email (string, required): User's email address
        - password (string, required): User's password
    
    Response (200 OK):
        - user: User object
        - tokens: { access, refresh }
        - message: Success message
    
    Response (400 Bad Request):
        - Invalid credentials error
    """
    
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        tokens = serializer.get_tokens(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'message': 'Login successful.',
        }, status=status.HTTP_200_OK)


class UserDetailView(generics.RetrieveAPIView):
    """
    GET /api/auth/me/
    
    Retrieve the authenticated user's profile.
    
    Headers:
        - Authorization: Bearer <access_token>
    
    Response (200 OK):
        - User object (id, email, full_name, bio, profile_picture_url, ...)
    
    Response (401 Unauthorized):
        - Authentication credentials were not provided
    """
    
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return {'request': self.request}

    def get_object(self):
        return self.request.user


class ProfileUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/auth/profile/

    Update the authenticated user's bio and/or profile picture.
    Supports multipart/form-data for file uploads.

    Fields:
        - bio (string, optional)
        - profile_picture (file, optional)
        - remove_picture (boolean, optional) – set true to delete current photo
    """
    serializer_class = ProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['patch']

    def get_object(self):
        return self.request.user

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user, context={'request': request}).data,
            status=status.HTTP_200_OK
        )


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/

    Change the authenticated user's password.
    Fields: current_password, new_password, confirm_password
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            return Response(
                {'current_password': 'Incorrect password.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)


class UpdateEmailView(APIView):
    """
    POST /api/auth/update-email/

    Change the authenticated user's email.
    Fields: new_email, current_password
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UpdateEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            return Response(
                {'current_password': 'Incorrect password.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.email = serializer.validated_data['new_email']
        user.save(update_fields=['email'])
        return Response(
            UserSerializer(user, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


class GoogleAuthView(APIView):
    """
    POST /api/auth/google/
    
    Authenticate or register a user using Google OAuth.
    
    Request Body:
        - id_token (string, required): Google ID token from frontend
    
    Response (200 OK):
        - user: User object
        - tokens: { access, refresh }
        - message: Success message
        - created: Boolean indicating if a new user was created
    
    Response (400 Bad Request):
        - Invalid token error
    """
    
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if user already exists
        email = serializer.validated_data['access_token']['email'].lower()
        user_exists = User.objects.filter(email=email).exists()
        
        user = serializer.save()
        tokens = serializer.get_tokens(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'message': 'Google authentication successful.',
            'created': not user_exists,
        }, status=status.HTTP_200_OK)
