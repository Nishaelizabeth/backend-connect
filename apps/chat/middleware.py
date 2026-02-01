"""
JWT Authentication middleware for Django Channels WebSocket connections.
Validates JWT tokens passed via query string or headers.
"""
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import get_user_model

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_string):
    """
    Validate JWT token and return the associated user.
    """
    try:
        # Decode the token
        access_token = AccessToken(token_string)
        user_id = access_token['user_id']
        
        # Get the user
        user = User.objects.get(id=user_id)
        return user
    except (TokenError, InvalidToken, User.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware for WebSocket JWT authentication.
    Accepts token via:
    1. Query string: ws://host/path/?token=<jwt>
    2. Subprotocol: Sec-WebSocket-Protocol header
    """
    
    async def __call__(self, scope, receive, send):
        # Try to get token from query string first
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        # If no token in query string, check subprotocols
        if not token:
            subprotocols = scope.get('subprotocols', [])
            for protocol in subprotocols:
                if protocol.startswith('Bearer.'):
                    token = protocol.replace('Bearer.', '')
                    break
        
        # Authenticate user if token is present
        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
