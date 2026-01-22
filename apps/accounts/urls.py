"""
URL configuration for the accounts app.

Provides authentication endpoints:
- /api/auth/register/     - User registration
- /api/auth/login/        - User login (JWT)
- /api/auth/me/           - Get current user
- /api/auth/google/       - Google OAuth
- /api/auth/token/refresh/ - Refresh JWT token
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    LoginView,
    UserDetailView,
    GoogleAuthView,
)

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('me/', UserDetailView.as_view(), name='me'),
    path('google/', GoogleAuthView.as_view(), name='google'),
    
    # JWT token management
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
