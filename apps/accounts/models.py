"""
Custom User Model for Travel Buddy Application.

Uses email as the unique identifier instead of username.
Supports multiple authentication providers (email, Google OAuth).
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom manager for User model with email as the unique identifier.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        
        Args:
            email: User's email address (required)
            password: User's password (optional for OAuth users)
            **extra_fields: Additional fields for the User model
            
        Returns:
            User: The created user instance
            
        Raises:
            ValueError: If email is not provided
        """
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', False)
        
        user = self.model(email=email, **extra_fields)
        
        if password:
            user.set_password(password)
        else:
            # For OAuth users who don't have a password
            user.set_unusable_password()
            
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        
        Args:
            email: Superuser's email address
            password: Superuser's password
            **extra_fields: Additional fields for the User model
            
        Returns:
            User: The created superuser instance
            
        Raises:
            ValueError: If is_staff or is_superuser is not True
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model that uses email as the unique identifier.
    
    Attributes:
        email: Primary identifier for authentication
        full_name: User's display name
        is_active: Whether the user account is active
        is_staff: Whether the user can access admin site
        date_joined: Timestamp of account creation
        auth_provider: Authentication method used ('email' or 'google')
    """
    
    class AuthProvider(models.TextChoices):
        """Supported authentication providers."""
        EMAIL = 'email', 'Email'
        GOOGLE = 'google', 'Google'

    email = models.EmailField(
        unique=True,
        max_length=255,
        verbose_name='Email Address',
        help_text='Required. Must be a valid email address.'
    )
    full_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Full Name'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active',
        help_text='Designates whether this user should be treated as active.'
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name='Staff Status',
        help_text='Designates whether the user can log into the admin site.'
    )
    date_joined = models.DateTimeField(
        default=timezone.now,
        verbose_name='Date Joined'
    )
    auth_provider = models.CharField(
        max_length=20,
        choices=AuthProvider.choices,
        default=AuthProvider.EMAIL,
        verbose_name='Authentication Provider',
        help_text='The method used to authenticate this user.'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email is already required by USERNAME_FIELD

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the user's full name or email if not set."""
        return self.full_name or self.email

    def get_short_name(self):
        """Return the user's email as a short identifier."""
        return self.email
