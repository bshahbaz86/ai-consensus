"""
API v1 accounts views.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.contrib.sessions.models import Session
from core.responses import success_response, error_response
from apps.accounts.serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserProfileSerializer,
    APIKeySerializer
)
from apps.accounts.models import APIKey, UserSession


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