"""
API v1 conversations URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'conversations'

# Main router for conversations
router = DefaultRouter()
router.register(r'', views.ConversationViewSet, basename='conversation')

urlpatterns = [
    path('', include(router.urls)),
    # Manual route for messages within conversations
    path('<uuid:conversation_pk>/messages/', views.MessageViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='conversation-messages'),
]