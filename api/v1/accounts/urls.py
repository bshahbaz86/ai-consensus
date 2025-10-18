"""
API v1 accounts URL configuration.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views
from .model_preferences_view import ModelPreferencesView

app_name = 'accounts'

router = DefaultRouter()
# Will add viewsets here later

urlpatterns = [
    # Authentication endpoints
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),

    # Google OAuth endpoints
    path('auth/google/init/', views.google_oauth_init, name='google-oauth-init'),
    path('auth/google/callback/', views.google_oauth_callback, name='google-oauth-callback'),

    # Email Passcode authentication
    path('auth/passcode/send/', views.passcode_send, name='passcode-send'),
    path('auth/passcode/verify/', views.passcode_verify, name='passcode-verify'),

    # Password authentication
    path('auth/password/login/', views.password_login, name='password-login'),
    path('auth/password/set/', views.set_password, name='set-password'),

    # API key management
    path('api-keys/', views.APIKeyManagementView.as_view(), name='api_keys'),

    # Model preferences
    path('model-preferences/', ModelPreferencesView.as_view(), name='model_preferences'),
] + router.urls