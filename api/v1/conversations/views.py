"""
API v1 conversations views.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class ConversationListView(APIView):
    """List user conversations."""
    def get(self, request):
        return Response({'message': 'Conversation list endpoint - not implemented yet'}, 
                       status=status.HTTP_501_NOT_IMPLEMENTED)


class ConversationCreateView(APIView):
    """Create new conversation."""
    def post(self, request):
        return Response({'message': 'Create conversation endpoint - not implemented yet'}, 
                       status=status.HTTP_501_NOT_IMPLEMENTED)


class ConversationDetailView(APIView):
    """Get conversation details."""
    def get(self, request, pk):
        return Response({'message': 'Conversation detail endpoint - not implemented yet'}, 
                       status=status.HTTP_501_NOT_IMPLEMENTED)


class MessageListView(APIView):
    """List messages in conversation."""
    def get(self, request, pk):
        return Response({'message': 'Message list endpoint - not implemented yet'}, 
                       status=status.HTTP_501_NOT_IMPLEMENTED)