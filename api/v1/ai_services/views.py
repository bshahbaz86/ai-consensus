"""
API v1 AI services views.
"""
import asyncio
from typing import Dict, Any, List
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

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


class StructuredSummaryView(APIView):
    """Generate structured summaries using Pydantic models and function calling."""
    permission_classes = [IsAuthenticated]
    
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