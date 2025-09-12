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
    
    # Structured summary endpoints
    path('summary/structured/', views.StructuredSummaryView.as_view(), name='structured_summary'),
    
    # LangChain agent endpoints
    path('agent/execute/', views.AgentExecutorView.as_view(), name='agent_execute'),
    path('agent/tools/', views.ToolsListView.as_view(), name='tools_list'),
    
    # Conversation-based agent endpoints
    path('agent/conversation/', views.ConversationAgentView.as_view(), name='conversation_agent'),
    path('agent/conversation/<int:conversation_id>/', views.ConversationAgentView.as_view(), name='conversation_agent_detail'),
] + router.urls