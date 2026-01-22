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
        - User object (id, email, full_name, is_active, date_joined, auth_provider)
    
    Response (401 Unauthorized):
        - Authentication credentials were not provided
    """
    
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


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
