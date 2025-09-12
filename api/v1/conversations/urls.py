"""
API v1 conversations URL configuration.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'conversations'

router = DefaultRouter()
# Will add viewsets here later

urlpatterns = [
    # Conversation endpoints
    path('', views.ConversationListView.as_view(), name='list'),
    path('create/', views.ConversationCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ConversationDetailView.as_view(), name='detail'),
    path('<int:pk>/messages/', views.MessageListView.as_view(), name='messages'),
] + router.urls