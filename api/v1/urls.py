"""
ChatAI API v1 URL Configuration

Routes for the REST API endpoints.
"""
from django.urls import path, include
from .consensus_ai import test_ai_services, critique_compare, combine_responses, cross_reflect

app_name = 'api_v1'

urlpatterns = [
    path('accounts/', include('api.v1.accounts.urls')),
    path('conversations/', include('api.v1.conversations.urls', namespace='conversations')),
    path('ai-services/', include('api.v1.ai_services.urls')),
    path('responses/', include('api.v1.responses.urls')),
    path('consensus/', test_ai_services, name='consensus'),
    path('consensus/synthesis/', combine_responses, name='consensus_synthesis'),
    path('consensus/critique/', critique_compare, name='consensus_critique'),
    path('consensus/cross-reflect/', cross_reflect, name='consensus_cross_reflect'),
]