"""
API v1 accounts views.
"""
import json
from pathlib import Path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, logout
from django.contrib.sessions.models import Session
from django.conf import settings
from django.utils import timezone
from core.responses import success_response, error_response
from apps.accounts.serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    APIKeySerializer,
    PasscodeSendSerializer,
    PasscodeVerifySerializer,
    SetPasswordSerializer
)
from apps.accounts.models import APIKey, UserSession, User, EmailPasscode
import requests
from django.core.mail import send_mail


class RegisterView(APIView):
    """User registration view."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Create authentication token
            token, created = Token.objects.get_or_create(user=user)
            
            # Create user session
            request.session.create()
            UserSession.objects.create(
                user=user,
                session_key=request.session.session_key,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Log the user in
            login(request, user)
            
            return success_response({
                'user': UserProfileSerializer(user).data,
                'token': token.key
            }, message="Registration successful", status_code=status.HTTP_201_CREATED)
        
        return error_response(
            message="Registration failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class LoginView(APIView):
    """User login view."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Get or create authentication token
            token, created = Token.objects.get_or_create(user=user)
            
            # Create user session
            if not request.session.session_key:
                request.session.create()
                
            UserSession.objects.update_or_create(
                user=user,
                session_key=request.session.session_key,
                defaults={
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'is_active': True
                }
            )
            
            # Log the user in
            login(request, user)
            
            return success_response({
                'user': UserProfileSerializer(user).data,
                'token': token.key
            }, message="Login successful")
        
        return error_response(
            message="Login failed",
            errors=serializer.errors,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class LogoutView(APIView):
    """User logout view."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Deactivate user session
            if request.session.session_key:
                UserSession.objects.filter(
                    user=request.user,
                    session_key=request.session.session_key
                ).update(is_active=False)
            
            # Delete authentication token
            Token.objects.filter(user=request.user).delete()
            
            # Log the user out
            logout(request)
            
            return success_response(message="Logout successful")
        
        except Exception as e:
            return error_response(
                message="Logout failed",
                errors={'detail': str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProfileView(APIView):
    """User profile view."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return success_response(serializer.data)
    
    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return success_response(serializer.data, message="Profile updated successfully")
        
        return error_response(
            message="Profile update failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class APIKeyManagementView(APIView):
    """API key management for AI services."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """List user's API keys."""
        api_keys = APIKey.objects.filter(user=request.user)
        serializer = APIKeySerializer(api_keys, many=True)
        return success_response(serializer.data)
    
    def post(self, request):
        """Add or update an API key."""
        serializer = APIKeySerializer(data=request.data)
        if serializer.is_valid():
            # Check if API key for this service already exists
            existing_key = APIKey.objects.filter(
                user=request.user,
                service_name=serializer.validated_data['service_name']
            ).first()
            
            if existing_key:
                # Update existing key
                serializer = APIKeySerializer(existing_key, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return success_response(serializer.data, message="API key updated successfully")
            else:
                # Create new key
                api_key = serializer.save(user=request.user)
                return success_response(
                    APIKeySerializer(api_key).data, 
                    message="API key added successfully",
                    status_code=status.HTTP_201_CREATED
                )
        
        return error_response(
            message="API key operation failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def delete(self, request):
        """Delete an API key."""
        service_name = request.data.get('service_name')
        if not service_name:
            return error_response(
                message="Service name is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            api_key = APIKey.objects.get(user=request.user, service_name=service_name)
            api_key.delete()
            return success_response(message="API key deleted successfully")
        except APIKey.DoesNotExist:
            return error_response(
                message="API key not found",
                status_code=status.HTTP_404_NOT_FOUND
            )


# Google OAuth Views

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def google_oauth_init(request):
    """
    Initiate Google OAuth flow.
    Returns the authorization URL for the frontend to redirect to.
    """
    # Build authorization URL
    authorization_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']}&"
        f"redirect_uri={settings.FRONTEND_URL}/auth/google/callback&"
        f"response_type=code&"
        f"scope=openid%20profile%20email&"
        f"access_type=online"
    )

    return success_response({
        'authorization_url': authorization_url
    })


@api_view(['POST'])
@authentication_classes([])  # Disable authentication to bypass CSRF for OAuth callback
@permission_classes([permissions.AllowAny])
def google_oauth_callback(request):
    """
    Handle Google OAuth callback.
    Exchange authorization code for tokens and create/login user.

    Expected payload: { "code": "auth_code_from_google" }
    """
    code = request.data.get('code')
    if not code:
        return error_response(
            message="Authorization code required",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Exchange code for tokens
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id'],
            'client_secret': settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['secret'],
            'redirect_uri': f"{settings.FRONTEND_URL}/auth/google/callback",
            'grant_type': 'authorization_code',
        }

        token_response = requests.post(token_url, data=token_data)

        if token_response.status_code != 200:
            return error_response(
                message="Failed to exchange authorization code",
                errors={'detail': token_response.text},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        tokens = token_response.json()
        access_token = tokens.get('access_token')

        # Get user info from Google
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        if user_info_response.status_code != 200:
            return error_response(
                message="Failed to fetch user information",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        user_info = user_info_response.json()

        # Get or create user
        google_id = user_info.get('id')
        email = user_info.get('email')

        user, created = User.objects.get_or_create(
            google_id=google_id,
            defaults={
                'email': email,
                'username': email.split('@')[0],
                'display_name': user_info.get('name', ''),
                'avatar': user_info.get('picture', ''),
                'google_email': email,
                'google_profile_picture': user_info.get('picture', ''),
                'auth_method': 'google_oauth',
                'is_active': True,
            }
        )

        # Update if existing user
        if not created:
            user.google_email = email
            user.google_profile_picture = user_info.get('picture', '')
            user.auth_method = 'google_oauth'
            user.last_auth_at = timezone.now()
        else:
            user.last_auth_at = timezone.now()

        # Encrypt and save tokens
        user.encrypt_google_tokens(
            access_token,
            tokens.get('refresh_token', '')
        )
        user.save()

        # Create session
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Create DRF token
        token, _ = Token.objects.get_or_create(user=user)

        # Create user session
        if not request.session.session_key:
            request.session.create()

        UserSession.objects.update_or_create(
            user=user,
            session_key=request.session.session_key,
            defaults={
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'is_active': True
            }
        )

        # Serialize user data
        return success_response({
            'user': UserProfileSerializer(user).data,
            'token': token.key,
            'is_new_user': created,
            'has_permanent_password': user.has_permanent_password,
        }, message="Google authentication successful")

    except Exception as e:
        return error_response(
            message="Google authentication failed",
            errors={'detail': str(e)},
            status_code=status.HTTP_400_BAD_REQUEST
        )


# Email Passcode Authentication Views

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def passcode_send(request):
    """
    Send a temporary 6-digit passcode to the provided email.
    The passcode expires in 15 minutes.
    """
    serializer = PasscodeSendSerializer(data=request.data)
    if not serializer.is_valid():
        return error_response(
            message="Invalid email",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    email = serializer.validated_data['email']

    try:
        # Generate passcode
        passcode_obj = EmailPasscode.generate_passcode(email)

        # Send email
        subject = 'Your AI Consensus Login Code'
        message = f'''
Your temporary login code is: {passcode_obj.passcode}

This code will expire in 15 minutes.

If you didn't request this code, you can safely ignore this email.
        '''

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

        return success_response({
            'email': email,
            'expires_in_minutes': 15
        }, message="Passcode sent successfully")

    except Exception as e:
        return error_response(
            message="Failed to send passcode",
            errors={'detail': str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def passcode_verify(request):
    """
    Verify a passcode and log in the user.
    Creates a new user if the email doesn't exist.
    """
    serializer = PasscodeVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return error_response(
            message="Invalid passcode",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    user = serializer.validated_data['user']

    try:
        # Create or get authentication token
        token, created = Token.objects.get_or_create(user=user)

        # Create user session
        if not request.session.session_key:
            request.session.create()

        UserSession.objects.update_or_create(
            user=user,
            session_key=request.session.session_key,
            defaults={
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'is_active': True
            }
        )

        # Log the user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        return success_response({
            'user': UserProfileSerializer(user).data,
            'token': token.key,
            'is_new_user': user.date_joined >= timezone.now() - timezone.timedelta(seconds=10),
            'has_permanent_password': user.has_permanent_password,
        }, message="Login successful")

    except Exception as e:
        return error_response(
            message="Login failed",
            errors={'detail': str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Password Authentication Views

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_password(request):
    """
    Set a permanent password for the authenticated user.
    This allows Google OAuth or passcode users to add password authentication.
    """
    serializer = SetPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return error_response(
            message="Invalid password",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = request.user
        user.set_password(serializer.validated_data['password'])
        user.has_permanent_password = True
        user.save(update_fields=['password', 'has_permanent_password'])

        return success_response({
            'has_permanent_password': True
        }, message="Password set successfully")

    except Exception as e:
        return error_response(
            message="Failed to set password",
            errors={'detail': str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def password_login(request):
    """
    Login with email and password.
    """
    serializer = UserLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return error_response(
            message="Login failed",
            errors=serializer.errors,
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    user = serializer.validated_data['user']

    # Check if user has a password set
    if not user.has_permanent_password:
        return error_response(
            message="Password login not available",
            errors={'detail': 'This account does not have a password set. Please use Google OAuth or email passcode login.'},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Get or create authentication token
        token, created = Token.objects.get_or_create(user=user)

        # Create user session
        if not request.session.session_key:
            request.session.create()

        UserSession.objects.update_or_create(
            user=user,
            session_key=request.session.session_key,
            defaults={
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'is_active': True
            }
        )

        # Log the user in
        login(request, user)

        # Update auth method
        user.auth_method = 'permanent_password'
        user.last_auth_at = timezone.now()
        user.save(update_fields=['auth_method', 'last_auth_at'])

        return success_response({
            'user': UserProfileSerializer(user).data,
            'token': token.key,
        }, message="Login successful")

    except Exception as e:
        return error_response(
            message="Login failed",
            errors={'detail': str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )