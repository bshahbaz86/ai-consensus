"""
Unified response structures for ChatAI API.
"""
from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    """
    Standard success response format.
    """
    response_data = {
        'success': True,
        'message': message,
    }
    if data is not None:
        response_data['data'] = data
    
    return Response(response_data, status=status_code)


def error_response(message="An error occurred", errors=None, error_code=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Standard error response format.
    """
    response_data = {
        'success': False,
        'message': message,
    }
    
    if errors:
        response_data['errors'] = errors
    
    if error_code:
        response_data['error_code'] = error_code
    
    return Response(response_data, status=status_code)