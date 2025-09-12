from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import asyncio
from apps.ai_services.services.factory import AIServiceFactory
from core.langchain.service import ConversationAgentExecutor
from core.langchain.tools import tool_registry


async def generate_synopsis_with_same_ai(content: str, ai_service_name: str, api_key: str, model: str) -> str:
    """
    Use the same AI service that generated the response to create an intelligent synopsis.
    This ensures each AI uses its own intelligence to summarize its own response.
    """
    try:
        # Create AI service instance
        ai_service = AIServiceFactory.create_service(ai_service_name.lower(), api_key, model=model)
        
        # Create synopsis prompt for the AI
        synopsis_prompt = f"""Please provide a concise, intelligent 35-45 word synopsis of your previous response that captures the key insights and main points:

{content[:800]}

Guidelines:
- Focus on the most important insights and conclusions  
- Use clear, professional language
- Avoid unnecessary introductory phrases
- Make every word count
- Aim for exactly 35-45 words"""

        # Get synopsis from the same AI service
        result = await ai_service.generate_response(synopsis_prompt)
        
        if result.get('success'):
            synopsis = result.get('content', 'Unable to generate synopsis')
            # Clean up the synopsis - remove any extraneous formatting
            words = synopsis.strip().split()
            if len(words) > 50:  # Ensure it's not too long
                synopsis = ' '.join(words[:45]) + '...'
            return synopsis
        else:
            return f"Synopsis generation failed: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        print(f"Error generating synopsis with same AI: {str(e)}")
        return "Synopsis generation failed"


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
                    model='claude-sonnet-4-20250514'
                )
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    claude_response = loop.run_until_complete(
                        claude_service.generate_response(message)
                    )
                    
                    # Generate synopsis using Claude itself
                    synopsis = "No synopsis available"
                    if claude_response['success'] and claude_response['content']:
                        synopsis = loop.run_until_complete(
                            generate_synopsis_with_same_ai(
                                claude_response['content'],
                                'claude',
                                settings.CLAUDE_API_KEY,
                                'claude-sonnet-4-20250514'
                            )
                        )
                    
                    results.append({
                        'service': 'Claude',
                        'success': claude_response['success'],
                        'content': claude_response['content'],  # Return full content
                        'synopsis': synopsis,
                        'error': claude_response.get('error')
                    })
                finally:
                    loop.close()
                    
            except Exception as e:
                results.append({
                    'service': 'Claude',
                    'success': False,
                    'content': None,
                    'synopsis': 'Synopsis generation failed',
                    'error': str(e)
                })
        
        # Test OpenAI if requested and API key available  
        if 'openai' in services and settings.OPENAI_API_KEY:
            try:
                openai_service = AIServiceFactory.create_service(
                    'openai',
                    settings.OPENAI_API_KEY, 
                    model='gpt-4o'
                )
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    openai_response = loop.run_until_complete(
                        openai_service.generate_response(message)
                    )
                    
                    # Generate synopsis using OpenAI itself
                    synopsis = "No synopsis available"
                    if openai_response['success'] and openai_response['content']:
                        synopsis = loop.run_until_complete(
                            generate_synopsis_with_same_ai(
                                openai_response['content'],
                                'openai',
                                settings.OPENAI_API_KEY,
                                'gpt-4o'
                            )
                        )
                    
                    results.append({
                        'service': 'OpenAI', 
                        'success': openai_response['success'],
                        'content': openai_response['content'],  # Return full content
                        'synopsis': synopsis,
                        'error': openai_response.get('error')
                    })
                finally:
                    loop.close()
                    
            except Exception as e:
                results.append({
                    'service': 'OpenAI',
                    'success': False, 
                    'content': None,
                    'synopsis': 'Synopsis generation failed',
                    'error': str(e)
                })
        
        # Test Gemini if requested and API key available
        if 'gemini' in services and settings.GEMINI_API_KEY:
            try:
                gemini_service = AIServiceFactory.create_service(
                    'gemini',
                    settings.GEMINI_API_KEY,
                    model='gemini-1.5-pro'
                )
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    gemini_response = loop.run_until_complete(
                        gemini_service.generate_response(message)
                    )
                    
                    # Generate synopsis using Gemini itself
                    synopsis = "No synopsis available"
                    if gemini_response['success'] and gemini_response['content']:
                        synopsis = loop.run_until_complete(
                            generate_synopsis_with_same_ai(
                                gemini_response['content'],
                                'gemini',
                                settings.GEMINI_API_KEY,
                                'gemini-1.5-pro'
                            )
                        )
                    
                    results.append({
                        'service': 'Gemini',
                        'success': gemini_response['success'],
                        'content': gemini_response['content'],  # Return full content
                        'synopsis': synopsis,
                        'error': gemini_response.get('error')
                    })
                finally:
                    loop.close()
                    
            except Exception as e:
                results.append({
                    'service': 'Gemini',
                    'success': False,
                    'content': None,
                    'synopsis': 'Synopsis generation failed',
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