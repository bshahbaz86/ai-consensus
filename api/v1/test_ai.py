from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
import asyncio
from apps.ai_services.services.factory import AIServiceFactory
from apps.ai_services.services.web_search_coordinator import WebSearchCoordinator
from apps.ai_services.utils.token_extractor import extract_tokens, calculate_total_tokens
from apps.ai_services.models import AIService, AIQuery
from apps.responses.models import AIResponse
from apps.conversations.models import Conversation
from django.utils import timezone
from asgiref.sync import sync_to_async


def check_test_endpoints_enabled():
    """
    Check if test endpoints are enabled.
    Raises JsonResponse with 403 status if disabled.
    """
    if not getattr(settings, 'ENABLE_TEST_AI_ENDPOINTS', False):
        return JsonResponse({
            'success': False,
            'error': 'Test AI endpoints are disabled. Enable ENABLE_TEST_AI_ENDPOINTS in settings to use these diagnostic endpoints.'
        }, status=403)
async def generate_synopsis_with_same_ai(content: str, ai_service_name: str, api_key: str, model: str) -> dict:
    """
    Use the same AI service that generated the response to create an intelligent synopsis.
    Returns dict with 'synopsis' text and 'metadata' for token tracking.
    """
    try:
        ai_service = AIServiceFactory.create_service(ai_service_name.lower(), api_key, model=model)

        synopsis_prompt = f"""Please provide a concise, intelligent 35-45 word synopsis of your previous response that captures the key insights and main points:

{content[:800]}

Guidelines:
- Focus on the most important insights and conclusions
- Use clear, professional language
- Avoid unnecessary introductory phrases
- Make every word count
- Aim for exactly 35-45 words"""

        result = await ai_service.generate_response(synopsis_prompt)

        if result.get('success'):
            synopsis = result.get('content', 'Unable to generate synopsis')
            words = synopsis.strip().split()
            if len(words) > 50:
                synopsis = ' '.join(words[:45]) + '...'
            return {'synopsis': synopsis, 'metadata': result.get('metadata', {}), 'success': True}
        else:
            return {'synopsis': f"Synopsis generation failed: {result.get('error', 'Unknown error')}", 'metadata': {}, 'success': False}

    except Exception as e:
        print(f"Error generating synopsis with same AI: {str(e)}")
        return {'synopsis': "Synopsis generation failed", 'metadata': {}, 'success': False}


async def process_claude(message: str, chat_history: str, web_search_context: str, search_result: dict, use_web_search: bool, ai_query):
    """Process Claude request with main response and synopsis generation."""
    try:
        claude_service = AIServiceFactory.create_service(
            'claude',
            settings.CLAUDE_API_KEY,
            model='claude-sonnet-4-20250514'
        )

        # Prepare context
        context = {}
        enhanced_message = message

        if chat_history:
            enhanced_message = f"Previous conversation:\n{chat_history}\n\n{'='*50}\n\nNew user question:\n{message}"

        if web_search_context and use_web_search and search_result and search_result.get('success', False):
            context['web_search'] = {
                'enabled': True,
                'results': search_result['results']
            }
            if chat_history:
                enhanced_message = f"Previous conversation:\n{chat_history}\n\n{'='*50}\n\nCurrent web information:\n{web_search_context}\n\n{'='*50}\n\nNew user question:\n{message}\n\nPlease provide a comprehensive response considering the conversation context and using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results."
            else:
                enhanced_message = f"Current web information:\n{web_search_context}\n\n{'='*50}\n\nUser question:\n{message}\n\nPlease provide a comprehensive response using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results."

        # Get main response
        claude_response = await claude_service.generate_response(enhanced_message, context)

        # Generate synopsis
        synopsis = "No synopsis available"
        synopsis_result = None
        if claude_response['success'] and claude_response['content']:
            synopsis_result = await generate_synopsis_with_same_ai(
                claude_response['content'],
                'claude',
                settings.CLAUDE_API_KEY,
                'claude-sonnet-4-20250514'
            )
            synopsis = synopsis_result.get('synopsis', 'No synopsis available')

        # Extract tokens
        input_tokens, output_tokens = extract_tokens(
            claude_response.get('metadata', {}),
            'claude'
        )
        total_tokens = calculate_total_tokens(input_tokens, output_tokens)

        # Create AIResponse records
        if ai_query:
            try:
                claude_service_obj = await sync_to_async(AIService.objects.get)(name='claude')

                # Main response record
                await sync_to_async(AIResponse.objects.create)(
                    query=ai_query,
                    service=claude_service_obj,
                    content=claude_response['content'],
                    raw_response=claude_response.get('metadata', {}),
                    summary=synopsis,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    tokens_used=total_tokens
                )

                # Synopsis generation record
                if synopsis_result and synopsis_result.get('success'):
                    synopsis_input_tokens, synopsis_output_tokens = extract_tokens(
                        synopsis_result.get('metadata', {}),
                        'claude'
                    )
                    synopsis_total_tokens = calculate_total_tokens(synopsis_input_tokens, synopsis_output_tokens)
                    await sync_to_async(AIResponse.objects.create)(
                        query=ai_query,
                        service=claude_service_obj,
                        content=synopsis,
                        raw_response=synopsis_result.get('metadata', {}),
                        summary='Synopsis generation call',
                        input_tokens=synopsis_input_tokens,
                        output_tokens=synopsis_output_tokens,
                        tokens_used=synopsis_total_tokens
                    )
            except Exception as e:
                print(f"Failed to create AIResponse for Claude: {e}")

        return {
            'service': 'Claude',
            'success': claude_response['success'],
            'content': claude_response['content'],
            'synopsis': synopsis,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'tokens_used': total_tokens,
            'error': claude_response.get('error')
        }

    except Exception as e:
        return {
            'service': 'Claude',
            'success': False,
            'content': None,
            'synopsis': 'Synopsis generation failed',
            'error': str(e)
        }


async def process_openai(message: str, chat_history: str, web_search_context: str, search_result: dict, use_web_search: bool, ai_query):
    """Process OpenAI request with main response and synopsis generation."""
    try:
        openai_service = AIServiceFactory.create_service(
            'openai',
            settings.OPENAI_API_KEY,
            model='gpt-4o'
        )

        # Prepare context
        context = {}
        enhanced_message = message

        if chat_history:
            enhanced_message = f"Previous conversation:\n{chat_history}\n\n{'='*50}\n\nNew user question:\n{message}"

        if web_search_context and use_web_search and search_result and search_result.get('success', False):
            context['web_search'] = {
                'enabled': True,
                'results': search_result['results']
            }
            if chat_history:
                enhanced_message = f"Previous conversation:\n{chat_history}\n\n{'='*50}\n\nCurrent web information:\n{web_search_context}\n\n{'='*50}\n\nNew user question:\n{message}\n\nPlease provide a comprehensive response considering the conversation context and using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results."
            else:
                enhanced_message = f"Current web information:\n{web_search_context}\n\n{'='*50}\n\nUser question:\n{message}\n\nPlease provide a comprehensive response using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results."

        # Get main response
        openai_response = await openai_service.generate_response(enhanced_message, context)

        # Generate synopsis
        synopsis = "No synopsis available"
        synopsis_result = None
        if openai_response['success'] and openai_response['content']:
            synopsis_result = await generate_synopsis_with_same_ai(
                openai_response['content'],
                'openai',
                settings.OPENAI_API_KEY,
                'gpt-4o'
            )
            synopsis = synopsis_result.get('synopsis', 'No synopsis available')

        # Extract tokens
        input_tokens, output_tokens = extract_tokens(
            openai_response.get('metadata', {}),
            'openai'
        )
        total_tokens = calculate_total_tokens(input_tokens, output_tokens)

        # Create AIResponse records
        if ai_query:
            try:
                openai_service_obj = await sync_to_async(AIService.objects.get)(name='openai')

                # Main response record
                await sync_to_async(AIResponse.objects.create)(
                    query=ai_query,
                    service=openai_service_obj,
                    content=openai_response['content'],
                    raw_response=openai_response.get('metadata', {}),
                    summary=synopsis,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    tokens_used=total_tokens
                )

                # Synopsis generation record
                if synopsis_result and synopsis_result.get('success'):
                    synopsis_input_tokens, synopsis_output_tokens = extract_tokens(
                        synopsis_result.get('metadata', {}),
                        'openai'
                    )
                    synopsis_total_tokens = calculate_total_tokens(synopsis_input_tokens, synopsis_output_tokens)
                    await sync_to_async(AIResponse.objects.create)(
                        query=ai_query,
                        service=openai_service_obj,
                        content=synopsis,
                        raw_response=synopsis_result.get('metadata', {}),
                        summary='Synopsis generation call',
                        input_tokens=synopsis_input_tokens,
                        output_tokens=synopsis_output_tokens,
                        tokens_used=synopsis_total_tokens
                    )
            except Exception as e:
                print(f"Failed to create AIResponse for OpenAI: {e}")

        return {
            'service': 'OpenAI',
            'success': openai_response['success'],
            'content': openai_response['content'],
            'synopsis': synopsis,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'tokens_used': total_tokens,
            'error': openai_response.get('error')
        }

    except Exception as e:
        return {
            'service': 'OpenAI',
            'success': False,
            'content': None,
            'synopsis': 'Synopsis generation failed',
            'error': str(e)
        }


async def process_gemini(message: str, chat_history: str, web_search_context: str, search_result: dict, use_web_search: bool, ai_query):
    """Process Gemini request with main response and synopsis generation."""
    try:
        gemini_service = AIServiceFactory.create_service(
            'gemini',
            settings.GEMINI_API_KEY,
            model='gemini-2.0-flash-exp'
        )

        # Prepare context
        context = {}
        enhanced_message = message

        if chat_history:
            enhanced_message = f"Previous conversation:\n{chat_history}\n\n{'='*50}\n\nNew user question:\n{message}"

        if web_search_context and use_web_search and search_result and search_result.get('success', False):
            context['web_search'] = {
                'enabled': True,
                'results': search_result['results']
            }
            if chat_history:
                enhanced_message = f"Previous conversation:\n{chat_history}\n\n{'='*50}\n\nCurrent web information:\n{web_search_context}\n\n{'='*50}\n\nNew user question:\n{message}\n\nPlease provide a comprehensive response considering the conversation context and using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results."
            else:
                enhanced_message = f"Current web information:\n{web_search_context}\n\n{'='*50}\n\nUser question:\n{message}\n\nPlease provide a comprehensive response using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results."

        # Get main response
        gemini_response = await gemini_service.generate_response(enhanced_message, context)

        # Generate synopsis
        synopsis = "No synopsis available"
        synopsis_result = None
        if gemini_response['success'] and gemini_response['content']:
            synopsis_result = await generate_synopsis_with_same_ai(
                gemini_response['content'],
                'gemini',
                settings.GEMINI_API_KEY,
                'gemini-2.0-flash-exp'
            )
            synopsis = synopsis_result.get('synopsis', 'No synopsis available')

        # Extract tokens
        input_tokens, output_tokens = extract_tokens(
            gemini_response.get('metadata', {}),
            'gemini'
        )
        total_tokens = calculate_total_tokens(input_tokens, output_tokens)

        # Create AIResponse records
        if ai_query:
            try:
                gemini_service_obj = await sync_to_async(AIService.objects.get)(name='gemini')

                # Main response record
                await sync_to_async(AIResponse.objects.create)(
                    query=ai_query,
                    service=gemini_service_obj,
                    content=gemini_response['content'],
                    raw_response=gemini_response.get('metadata', {}),
                    summary=synopsis,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    tokens_used=total_tokens
                )

                # Synopsis generation record
                if synopsis_result and synopsis_result.get('success'):
                    synopsis_input_tokens, synopsis_output_tokens = extract_tokens(
                        synopsis_result.get('metadata', {}),
                        'gemini'
                    )
                    synopsis_total_tokens = calculate_total_tokens(synopsis_input_tokens, synopsis_output_tokens)
                    await sync_to_async(AIResponse.objects.create)(
                        query=ai_query,
                        service=gemini_service_obj,
                        content=synopsis,
                        raw_response=synopsis_result.get('metadata', {}),
                        summary='Synopsis generation call',
                        input_tokens=synopsis_input_tokens,
                        output_tokens=synopsis_output_tokens,
                        tokens_used=synopsis_total_tokens
                    )
            except Exception as e:
                print(f"Failed to create AIResponse for Gemini: {e}")

        return {
            'service': 'Gemini',
            'success': gemini_response['success'],
            'content': gemini_response['content'],
            'synopsis': synopsis,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'tokens_used': total_tokens,
            'error': gemini_response.get('error')
        }

    except Exception as e:
        return {
            'service': 'Gemini',
            'success': False,
            'content': None,
            'synopsis': 'Synopsis generation failed',
            'error': str(e)
        }


async def process_all_services_async(message: str, services: list, use_web_search: bool, chat_history: str, conversation_id: str, user_location: dict = None):
    """
    Async helper that coordinates parallel LLM calls.
    """
    # Create AIQuery for cost tracking if a conversation is provided
    ai_query = None
    if conversation_id:
        try:
            conversation = await sync_to_async(Conversation.objects.select_related('user').get)(
                id=conversation_id
            )
            ai_query = await sync_to_async(AIQuery.objects.create)(
                user=conversation.user,
                conversation=conversation,
                prompt=message,
                context={'chat_history': chat_history, 'use_web_search': use_web_search},
                status='processing',
                services_requested=services
            )
        except Exception as e:
            print(f"Failed to create AIQuery: {e}")
            import traceback
            traceback.print_exc()
            pass

    # Perform web search once if needed
    web_search_context = ""
    search_result = {}

    if use_web_search:
        try:
            print(f"[WEB SEARCH] Web search enabled for query: {message[:50]}...")
            print(f"[WEB SEARCH] User location: {user_location}")

            # Add overall timeout for web search
            async def search_with_timeout():
                web_search_coordinator = WebSearchCoordinator()
                return await web_search_coordinator.search_for_query(
                    user_query=message,
                    user=None,
                    context={},
                    user_location=user_location
                )

            # Wrap in timeout - fail gracefully if takes too long
            search_result = await asyncio.wait_for(search_with_timeout(), timeout=15.0)

            print(f"[WEB SEARCH] Search result success: {search_result.get('success')}")
            print(f"[WEB SEARCH] Search result error: {search_result.get('error')}")
            print(f"[WEB SEARCH] Results count: {len(search_result.get('results', []))}")

            if search_result.get('success', False) and search_result.get('results'):
                search_summary = []
                for idx, result in enumerate(search_result['results'][:5], 1):
                    search_summary.append(
                        f"{idx}. {result.get('title', 'No title')}\n"
                        f"   URL: {result.get('url', 'No URL')}\n"
                        f"   {result.get('content', 'No content')[:200]}...\n"
                    )
                web_search_context = '\n'.join(search_summary)
                print(f"[WEB SEARCH] Web search context created with {len(search_summary)} results")
            else:
                print(f"[WEB SEARCH] No valid search results to process")
        except asyncio.TimeoutError:
            print(f"[WEB SEARCH] Web search timed out after 15 seconds - continuing without search")
        except Exception as e:
            print(f"[WEB SEARCH] Web search failed: {str(e)}")
            import traceback
            traceback.print_exc()

    # Build list of coroutines for requested services
    tasks = []

    if 'claude' in services and settings.CLAUDE_API_KEY:
        tasks.append(process_claude(message, chat_history, web_search_context, search_result, use_web_search, ai_query))

    if 'openai' in services and settings.OPENAI_API_KEY:
        tasks.append(process_openai(message, chat_history, web_search_context, search_result, use_web_search, ai_query))

    if 'gemini' in services and settings.GEMINI_API_KEY:
        tasks.append(process_gemini(message, chat_history, web_search_context, search_result, use_web_search, ai_query))

    # Run all service requests concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any exceptions that occurred
    processed_results = []
    for result in results:
        if isinstance(result, Exception):
            print(f"Error in parallel execution: {result}")
            processed_results.append({
                'service': 'Unknown',
                'success': False,
                'content': None,
                'synopsis': 'Error occurred',
                'error': str(result)
            })
        else:
            processed_results.append(result)

    # Update AIQuery status
    if ai_query:
        try:
            ai_query.status = 'completed'
            ai_query.completed_at = timezone.now()
            ai_query.total_responses = len(processed_results)
            await sync_to_async(ai_query.save)()

            # Update conversation stats to recalculate costs
            if ai_query.conversation:
                await sync_to_async(ai_query.conversation.update_conversation_metadata)()
        except Exception as e:
            print(f"Failed to update AIQuery: {e}")

    return processed_results


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_ai_services(request):
    """
    Parallelized test endpoint for AI service integration.
    POST /api/v1/test-ai/
    Body: {"message": "test question", "services": ["claude", "openai"], "use_web_search": true}

    SECURITY: This endpoint is for testing/diagnostics only.
    Requires authentication and ENABLE_TEST_AI_ENDPOINTS=True in settings.
    """
    # Check if test endpoints are enabled
    disabled_response = check_test_endpoints_enabled()
    if disabled_response:
        return disabled_response

    try:
        data = request.data
        message = data.get('message', 'Hello, how are you?')
        services = data.get('services', ['claude', 'openai', 'gemini'])
        use_web_search = data.get('use_web_search', False)
        user_location = data.get('user_location')
        chat_history = data.get('chat_history', '')
        conversation_id = data.get('conversation_id')

        # Run async processing
        results = asyncio.run(
            process_all_services_async(
                message=message,
                services=services,
                use_web_search=use_web_search,
                chat_history=chat_history,
                conversation_id=conversation_id,
                user_location=user_location
            )
        )

        return JsonResponse({
            'success': True,
            'results': results,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def combine_responses(request):
    """
    Combine two LLM responses into a unified synthesis.

    SECURITY: This endpoint is for testing/diagnostics only.
    Requires authentication and ENABLE_TEST_AI_ENDPOINTS=True in settings.
    """
    # Check if test endpoints are enabled
    disabled_response = check_test_endpoints_enabled()
    if disabled_response:
        return disabled_response

    try:
        data = request.data
        user_query = data.get('user_query', '')
        llm1_name = data.get('llm1_name', '')
        llm1_response = data.get('llm1_response', '')
        llm2_name = data.get('llm2_name', '')
        llm2_response = data.get('llm2_response', '')
        chat_history = data.get('chat_history', '')
        conversation_id = data.get('conversation_id')  # Optional for cost tracking

        if not all([user_query, llm1_name, llm1_response, llm2_name, llm2_response]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        # Create the synthesis prompt
        synthesis_prompt = f"""Role:
You are tasked with synthesizing information from multiple LLM responses into a single, cohesive output. Your job is to surface the shared insights, highlight important differences, and present a unified narrative that is clear, accurate, and professional.

Instructions:

1. Analyze the Sources
   - Carefully read each provided response.
   - Extract the key arguments, supporting evidence, tone, and framing from each.

2. Identify Common Ground
   - Determine the central ideas, concepts, or themes that appear across most or all responses.
   - Emphasize these shared elements as the backbone of your synthesis.

3. Acknowledge Divergences
   - Identify significant points of disagreement, alternative perspectives, or differences in emphasis.
   - Briefly note these divergences, and if relevant, suggest why they may exist (e.g., different assumptions, focus areas, or contexts).

4. Integrate & Re-Present
   - Write a new, unified response that:
     * Clearly articulates the common themes.
     * Integrates unique insights that add depth and nuance.
     * Acknowledges divergences without letting them overshadow consensus.
   - Use consistent, professional tone and logical flow.
   - Reinforce the shared themes with related language (e.g., if "efficiency" is a theme, also use "streamlined," "optimized," "productive").

5. Structure the Output
   - Part 1: Common Themes – Outline and explain the main overlapping ideas and why they matter.
   - Part 2: Diverse Perspectives – Incorporate distinctive viewpoints, showing how they enrich or expand the common ground.
   - Part 3: Unified Narrative – Blend both common and divergent insights into a coherent conclusion that leaves the reader with a clear, comprehensive understanding.

Format Requirements:
- Approx. 500–700 words.
- Use clear headings or smooth paragraph transitions to organize the response.
- When appropriate, cite the originating source in parentheses (e.g., "({llm1_name})" or "({llm2_name})") to maintain transparency.

Original User Query: {user_query}

Chat History: {chat_history}

Sources:

Source 1 ({llm1_name}):
{llm1_response}

Source 2 ({llm2_name}):
{llm2_response}

Please provide your synthesis now:"""

        # Use Claude for synthesis (or OpenAI as fallback)
        synthesis_service = None
        synthesis_provider = None

        # Try Claude first for high-quality synthesis
        if settings.CLAUDE_API_KEY:
            try:
                synthesis_service = AIServiceFactory.create_service(
                    'claude',
                    settings.CLAUDE_API_KEY,
                    model='claude-sonnet-4-20250514'
                )
                synthesis_provider = 'Claude'
            except Exception:
                synthesis_service = None

        # Fallback to OpenAI if Claude unavailable
        if not synthesis_service and settings.OPENAI_API_KEY:
            synthesis_service = AIServiceFactory.create_service(
                'openai',
                settings.OPENAI_API_KEY,
                model='gpt-4o'
            )
            synthesis_provider = 'OpenAI'

        if synthesis_service:
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                synthesis_response = loop.run_until_complete(
                    synthesis_service.generate_response(synthesis_prompt)
                )
            finally:
                loop.close()

            if synthesis_response['success']:
                # Track cost if conversation_id provided
                if conversation_id:
                    try:
                        from uuid import UUID
                        conversation = Conversation.objects.get(id=UUID(conversation_id))
                        ai_query = AIQuery.objects.create(
                            user=conversation.user,
                            conversation=conversation,
                            prompt=f"Synthesis: {user_query[:100]}",
                            status='completed',
                            started_at=timezone.now(),
                            completed_at=timezone.now()
                        )

                        # Get service object
                        service_name = synthesis_provider.lower()
                        service_obj = AIService.objects.get(name=service_name)

                        # Extract tokens
                        input_tokens, output_tokens = extract_tokens(
                            synthesis_response.get('metadata', {}),
                            service_name
                        )
                        total_tokens = calculate_total_tokens(input_tokens, output_tokens)

                        # Create AIResponse record
                        AIResponse.objects.create(
                            query=ai_query,
                            service=service_obj,
                            content=synthesis_response['content'],
                            raw_response=synthesis_response.get('metadata', {}),
                            summary='Response synthesis',
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            tokens_used=total_tokens
                        )

                        # Ensure conversation aggregates reflect the new cost entry
                        conversation.update_conversation_metadata()
                    except Exception as e:
                        print(f"Failed to track synthesis cost: {e}")

                return JsonResponse({
                    'success': True,
                    'synthesis': synthesis_response['content'],
                    'synthesis_provider': synthesis_provider
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': f"Synthesis generation failed: {synthesis_response.get('error', 'Unknown error')}"
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'error': 'No AI service available for synthesis functionality (configure Claude or OpenAI API keys)'
            }, status=500)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def critique_compare(request):
    """
    Compare two LLM responses using AI critique framework.

    SECURITY: This endpoint is for testing/diagnostics only.
    Requires authentication and ENABLE_TEST_AI_ENDPOINTS=True in settings.
    """
    # Check if test endpoints are enabled
    disabled_response = check_test_endpoints_enabled()
    if disabled_response:
        return disabled_response

    try:
        data = request.data
        user_query = data.get('user_query', '')
        llm1_name = data.get('llm1_name', '')
        llm1_response = data.get('llm1_response', '')
        llm2_name = data.get('llm2_name', '')
        llm2_response = data.get('llm2_response', '')
        chat_history = data.get('chat_history', '')
        conversation_id = data.get('conversation_id')  # Optional for cost tracking

        # DEBUG: Log received conversation_id
        print(f"[CRITIQUE_COMPARE DEBUG] Received conversation_id: {conversation_id}")
        print(f"[CRITIQUE_COMPARE DEBUG] Request data keys: {data.keys()}")

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

        # Use OpenAI for critique to avoid bias (if available), fallback to Claude
        critique_service = None
        critique_provider = None

        # Try OpenAI first to avoid self-evaluation bias when comparing Claude responses
        if settings.OPENAI_API_KEY and 'claude' in [llm1_name.lower(), llm2_name.lower()]:
            try:
                critique_service = AIServiceFactory.create_service(
                    'openai',
                    settings.OPENAI_API_KEY,
                    model='gpt-4o'
                )
                critique_provider = 'OpenAI (unbiased)'
            except Exception:
                critique_service = None

        # Fallback to Claude if OpenAI unavailable or no Claude responses being compared
        if not critique_service and settings.CLAUDE_API_KEY:
            critique_service = AIServiceFactory.create_service(
                'claude',
                settings.CLAUDE_API_KEY,
                model='claude-sonnet-4-20250514'
            )
            critique_provider = 'Claude'

        if critique_service:
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                critique_response = loop.run_until_complete(
                    critique_service.generate_response(critique_prompt)
                )
            finally:
                loop.close()

            if critique_response['success']:
                # Track cost if conversation_id provided
                print(f"[CRITIQUE_COMPARE DEBUG] About to check conversation_id: {conversation_id}")
                if conversation_id:
                    print(f"[CRITIQUE_COMPARE DEBUG] conversation_id is truthy, attempting to track cost")
                    try:
                        from uuid import UUID
                        conversation = Conversation.objects.get(id=UUID(conversation_id))
                        print(f"[CRITIQUE_COMPARE DEBUG] Found conversation: {conversation.id}")
                        ai_query = AIQuery.objects.create(
                            user=conversation.user,
                            conversation=conversation,
                            prompt=f"Critique: {user_query[:100]}",
                            status='completed',
                            started_at=timezone.now(),
                            completed_at=timezone.now()
                        )
                        print(f"[CRITIQUE_COMPARE DEBUG] Created AIQuery: {ai_query.id}")

                        # Get service object
                        service_name = 'openai' if 'openai' in critique_provider.lower() else 'claude'
                        service_obj = AIService.objects.get(name=service_name)

                        # Extract tokens
                        input_tokens, output_tokens = extract_tokens(
                            critique_response.get('metadata', {}),
                            service_name
                        )
                        total_tokens = calculate_total_tokens(input_tokens, output_tokens)

                        # Create AIResponse record
                        AIResponse.objects.create(
                            query=ai_query,
                            service=service_obj,
                            content=critique_response['content'],
                            raw_response=critique_response.get('metadata', {}),
                            summary='Response comparison critique',
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            tokens_used=total_tokens
                        )
                        print(f"[CRITIQUE_COMPARE DEBUG] Created AIResponse for service: {service_name}")

                        # Refresh conversation aggregates so cost updates propagate to the UI
                        conversation.update_conversation_metadata()
                    except Exception as e:
                        print(f"[CRITIQUE_COMPARE DEBUG] Failed to track critique cost: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"[CRITIQUE_COMPARE DEBUG] conversation_id is falsy, skipping cost tracking")

                return JsonResponse({
                    'success': True,
                    'critique': critique_response['content'],
                    'critique_provider': critique_provider
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': f"Critique generation failed: {critique_response.get('error', 'Unknown error')}"
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'error': 'No AI service available for critique functionality (configure OpenAI or Claude API keys)'
            }, status=500)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cross_reflect(request):
    """
    Generate cross-reflections where each LLM reflects on the other's response.
    Each LLM receives the peer's answer and provides a reflection/critique.

    SECURITY: This endpoint is for testing/diagnostics only.
    Requires authentication and ENABLE_TEST_AI_ENDPOINTS=True in settings.
    """
    # Check if test endpoints are enabled
    disabled_response = check_test_endpoints_enabled()
    if disabled_response:
        return disabled_response

    try:
        data = request.data
        user_query = data.get('user_query', '')
        llm1_name = data.get('llm1_name', '')
        llm1_response = data.get('llm1_response', '')
        llm2_name = data.get('llm2_name', '')
        llm2_response = data.get('llm2_response', '')
        chat_history = data.get('chat_history', '')
        conversation_id = data.get('conversation_id')  # Optional for cost tracking

        if not all([user_query, llm1_name, llm1_response, llm2_name, llm2_response]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        # Map service names to their configurations
        service_config = {
            'claude': {
                'api_key': settings.CLAUDE_API_KEY,
                'model': 'claude-sonnet-4-20250514'
            },
            'openai': {
                'api_key': settings.OPENAI_API_KEY,
                'model': 'gpt-4o'
            },
            'gemini': {
                'api_key': settings.GEMINI_API_KEY,
                'model': 'gemini-2.0-flash-exp'
            }
        }

        # Normalize service names
        llm1_key = llm1_name.lower()
        llm2_key = llm2_name.lower()

        # Validate that both services are available
        if llm1_key not in service_config or llm2_key not in service_config:
            return JsonResponse({
                'success': False,
                'error': f'Invalid service names: {llm1_name}, {llm2_name}'
            }, status=400)

        if not service_config[llm1_key]['api_key'] or not service_config[llm2_key]['api_key']:
            return JsonResponse({
                'success': False,
                'error': 'API keys not configured for the selected services'
            }, status=400)

        # Create reflection prompts
        # LLM1 reflects on LLM2's response
        llm1_reflection_prompt = f"""You are {llm1_name}, and you previously provided a response to a user's query. Now you are given the opportunity to reflect on another AI's response to the same query.

Original User Query: {user_query}

Chat History: {chat_history}

Your Original Response:
{llm1_response}

{llm2_name}'s Response:
{llm2_response}

Instructions:
Please provide a thoughtful reflection on {llm2_name}'s response. Consider:
1. What insights or perspectives did {llm2_name} offer that you may have missed or underemphasized?
2. Are there any points where {llm2_name}'s approach differs from yours? If so, evaluate the merits of their approach.
3. What can you learn from {llm2_name}'s response that could improve your future answers?
4. If you were to revise your original response based on {llm2_name}'s perspective, what would you change or add?
5. Are there any areas where you still believe your approach was stronger? Explain why.

Provide a balanced, constructive reflection that demonstrates intellectual honesty and a willingness to learn from other perspectives."""

        # LLM2 reflects on LLM1's response
        llm2_reflection_prompt = f"""You are {llm2_name}, and you previously provided a response to a user's query. Now you are given the opportunity to reflect on another AI's response to the same query.

Original User Query: {user_query}

Chat History: {chat_history}

Your Original Response:
{llm2_response}

{llm1_name}'s Response:
{llm1_response}

Instructions:
Please provide a thoughtful reflection on {llm1_name}'s response. Consider:
1. What insights or perspectives did {llm1_name} offer that you may have missed or underemphasized?
2. Are there any points where {llm1_name}'s approach differs from yours? If so, evaluate the merits of their approach.
3. What can you learn from {llm1_name}'s response that could improve your future answers?
4. If you were to revise your original response based on {llm1_name}'s perspective, what would you change or add?
5. Are there any areas where you still believe your approach was stronger? Explain why.

Provide a balanced, constructive reflection that demonstrates intellectual honesty and a willingness to learn from other perspectives."""

        # Create AI service instances
        llm1_service = AIServiceFactory.create_service(
            llm1_key,
            service_config[llm1_key]['api_key'],
            model=service_config[llm1_key]['model']
        )

        llm2_service = AIServiceFactory.create_service(
            llm2_key,
            service_config[llm2_key]['api_key'],
            model=service_config[llm2_key]['model']
        )

        # Run both reflections in parallel for better performance
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Generate both reflections concurrently
            llm1_reflection_response, llm2_reflection_response = loop.run_until_complete(
                asyncio.gather(
                    llm1_service.generate_response(llm1_reflection_prompt),
                    llm2_service.generate_response(llm2_reflection_prompt)
                )
            )

            # Generate synopses for both reflections
            llm1_synopsis, llm2_synopsis = loop.run_until_complete(
                asyncio.gather(
                    generate_synopsis_with_same_ai(
                        llm1_reflection_response.get('content', ''),
                        llm1_key,
                        service_config[llm1_key]['api_key'],
                        service_config[llm1_key]['model']
                    ) if llm1_reflection_response.get('success') else asyncio.sleep(0, result="Reflection failed"),
                    generate_synopsis_with_same_ai(
                        llm2_reflection_response.get('content', ''),
                        llm2_key,
                        service_config[llm2_key]['api_key'],
                        service_config[llm2_key]['model']
                    ) if llm2_reflection_response.get('success') else asyncio.sleep(0, result="Reflection failed")
                )
            )
        finally:
            loop.close()

        # Check if both reflections succeeded
        if llm1_reflection_response.get('success') and llm2_reflection_response.get('success'):
            # Track cost if conversation_id provided
            if conversation_id:
                try:
                    from uuid import UUID
                    conversation = Conversation.objects.get(id=UUID(conversation_id))
                    ai_query = AIQuery.objects.create(
                        user=conversation.user,
                        conversation=conversation,
                        prompt=f"Cross-reflection: {user_query[:100]}",
                        status='completed',
                        started_at=timezone.now(),
                        completed_at=timezone.now()
                    )

                    # Track LLM1's reflection
                    llm1_service_obj = AIService.objects.get(name=llm1_key)
                    llm1_input_tokens, llm1_output_tokens = extract_tokens(
                        llm1_reflection_response.get('metadata', {}),
                        llm1_key
                    )
                    llm1_total_tokens = calculate_total_tokens(llm1_input_tokens, llm1_output_tokens)

                    AIResponse.objects.create(
                        query=ai_query,
                        service=llm1_service_obj,
                        content=llm1_reflection_response.get('content', ''),
                        raw_response=llm1_reflection_response.get('metadata', {}),
                        summary=f'{llm1_name} reflecting on {llm2_name}',
                        input_tokens=llm1_input_tokens,
                        output_tokens=llm1_output_tokens,
                        tokens_used=llm1_total_tokens
                    )

                    # Track LLM2's reflection
                    llm2_service_obj = AIService.objects.get(name=llm2_key)
                    llm2_input_tokens, llm2_output_tokens = extract_tokens(
                        llm2_reflection_response.get('metadata', {}),
                        llm2_key
                    )
                    llm2_total_tokens = calculate_total_tokens(llm2_input_tokens, llm2_output_tokens)

                    AIResponse.objects.create(
                        query=ai_query,
                        service=llm2_service_obj,
                        content=llm2_reflection_response.get('content', ''),
                        raw_response=llm2_reflection_response.get('metadata', {}),
                        summary=f'{llm2_name} reflecting on {llm1_name}',
                        input_tokens=llm2_input_tokens,
                        output_tokens=llm2_output_tokens,
                        tokens_used=llm2_total_tokens
                    )

                    # Track synopsis costs if they were generated
                    if isinstance(llm1_synopsis, dict) and llm1_synopsis.get('success'):
                        llm1_syn_input, llm1_syn_output = extract_tokens(
                            llm1_synopsis.get('metadata', {}),
                            llm1_key
                        )
                        AIResponse.objects.create(
                            query=ai_query,
                            service=llm1_service_obj,
                            content=llm1_synopsis.get('synopsis', ''),
                            raw_response=llm1_synopsis.get('metadata', {}),
                            summary='Synopsis generation for cross-reflection',
                            input_tokens=llm1_syn_input,
                            output_tokens=llm1_syn_output,
                            tokens_used=calculate_total_tokens(llm1_syn_input, llm1_syn_output)
                        )

                    if isinstance(llm2_synopsis, dict) and llm2_synopsis.get('success'):
                        llm2_syn_input, llm2_syn_output = extract_tokens(
                            llm2_synopsis.get('metadata', {}),
                            llm2_key
                        )
                        AIResponse.objects.create(
                            query=ai_query,
                            service=llm2_service_obj,
                            content=llm2_synopsis.get('synopsis', ''),
                            raw_response=llm2_synopsis.get('metadata', {}),
                            summary='Synopsis generation for cross-reflection',
                            input_tokens=llm2_syn_input,
                            output_tokens=llm2_syn_output,
                            tokens_used=calculate_total_tokens(llm2_syn_input, llm2_syn_output)
                        )

                    # Refresh conversation metadata so aggregated costs include these reflections
                    conversation.update_conversation_metadata()
                except Exception as e:
                    print(f"Failed to track cross-reflection cost: {e}")

            return JsonResponse({
                'success': True,
                'reflections': [
                    {
                        'service': llm1_name,
                        'content': llm1_reflection_response.get('content', ''),
                        'synopsis': llm1_synopsis.get('synopsis', 'No synopsis available') if isinstance(llm1_synopsis, dict) else llm1_synopsis,
                        'reflecting_on': llm2_name
                    },
                    {
                        'service': llm2_name,
                        'content': llm2_reflection_response.get('content', ''),
                        'synopsis': llm2_synopsis.get('synopsis', 'No synopsis available') if isinstance(llm2_synopsis, dict) else llm2_synopsis,
                        'reflecting_on': llm1_name
                    }
                ]
            })
        else:
            # Handle partial or complete failure
            errors = []
            if not llm1_reflection_response.get('success'):
                errors.append(f"{llm1_name}: {llm1_reflection_response.get('error', 'Unknown error')}")
            if not llm2_reflection_response.get('success'):
                errors.append(f"{llm2_name}: {llm2_reflection_response.get('error', 'Unknown error')}")

            return JsonResponse({
                'success': False,
                'error': f"Cross-reflection failed: {'; '.join(errors)}"
            }, status=500)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
