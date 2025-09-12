"""
API v1 accounts URL configuration.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'accounts'

router = DefaultRouter()
# Will add viewsets here later

urlpatterns = [
    # Authentication endpoints
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    # API key management
    path('api-keys/', views.APIKeyManagementView.as_view(), name='api_keys'),
] + router.urls