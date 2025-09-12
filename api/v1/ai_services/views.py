"""
API v1 AI services views.
"""
import asyncio
from typing import Dict, Any, List
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from core.langchain.service import LangChainService, ConversationAgentExecutor
from core.langchain.tools import tool_registry, get_default_tools, get_all_tools
from core.ai_models import StructuredSummaryResult
from apps.responses.services.structured_summary import StructuredSummaryService


class AIServiceListView(APIView):
    """List available AI services."""
    def get(self, request):
        return Response({'message': 'AI service list endpoint - not implemented yet'}, 
                       status=status.HTTP_501_NOT_IMPLEMENTED)


class MultiAIQueryView(APIView):
    """Submit query to multiple AI services."""
    def post(self, request):
        return Response({'message': 'Multi AI query endpoint - not implemented yet'}, 
                       status=status.HTTP_501_NOT_IMPLEMENTED)


class ConfigureKeysView(APIView):
    """Configure API keys for AI services."""
    def post(self, request):
        return Response({'message': 'Configure keys endpoint - not implemented yet'}, 
                       status=status.HTTP_501_NOT_IMPLEMENTED)


@method_decorator(csrf_exempt, name='dispatch')
class StructuredSummaryView(APIView):
    """Generate structured summaries using Pydantic models and function calling."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            data = request.data
            content = data.get('content', '')
            ai_service = data.get('ai_service', 'openai')
            use_enhanced = data.get('use_enhanced', True)
            
            if not content:
                return Response(
                    {'error': 'Content is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create service and generate summary
            summary_service = StructuredSummaryService()
            
            # Run async method
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    summary_service.generate_structured_summary(
                        content=content,
                        ai_service_name=ai_service,
                        use_enhanced=use_enhanced
                    )
                )
            finally:
                loop.close()
            
            return Response({
                'success': result.success,
                'enhanced_summary': result.enhanced_summary.model_dump(),
                'legacy_summary': result.legacy_summary,
                'metadata': result.metadata.model_dump(),
                'error_message': result.error_message
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error generating structured summary: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class AgentExecutorView(APIView):
    """Execute queries using LangChain agents with tool access."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            data = request.data
            query = data.get('query', '')
            tools = data.get('tools', ['web_search', 'calculator', 'datetime'])
            ai_service = data.get('ai_service', 'openai')
            conversation_id = data.get('conversation_id')
            
            if not query:
                return Response(
                    {'error': 'Query is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get requested tools
            available_tools = tool_registry.get_tools(tools)
            
            # Create agent executor
            agent_executor = ConversationAgentExecutor(conversation_id=conversation_id)
            agent_executor.setup_service(tools=available_tools, ai_service_name=ai_service)
            
            # Process query
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    agent_executor.process_query(query)
                )
            finally:
                loop.close()
            
            return Response({
                'success': result.get('success', False),
                'response': result.get('response', ''),
                'metadata': result.get('metadata', {}),
                'intermediate_steps': result.get('intermediate_steps', []),
                'panels': result.get('panels', []),
                'error': result.get('error')
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error executing agent query: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class ToolsListView(APIView):
    """List available tools for LangChain agents."""
    
    def get(self, request):
        try:
            tool_type = request.GET.get('type', 'all')
            
            if tool_type == 'default':
                tools = get_default_tools()
            else:
                tools = get_all_tools()
            
            # Get tool information
            tool_info = []
            for tool in tools:
                tool_info.append({
                    'name': tool.name,
                    'description': tool.description,
                    'args_schema': tool.args_schema.schema() if hasattr(tool, 'args_schema') and tool.args_schema else None
                })
            
            return Response({
                'tools': tool_info,
                'count': len(tool_info),
                'type': tool_type
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error listing tools: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class ConversationAgentView(APIView):
    """Manage conversation-based agent interactions."""
    
    def post(self, request, conversation_id=None):
        """Process a query in the context of a specific conversation."""
        try:
            data = request.data
            query = data.get('query', '')
            tools = data.get('tools', ['web_search', 'calculator', 'content_summarizer'])
            ai_service = data.get('ai_service', 'openai')
            
            if not query:
                return Response(
                    {'error': 'Query is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get requested tools
            available_tools = tool_registry.get_tools(tools)
            
            # Create conversation agent
            agent = ConversationAgentExecutor(conversation_id=conversation_id)
            agent.setup_service(tools=available_tools, ai_service_name=ai_service)
            
            # Process query
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    agent.process_query(query)
                )
            finally:
                loop.close()
            
            return Response({
                'conversation_id': conversation_id,
                'success': result.get('success', False),
                'response': result.get('response', ''),
                'metadata': result.get('metadata', {}),
                'panels': result.get('panels', []),
                'error': result.get('error')
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error in conversation agent: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, conversation_id=None):
        """Clear conversation history for agent."""
        try:
            agent = ConversationAgentExecutor(conversation_id=conversation_id)
            agent.clear_history()
            
            return Response({
                'message': f'Conversation {conversation_id} history cleared',
                'conversation_id': conversation_id
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error clearing conversation history: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )