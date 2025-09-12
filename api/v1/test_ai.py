from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import asyncio
from apps.ai_services.services.factory import AIServiceFactory


@csrf_exempt 
@require_http_methods(["POST"])
def test_ai_services(request):
    """
    Simple test endpoint to verify real AI API integration
    POST /api/v1/test-ai/
    Body: {"message": "test question", "services": ["claude", "openai"]}
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', 'Hello, how are you?')
        services = data.get('services', ['claude', 'openai', 'gemini'])
        
        results = []
        
        # Test Claude if requested and API key available
        if 'claude' in services and settings.CLAUDE_API_KEY:
            try:
                claude_service = AIServiceFactory.create_service(
                    'claude', 
                    settings.CLAUDE_API_KEY,
                    model='claude-3-haiku-20240307'
                )
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    claude_response = loop.run_until_complete(
                        claude_service.generate_response(message)
                    )
                    results.append({
                        'service': 'Claude',
                        'success': claude_response['success'],
                        'content': claude_response['content'],  # Return full content
                        'error': claude_response.get('error')
                    })
                finally:
                    loop.close()
                    
            except Exception as e:
                results.append({
                    'service': 'Claude',
                    'success': False,
                    'content': None,
                    'error': str(e)
                })
        
        # Test OpenAI if requested and API key available  
        if 'openai' in services and settings.OPENAI_API_KEY:
            try:
                openai_service = AIServiceFactory.create_service(
                    'openai',
                    settings.OPENAI_API_KEY, 
                    model='gpt-4'
                )
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    openai_response = loop.run_until_complete(
                        openai_service.generate_response(message)
                    )
                    results.append({
                        'service': 'OpenAI', 
                        'success': openai_response['success'],
                        'content': openai_response['content'],  # Return full content
                        'error': openai_response.get('error')
                    })
                finally:
                    loop.close()
                    
            except Exception as e:
                results.append({
                    'service': 'OpenAI',
                    'success': False, 
                    'content': None,
                    'error': str(e)
                })
        
        # Test Gemini if requested and API key available
        if 'gemini' in services and settings.GEMINI_API_KEY:
            try:
                gemini_service = AIServiceFactory.create_service(
                    'gemini',
                    settings.GEMINI_API_KEY,
                    model='gemini-1.5-flash'
                )
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    gemini_response = loop.run_until_complete(
                        gemini_service.generate_response(message)
                    )
                    results.append({
                        'service': 'Gemini',
                        'success': gemini_response['success'],
                        'content': gemini_response['content'],  # Return full content
                        'error': gemini_response.get('error')
                    })
                finally:
                    loop.close()
                    
            except Exception as e:
                results.append({
                    'service': 'Gemini',
                    'success': False,
                    'content': None,
                    'error': str(e)
                })
        
        return JsonResponse({
            'success': True,
            'message': message,
            'results': results,
            'api_keys_configured': {
                'claude': bool(settings.CLAUDE_API_KEY),
                'openai': bool(settings.OPENAI_API_KEY),
                'gemini': bool(settings.GEMINI_API_KEY)
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)