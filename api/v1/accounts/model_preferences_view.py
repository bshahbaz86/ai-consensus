"""
User model preferences views.
"""
from rest_framework.views import APIView
from rest_framework import permissions
from core.responses import success_response, error_response


class ModelPreferencesView(APIView):
    """Manage user's AI model preferences."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user's current model preferences."""
        user = request.user
        preferences = {
            'openai_model': user.openai_model,
            'claude_model': user.claude_model,
            'gemini_model': user.gemini_model,
        }
        return success_response(preferences, message="Model preferences retrieved successfully")

    def put(self, request):
        """Update user's model preferences."""
        user = request.user
        data = request.data

        # Update model preferences
        if 'openai_model' in data:
            user.openai_model = data['openai_model']
        if 'claude_model' in data:
            user.claude_model = data['claude_model']
        if 'gemini_model' in data:
            user.gemini_model = data['gemini_model']

        user.save()

        preferences = {
            'openai_model': user.openai_model,
            'claude_model': user.claude_model,
            'gemini_model': user.gemini_model,
        }

        return success_response(preferences, message="Model preferences updated successfully")
