"""
API v1 responses URL configuration.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'responses'

router = DefaultRouter()
# Will add viewsets here later

urlpatterns = [
    # Response endpoints
    path('', views.ResponseListView.as_view(), name='list'),
    path('<int:pk>/', views.ResponseDetailView.as_view(), name='detail'),
    path('<int:pk>/select/', views.SelectResponseView.as_view(), name='select'),
] + router.urls