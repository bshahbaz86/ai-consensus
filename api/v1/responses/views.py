"""
API v1 responses views.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class ResponseListView(APIView):
    """List responses for a query."""
    def get(self, request):
        return Response({'message': 'Response list endpoint - not implemented yet'}, 
                       status=status.HTTP_501_NOT_IMPLEMENTED)


class ResponseDetailView(APIView):
    """Get response details."""
    def get(self, request, pk):
        return Response({'message': 'Response detail endpoint - not implemented yet'}, 
                       status=status.HTTP_501_NOT_IMPLEMENTED)


class SelectResponseView(APIView):
    """Select a response to continue conversation."""
    def post(self, request, pk):
        return Response({'message': 'Select response endpoint - not implemented yet'}, 
                       status=status.HTTP_501_NOT_IMPLEMENTED)