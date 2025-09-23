"""
ChatAI API v1 URL Configuration

Routes for the REST API endpoints.
"""
from django.urls import path, include
from .test_ai import test_ai_services, critique_compare
from .demo_view import demo_view

app_name = 'api_v1'

urlpatterns = [
    path('auth/', include('api.v1.accounts.urls')),
    path('conversations/', include('api.v1.conversations.urls', namespace='conversations')),
    path('ai-services/', include('api.v1.ai_services.urls')),
    path('responses/', include('api.v1.responses.urls')),
    path('test-ai/', test_ai_services, name='test_ai'),
    path('critique/compare/', critique_compare, name='critique_compare'),
    path('demo/', demo_view, name='demo'),
]