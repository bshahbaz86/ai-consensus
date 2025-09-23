from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import asyncio
from apps.ai_services.services.factory import AIServiceFactory
from apps.ai_services.services.web_search_coordinator import WebSearchCoordinator
# Removed langchain imports - agent functionality has been removed


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
    Body: {"message": "test question", "services": ["claude", "openai"], "use_web_search": true}
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', 'Hello, how are you?')
        services = data.get('services', ['claude', 'openai', 'gemini'])
        use_web_search = data.get('use_web_search', False)
        chat_history = data.get('chat_history', '')
        
        # Handle web search if enabled
        web_search_context = None
        web_search_sources = []
        
        if use_web_search:
            try:
                search_coordinator = WebSearchCoordinator()
                
                # Run web search async
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    search_result = loop.run_until_complete(
                        search_coordinator.search_for_query(
                            user_query=message,
                            user=None,  # No user for test endpoint
                            context={}
                        )
                    )
                    
                    if search_result['success']:
                        web_search_sources = search_result.get('sources', [])
                        # Format search results for AI context
                        search_summary = []
                        search_summary.append(f"Web Search Results for: {message}")
                        search_summary.append(f"Found {len(search_result['results'])} relevant sources")
                        search_summary.append("\n--- Search Results ---")
                        
                        for i, result in enumerate(search_result['results'][:6], 1):
                            search_summary.append(f"\n{i}. {result.get('title', 'No title')}")
                            search_summary.append(f"   Source: {result.get('source', 'Unknown source')}")
                            if result.get('published_date'):
                                search_summary.append(f"   Published: {result['published_date']}")
                            search_summary.append(f"   Content: {result.get('snippet', 'No content preview')}")
                        
                        search_summary.append("\n--- End Search Results ---")
                        search_summary.append("\nPlease use this current web information to enhance your response.")
                        
                        web_search_context = '\n'.join(search_summary)
                        
                finally:
                    loop.close()
                    
            except Exception as e:
                print(f"Web search failed: {str(e)}")
                # Continue without web search if it fails
        
        results = []
        
        # Test Claude if requested and API key available
        if 'claude' in services and settings.CLAUDE_API_KEY:
            try:
                claude_service = AIServiceFactory.create_service(
                    'claude', 
                    settings.CLAUDE_API_KEY,
                    model='claude-sonnet-4-20250514'
                )
                
                # Prepare context with web search and chat history if available
                context = {}
                enhanced_message = message

                # Add chat history if available
                if chat_history:
                    enhanced_message = f"Previous conversation:\n{chat_history}\n\n{'='*50}\n\nNew user question:\n{message}"

                if web_search_context:
                    if chat_history:
                        enhanced_message = f"Previous conversation:\n{chat_history}\n\n{'='*50}\n\nCurrent web information:\n{web_search_context}\n\n{'='*50}\n\nNew user question:\n{message}\n\nPlease provide a comprehensive response considering the conversation context and using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results."
                    else:
                        enhanced_message = f"Current web information:\n{web_search_context}\n\n{'='*50}\n\nUser question:\n{message}\n\nPlease provide a comprehensive response using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results."
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    claude_response = loop.run_until_complete(
                        claude_service.generate_response(enhanced_message, context)
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
                
                # Prepare context with web search and chat history if available
                context = {}
                enhanced_message = message

                # Add chat history if available
                if chat_history:
                    enhanced_message = f"Previous conversation:\n{chat_history}\n\n{'='*50}\n\nNew user question:\n{message}"

                if web_search_context:
                    if chat_history:
                        enhanced_message = f"Previous conversation:\n{chat_history}\n\n{'='*50}\n\nCurrent web information:\n{web_search_context}\n\n{'='*50}\n\nNew user question:\n{message}\n\nPlease provide a comprehensive response considering the conversation context and using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results."
                    else:
                        enhanced_message = f"Current web information:\n{web_search_context}\n\n{'='*50}\n\nUser question:\n{message}\n\nPlease provide a comprehensive response using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results."
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    openai_response = loop.run_until_complete(
                        openai_service.generate_response(enhanced_message, context)
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
                    model='gemini-1.5-flash'
                )
                
                # Prepare context with web search and chat history if available
                context = {}
                enhanced_message = message

                # Add chat history if available
                if chat_history:
                    enhanced_message = f"Previous conversation:\n{chat_history}\n\n{'='*50}\n\nNew user question:\n{message}"

                if web_search_context:
                    if chat_history:
                        enhanced_message = f"Previous conversation:\n{chat_history}\n\n{'='*50}\n\nCurrent web information:\n{web_search_context}\n\n{'='*50}\n\nNew user question:\n{message}\n\nPlease provide a comprehensive response considering the conversation context and using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results."
                    else:
                        enhanced_message = f"Current web information:\n{web_search_context}\n\n{'='*50}\n\nUser question:\n{message}\n\nPlease provide a comprehensive response using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results."
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    gemini_response = loop.run_until_complete(
                        gemini_service.generate_response(enhanced_message, context)
                    )
                    
                    # Generate synopsis using Gemini itself
                    synopsis = "No synopsis available"
                    if gemini_response['success'] and gemini_response['content']:
                        synopsis = loop.run_until_complete(
                            generate_synopsis_with_same_ai(
                                gemini_response['content'],
                                'gemini',
                                settings.GEMINI_API_KEY,
                                'gemini-1.5-flash'
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
            'web_search_enabled': use_web_search,
            'web_search_sources': web_search_sources,
            'api_keys_configured': {
                'claude': bool(settings.CLAUDE_API_KEY),
                'openai': bool(settings.OPENAI_API_KEY),
                'gemini': bool(settings.GEMINI_API_KEY),
                'google_search': bool(getattr(settings, 'GOOGLE_CSE_API_KEY', None))
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def critique_compare(request):
    """
    Compare two LLM responses using AI critique framework.
    """
    try:
        data = json.loads(request.body)
        user_query = data.get('user_query', '')
        llm1_name = data.get('llm1_name', '')
        llm1_response = data.get('llm1_response', '')
        llm2_name = data.get('llm2_name', '')
        llm2_response = data.get('llm2_response', '')
        chat_history = data.get('chat_history', '')

        if not all([user_query, llm1_name, llm1_response, llm2_name, llm2_response]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        # Create the critique prompt using the framework you provided
        critique_prompt = f"""You are tasked with conducting a thorough, objective analysis comparing two LLM responses to the same user query. Your goal is to evaluate both responses fairly across multiple dimensions and provide actionable insights for improvement.

Original User Query along with chat history: {user_query}

Chat History: {chat_history}

{llm1_name}'s Response: {llm1_response}

{llm2_name}'s Response: {llm2_response}

Please provide your analysis in the following structured format:

## Executive Summary
A brief 2-3 sentence overview of which response better serves the user's needs and why.

## Overall Assessment
Rate each response (1-10) with brief justification:
{llm1_name}: [Score] - [Reasoning]
{llm2_name}: [Score] - [Reasoning]

## Detailed Comparison

### Content Analysis
Compare accuracy, completeness, and relevance. Note any factual discrepancies or gaps. Evaluate depth vs. breadth trade-offs.

### Style & Communication
Assess clarity, tone, and accessibility. Compare use of examples and explanations. Evaluate formatting and organization.

### Technical Execution
Review adherence to specific requirements. Assess any code, formatting, or structural elements. Note handling of edge cases or constraints.

### User-Centric Evaluation
Which response better addresses the user's underlying need? Which provides more actionable value? Which anticipates logical follow-up questions?

## Strengths & Weaknesses Matrix

### {llm1_name}'s Response
**Strengths:** [List 2-3 key advantages]
**Weaknesses:** [List 2-3 areas for improvement]

### {llm2_name}'s Response
**Strengths:** [List 2-3 key advantages]
**Weaknesses:** [List 2-3 areas for improvement]

## Synthesis & Recommendations

### For {llm1_name}'s Future Responses:
Specific improvements based on {llm2_name}'s strengths. Approaches to maintain current advantages. Suggestions for better handling similar queries.

### Ideal Response Characteristics:
What would a superior response combine from both? What novel approaches could surpass both responses?

Focus on helping improve future responses while maintaining objectivity in your evaluation."""

        # Use Claude for the critique (as it's typically most analytical)
        if settings.CLAUDE_API_KEY:
            claude_service = AIServiceFactory.create_service(
                'claude',
                settings.CLAUDE_API_KEY,
                model='claude-sonnet-4-20250514'
            )

            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                critique_response = loop.run_until_complete(
                    claude_service.generate_response(critique_prompt)
                )
            finally:
                loop.close()

            if critique_response['success']:
                return JsonResponse({
                    'success': True,
                    'critique': critique_response['content']
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': f"Critique generation failed: {critique_response.get('error', 'Unknown error')}"
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Claude API key not configured for critique functionality'
            }, status=500)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)