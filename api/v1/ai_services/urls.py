"""
API v1 AI services URL configuration.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'ai_services'

router = DefaultRouter()
# Will add viewsets here later

urlpatterns = [
    # AI service endpoints
    path('', views.AIServiceListView.as_view(), name='list'),
    path('query/', views.MultiAIQueryView.as_view(), name='multi_query'),
    path('configure/', views.ConfigureKeysView.as_view(), name='configure'),
    
    # Structured summary endpoint
    path('summary/structured/', views.StructuredSummaryView.as_view(), name='structured_summary'),
] + router.urls