"""
Integration tests for consensus endpoints.

Tests the full flow from HTTP request through service layer to database storage.
"""
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.conversations.models import Conversation
from apps.ai_services.models import AIService, AIQuery
from apps.responses.models import AIResponse

User = get_user_model()


@override_settings(
    ENABLE_CONSENSUS_ENDPOINTS=True,
    CLAUDE_API_KEY='test-claude-key',
    OPENAI_API_KEY='test-openai-key',
    GEMINI_API_KEY='test-gemini-key'
)
class ConsensusIntegrationTests(TransactionTestCase):
    """Test consensus endpoints with full integration flow."""

    def setUp(self):
        """Set up test data and API client."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create AI services
        self.claude_service = AIService.objects.create(
            name='claude',
            display_name='Claude',
            api_base_url='https://api.anthropic.com',
            model_name='claude-sonnet-4-20250514',
            input_cost_per_1k=Decimal('0.003'),
            output_cost_per_1k=Decimal('0.015')
        )
        self.openai_service = AIService.objects.create(
            name='openai',
            display_name='OpenAI',
            api_base_url='https://api.openai.com',
            model_name='gpt-4o',
            input_cost_per_1k=Decimal('0.005'),
            output_cost_per_1k=Decimal('0.015')
        )
        self.gemini_service = AIService.objects.create(
            name='gemini',
            display_name='Gemini',
            api_base_url='https://generativelanguage.googleapis.com',
            model_name='gemini-2.0-flash-exp',
            input_cost_per_1k=Decimal('0.001'),
            output_cost_per_1k=Decimal('0.002')
        )

        # Create a test conversation
        self.conversation = Conversation.objects.create(
            user=self.user,
            title='Test Conversation'
        )

    @patch('api.v1.consensus_ai.AIServiceFactory.create_service')
    @patch('api.v1.consensus_ai.WebSearchCoordinator.search_for_query')
    def test_full_consensus_flow_all_services_succeed(self, mock_search, mock_factory):
        """
        Test: User query → 3 LLMs → 6 AIResponse records (3 main + 3 synopsis) → cost aggregation
        """
        # Mock web search to return no results (disabled)
        mock_search.return_value = AsyncMock(return_value={'success': False, 'results': []})

        # Mock AI service responses
        mock_claude = MagicMock()
        mock_claude.generate_response = AsyncMock(return_value={
            'success': True,
            'content': 'Claude response about Django testing',
            'metadata': {
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 200
                }
            }
        })

        mock_openai = MagicMock()
        mock_openai.generate_response = AsyncMock(return_value={
            'success': True,
            'content': 'OpenAI response about Django testing',
            'metadata': {
                'usage': {
                    'prompt_tokens': 110,
                    'completion_tokens': 210
                }
            }
        })

        mock_gemini = MagicMock()
        mock_gemini.generate_response = AsyncMock(return_value={
            'success': True,
            'content': 'Gemini response about Django testing',
            'metadata': {
                'usage': {
                    'promptTokenCount': 90,
                    'candidatesTokenCount': 180
                }
            }
        })

        # Mock synopsis generation (same services called again)
        def mock_create_service(service_name, api_key, model=None):
            if 'claude' in service_name:
                return mock_claude
            elif 'openai' in service_name:
                return mock_openai
            elif 'gemini' in service_name:
                return mock_gemini
            return None

        mock_factory.side_effect = mock_create_service

        # Make request
        url = reverse('api_v1:consensus')
        data = {
            'message': 'What are best practices for Django testing?',
            'services': ['claude', 'openai', 'gemini'],
            'use_web_search': False,
            'conversation_id': str(self.conversation.id)
        }

        response = self.client.post(url, data, format='json')

        # Assert response structure
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['results']), 3)

        # Assert all services succeeded
        for result in response_data['results']:
            self.assertTrue(result['success'])
            self.assertIn(result['service'], ['Claude', 'OpenAI', 'Gemini'])
            self.assertIsNotNone(result['content'])
            self.assertIsNotNone(result['synopsis'])

        # Assert database records created
        # Should have 1 AIQuery
        ai_query = AIQuery.objects.filter(conversation=self.conversation).first()
        self.assertIsNotNone(ai_query)
        self.assertEqual(ai_query.status, 'completed')
        self.assertEqual(ai_query.services_requested, ['claude', 'openai', 'gemini'])

        # Should have 6 AIResponse records (3 main + 3 synopsis)
        ai_responses = AIResponse.objects.filter(query=ai_query)
        self.assertEqual(ai_responses.count(), 6)

        # Assert main responses have content and synopsis
        main_responses = ai_responses.exclude(summary='Synopsis generation call')
        self.assertEqual(main_responses.count(), 3)
        for response in main_responses:
            self.assertIsNotNone(response.content)
            self.assertIsNotNone(response.summary)  # synopsis stored in summary field
            self.assertGreater(response.tokens_used, 0)

        # Assert synopsis responses exist
        synopsis_responses = ai_responses.filter(summary='Synopsis generation call')
        self.assertEqual(synopsis_responses.count(), 3)

        # Note: Conversation.total_tokens_used is aggregated from Message records, not AIResponse records
        # The consensus endpoint creates AIResponse records for tracking AI service costs
        # Message records (which update conversation.total_tokens_used) are created separately
        # when messages are added to the conversation via other endpoints

    @patch('api.v1.consensus_ai.AIServiceFactory.create_service')
    def test_consensus_flow_with_partial_service_failure(self, mock_factory):
        """
        Test: 1 LLM fails → other 2 succeed → partial results + error handling
        """
        # Mock Claude to fail
        mock_claude = MagicMock()
        mock_claude.generate_response = AsyncMock(return_value={
            'success': False,
            'content': None,
            'error': 'API rate limit exceeded'
        })

        # Mock OpenAI and Gemini to succeed
        mock_openai = MagicMock()
        mock_openai.generate_response = AsyncMock(return_value={
            'success': True,
            'content': 'OpenAI response',
            'metadata': {'usage': {'prompt_tokens': 100, 'completion_tokens': 200}}
        })

        mock_gemini = MagicMock()
        mock_gemini.generate_response = AsyncMock(return_value={
            'success': True,
            'content': 'Gemini response',
            'metadata': {'usageMetadata': {'promptTokenCount': 90, 'candidatesTokenCount': 180}}
        })

        def mock_create_service(service_name, api_key, model=None):
            if 'claude' in service_name:
                return mock_claude
            elif 'openai' in service_name:
                return mock_openai
            elif 'gemini' in service_name:
                return mock_gemini
            return None

        mock_factory.side_effect = mock_create_service

        # Make request
        url = reverse('api_v1:consensus')
        data = {
            'message': 'Test query',
            'services': ['claude', 'openai', 'gemini'],
            'use_web_search': False,
            'conversation_id': str(self.conversation.id)
        }

        response = self.client.post(url, data, format='json')

        # Assert response indicates partial success
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertTrue(response_data['success'])  # Overall request succeeded
        self.assertEqual(len(response_data['results']), 3)

        # Assert Claude failed, others succeeded
        claude_result = next(r for r in response_data['results'] if r['service'] == 'Claude')
        self.assertFalse(claude_result['success'])
        self.assertEqual(claude_result['error'], 'API rate limit exceeded')

        openai_result = next(r for r in response_data['results'] if r['service'] == 'OpenAI')
        self.assertTrue(openai_result['success'])

        gemini_result = next(r for r in response_data['results'] if r['service'] == 'Gemini')
        self.assertTrue(gemini_result['success'])

        # Assert only successful services created AIResponse records
        ai_query = AIQuery.objects.filter(conversation=self.conversation).first()
        ai_responses = AIResponse.objects.filter(query=ai_query)
        # Should have 4 records (2 main + 2 synopsis for successful services)
        self.assertEqual(ai_responses.count(), 4)

    @patch('api.v1.consensus_ai.AIServiceFactory.create_service')
    def test_synthesis_endpoint_combines_responses(self, mock_factory):
        """
        Test: 2 LLM responses → synthesis → cost tracked
        """
        # Mock synthesis service (Claude)
        mock_claude = MagicMock()
        mock_claude.generate_response = AsyncMock(return_value={
            'success': True,
            'content': 'Synthesized response combining both perspectives on Django ORM...',
            'metadata': {
                'usage': {
                    'input_tokens': 500,
                    'output_tokens': 300
                }
            }
        })

        mock_factory.return_value = mock_claude

        # Make request
        url = reverse('api_v1:consensus_synthesis')
        data = {
            'user_query': 'What is Django ORM?',
            'llm1_name': 'Claude',
            'llm1_response': 'Django ORM is an object-relational mapper...',
            'llm2_name': 'OpenAI',
            'llm2_response': 'Django ORM provides a Pythonic interface...',
            'chat_history': '',
            'conversation_id': str(self.conversation.id)
        }

        response = self.client.post(url, data, format='json')

        # Assert response structure
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertIn('synthesis', response_data)
        self.assertIn('synthesis_provider', response_data)
        self.assertEqual(response_data['synthesis_provider'], 'Claude')

        # Assert cost tracked
        ai_query = AIQuery.objects.filter(
            conversation=self.conversation,
            prompt__startswith='Synthesis:'
        ).first()
        self.assertIsNotNone(ai_query)
        self.assertEqual(ai_query.status, 'completed')

        ai_response = AIResponse.objects.filter(query=ai_query).first()
        self.assertIsNotNone(ai_response)
        self.assertEqual(ai_response.summary, 'Response synthesis')
        self.assertGreater(ai_response.tokens_used, 0)

    @patch('api.v1.consensus_ai.AIServiceFactory.create_service')
    def test_critique_endpoint_compares_responses(self, mock_factory):
        """
        Test: 2 responses → critique → correct provider selected
        """
        # Mock critique service (OpenAI for unbiased comparison when Claude is involved)
        mock_openai = MagicMock()
        mock_openai.generate_response = AsyncMock(return_value={
            'success': True,
            'content': '## Executive Summary\nClaude provides more detailed examples...',
            'metadata': {
                'usage': {
                    'prompt_tokens': 600,
                    'completion_tokens': 400
                }
            }
        })

        mock_factory.return_value = mock_openai

        # Make request
        url = reverse('api_v1:consensus_critique')
        data = {
            'user_query': 'Explain Django signals',
            'llm1_name': 'Claude',
            'llm1_response': 'Django signals allow decoupled applications...',
            'llm2_name': 'OpenAI',
            'llm2_response': 'Signals are a strategy to allow certain senders...',
            'chat_history': '',
            'conversation_id': str(self.conversation.id)
        }

        response = self.client.post(url, data, format='json')

        # Assert response structure
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertIn('critique', response_data)
        self.assertIn('critique_provider', response_data)
        # OpenAI should be selected for unbiased comparison
        self.assertEqual(response_data['critique_provider'], 'OpenAI (unbiased)')

        # Assert cost tracked
        ai_query = AIQuery.objects.filter(
            conversation=self.conversation,
            prompt__startswith='Critique:'
        ).first()
        self.assertIsNotNone(ai_query)

        ai_response = AIResponse.objects.filter(query=ai_query).first()
        self.assertIsNotNone(ai_response)
        self.assertEqual(ai_response.summary, 'Response comparison critique')

    @patch('api.v1.consensus_ai.AIServiceFactory.create_service')
    def test_cross_reflect_parallel_execution(self, mock_factory):
        """
        Test: 2 LLMs reflect on each other + synopses → 4 API calls → all tracked
        """
        # Mock both services for reflections and synopses
        mock_claude = MagicMock()
        mock_claude.generate_response = AsyncMock(return_value={
            'success': True,
            'content': 'Reflecting on OpenAI response: I appreciate the emphasis on...',
            'metadata': {'usage': {'input_tokens': 300, 'output_tokens': 250}}
        })

        mock_openai = MagicMock()
        mock_openai.generate_response = AsyncMock(return_value={
            'success': True,
            'content': 'Reflecting on Claude response: The detailed examples are valuable...',
            'metadata': {'usage': {'prompt_tokens': 310, 'completion_tokens': 260}}
        })

        def mock_create_service(service_name, api_key, model=None):
            if 'claude' in service_name:
                return mock_claude
            elif 'openai' in service_name:
                return mock_openai
            return None

        mock_factory.side_effect = mock_create_service

        # Make request
        url = reverse('api_v1:consensus_cross_reflect')
        data = {
            'user_query': 'What is REST API design?',
            'llm1_name': 'Claude',
            'llm1_response': 'REST APIs should follow stateless design...',
            'llm2_name': 'OpenAI',
            'llm2_response': 'RESTful architecture emphasizes resource-based URLs...',
            'chat_history': '',
            'conversation_id': str(self.conversation.id)
        }

        response = self.client.post(url, data, format='json')

        # Assert response structure
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertIn('reflections', response_data)
        self.assertEqual(len(response_data['reflections']), 2)

        # Assert both reflections succeeded
        for reflection in response_data['reflections']:
            self.assertIn('service', reflection)
            self.assertIn('content', reflection)
            self.assertIn('synopsis', reflection)
            self.assertIn('reflecting_on', reflection)

        # Assert cost tracked for all 4 operations (2 reflections + 2 synopses)
        ai_query = AIQuery.objects.filter(
            conversation=self.conversation,
            prompt__startswith='Cross-reflection:'
        ).first()
        self.assertIsNotNone(ai_query)

        ai_responses = AIResponse.objects.filter(query=ai_query)
        # Should have 4 records (2 reflections + 2 synopses)
        self.assertEqual(ai_responses.count(), 4)

        # Assert reflection responses
        reflection_responses = ai_responses.exclude(summary='Synopsis generation for cross-reflection')
        self.assertEqual(reflection_responses.count(), 2)

    @patch('api.v1.consensus_ai.WebSearchCoordinator.search_for_query')
    @patch('api.v1.consensus_ai.AIServiceFactory.create_service')
    def test_web_search_timeout_graceful_degradation(self, mock_factory, mock_search):
        """
        Test: Web search times out → LLMs still run → no crash
        """
        # Mock web search to timeout
        import asyncio
        mock_search.side_effect = asyncio.TimeoutError('Search timed out after 200s')

        # Mock LLM to succeed
        mock_claude = MagicMock()
        mock_claude.generate_response = AsyncMock(return_value={
            'success': True,
            'content': 'Response without web search',
            'metadata': {'usage': {'input_tokens': 100, 'output_tokens': 200}}
        })

        mock_factory.return_value = mock_claude

        # Make request with web search enabled
        url = reverse('api_v1:consensus')
        data = {
            'message': 'Latest news about Django 5.0',
            'services': ['claude'],
            'use_web_search': True,  # Web search enabled
            'conversation_id': str(self.conversation.id)
        }

        response = self.client.post(url, data, format='json')

        # Assert request still succeeded despite web search timeout
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['results']), 1)
        self.assertTrue(response_data['results'][0]['success'])

        # Assert no web search sources returned
        self.assertEqual(len(response_data.get('web_search_sources', [])), 0)

    def test_unauthenticated_access_denied(self):
        """
        Test: No auth token → 401 or 403 response (authentication required)
        """
        # Remove authentication
        self.client.force_authenticate(user=None)

        url = reverse('api_v1:consensus')
        data = {
            'message': 'Test',
            'services': ['claude']
        }

        response = self.client.post(url, data, format='json')
        # Should return 401 (Unauthorized) or 403 (Forbidden) for unauthenticated access
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
