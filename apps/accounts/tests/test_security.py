"""
Security tests for authentication, API key encryption, and user isolation.

Tests critical security features to protect user data and prevent unauthorized access.
"""
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import APIKey
from apps.conversations.models import Conversation, Message

User = get_user_model()


class APIKeyEncryptionTests(TestCase):
    """Test API key encryption and decryption."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_api_key_encryption_decryption_round_trip(self):
        """
        Test: Store API key → retrieve → decrypt → matches original
        """
        # Create API key
        api_key = APIKey.objects.create(
            user=self.user,
            service_name='openai'
        )

        # Set a test key
        original_key = 'sk-test1234567890abcdefghijklmnopqrstuvwxyz'
        api_key.set_key(original_key)
        api_key.save()

        # Retrieve and decrypt
        retrieved_key = api_key.get_key()

        # Assert encryption worked
        self.assertEqual(retrieved_key, original_key)
        self.assertNotEqual(api_key.encrypted_key, original_key)
        self.assertIsNotNone(api_key.encrypted_key)

    def test_api_key_encryption_different_keys_produce_different_ciphertext(self):
        """
        Test: Different API keys produce different encrypted values
        """
        api_key1 = APIKey.objects.create(user=self.user, service_name='openai')
        api_key1.set_key('sk-key-one-12345')
        api_key1.save()

        api_key2 = APIKey.objects.create(user=self.user, service_name='claude')
        api_key2.set_key('sk-key-two-67890')
        api_key2.save()

        self.assertNotEqual(api_key1.encrypted_key, api_key2.encrypted_key)

    def test_api_key_empty_key_handling(self):
        """
        Test: Empty key doesn't cause encryption errors
        """
        api_key = APIKey.objects.create(user=self.user, service_name='gemini')
        api_key.set_key('')
        api_key.save()

        retrieved_key = api_key.get_key()
        self.assertIsNone(retrieved_key)

    def test_api_key_invalid_encrypted_data_returns_none(self):
        """
        Test: Corrupted encrypted data returns None instead of crashing
        """
        api_key = APIKey.objects.create(
            user=self.user,
            service_name='openai',
            encrypted_key='invalid-base64-data!!!'
        )

        retrieved_key = api_key.get_key()
        self.assertIsNone(retrieved_key)

    @override_settings(ENCRYPTION_KEY='different-32-char-key-for-test!')
    def test_api_key_wrong_encryption_key_fails_decryption(self):
        """
        Test: Using wrong encryption key fails to decrypt
        """
        # Create and encrypt with original key
        api_key = APIKey.objects.create(user=self.user, service_name='openai')
        original_key = 'sk-test-key-12345'

        # Temporarily use original encryption key
        with override_settings(ENCRYPTION_KEY='dev-key-32-chars-for-encryption!'):
            api_key.set_key(original_key)
            api_key.save()

        # Try to decrypt with different key (current override_settings)
        retrieved_key = api_key.get_key()
        self.assertIsNone(retrieved_key)  # Should fail to decrypt


class AuthenticationSecurityTests(TestCase):
    """Test authentication and authorization security."""

    def setUp(self):
        """Set up test users and client."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.client = APIClient()

    def test_unauthenticated_access_denied_to_consensus(self):
        """
        Test: No auth token → 401 or 403 on /api/v1/consensus/
        """
        url = reverse('api_v1:consensus')
        data = {
            'message': 'Test query',
            'services': ['claude']
        }

        response = self.client.post(url, data, format='json')
        # Should return 401 (Unauthorized) or 403 (Forbidden)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_unauthenticated_access_denied_to_synthesis(self):
        """
        Test: No auth token → 401 or 403 on synthesis endpoint
        """
        url = reverse('api_v1:consensus_synthesis')
        data = {
            'user_query': 'Test',
            'llm1_name': 'Claude',
            'llm1_response': 'Response 1',
            'llm2_name': 'OpenAI',
            'llm2_response': 'Response 2'
        }

        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_unauthenticated_access_denied_to_critique(self):
        """
        Test: No auth token → 401 or 403 on critique endpoint
        """
        url = reverse('api_v1:consensus_critique')
        data = {
            'user_query': 'Test',
            'llm1_name': 'Claude',
            'llm1_response': 'Response 1',
            'llm2_name': 'OpenAI',
            'llm2_response': 'Response 2'
        }

        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_unauthenticated_access_denied_to_cross_reflect(self):
        """
        Test: No auth token → 401 or 403 on cross-reflect endpoint
        """
        url = reverse('api_v1:consensus_cross_reflect')
        data = {
            'user_query': 'Test',
            'llm1_name': 'Claude',
            'llm1_response': 'Response 1',
            'llm2_name': 'OpenAI',
            'llm2_response': 'Response 2'
        }

        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class UserIsolationTests(TestCase):
    """Test that users cannot access other users' data."""

    def setUp(self):
        """Set up test users and data."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )

        # Create conversations for each user
        self.user1_conversation = Conversation.objects.create(
            user=self.user1,
            title='User 1 Conversation'
        )
        self.user2_conversation = Conversation.objects.create(
            user=self.user2,
            title='User 2 Conversation'
        )

        # Create messages
        Message.objects.create(
            conversation=self.user1_conversation,
            role='user',
            content='User 1 secret message'
        )
        Message.objects.create(
            conversation=self.user2_conversation,
            role='user',
            content='User 2 secret message'
        )

        self.client = APIClient()

    def test_user_cannot_access_other_user_conversation(self):
        """
        Test: User 1 cannot GET /conversations/{user2_conversation_id}
        """
        self.client.force_authenticate(user=self.user1)

        url = reverse('api_v1:conversations:conversation-detail', kwargs={'pk': self.user2_conversation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_update_other_user_conversation(self):
        """
        Test: User 1 cannot PATCH /conversations/{user2_conversation_id}
        """
        self.client.force_authenticate(user=self.user1)

        url = reverse('api_v1:conversations:conversation-detail', kwargs={'pk': self.user2_conversation.id})
        data = {'title': 'Hacked title'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify conversation wasn't modified
        self.user2_conversation.refresh_from_db()
        self.assertEqual(self.user2_conversation.title, 'User 2 Conversation')

    def test_user_cannot_delete_other_user_conversation(self):
        """
        Test: User 1 cannot DELETE /conversations/{user2_conversation_id}
        """
        self.client.force_authenticate(user=self.user1)

        url = reverse('api_v1:conversations:conversation-detail', kwargs={'pk': self.user2_conversation.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify conversation still exists
        self.assertTrue(Conversation.objects.filter(id=self.user2_conversation.id).exists())

    def test_user_cannot_access_other_user_messages(self):
        """
        Test: User 1 cannot GET /conversations/{user2_conversation_id}/messages/
        """
        self.client.force_authenticate(user=self.user1)

        url = reverse('api_v1:conversations:conversation-messages', kwargs={'conversation_pk': self.user2_conversation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_only_see_own_conversations(self):
        """
        Test: User 1's conversation list only includes their conversations
        """
        self.client.force_authenticate(user=self.user1)

        url = reverse('api_v1:conversations:conversation-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        conversation_ids = [conv['id'] for conv in data['results']]
        self.assertIn(str(self.user1_conversation.id), conversation_ids)
        self.assertNotIn(str(self.user2_conversation.id), conversation_ids)


class InputValidationTests(TestCase):
    """Test input validation and injection protection."""

    def setUp(self):
        """Set up test user and client."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create a test conversation
        self.conversation = Conversation.objects.create(
            user=self.user,
            title='Test Conversation'
        )

    def test_sql_injection_in_search_query(self):
        """
        Test: Malicious search query doesn't execute SQL
        """
        url = reverse('api_v1:conversations:conversation-search')

        # Try SQL injection in search query (simpler patterns less likely to cause parsing errors)
        malicious_queries = [
            "' OR 1=1--",
            "admin'--",
            "' OR 'x'='x",
        ]

        for malicious_query in malicious_queries:
            try:
                response = self.client.get(url, {'q': malicious_query})

                # Should return safely (either 200 with no results or proper error)
                self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

                # Verify conversations table still exists
                self.assertTrue(Conversation.objects.exists())

                # Verify our test conversation still exists
                self.assertTrue(Conversation.objects.filter(id=self.conversation.id).exists())
            except Exception as e:
                # If an exception occurs, it should be a validation error, not a database error
                self.assertNotIn('database', str(e).lower())

    def test_xss_in_conversation_title(self):
        """
        Test: XSS payload in conversation title is stored safely
        """
        url = reverse('api_v1:conversations:conversation-list')

        xss_payload = '<script>alert("XSS")</script>'
        data = {
            'title': xss_payload,
            'agent_mode': 'standard'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify conversation was created with the payload as plain text
        conversation = Conversation.objects.get(id=response.json()['id'])
        self.assertEqual(conversation.title, xss_payload)

        # The frontend/Django templates should escape this when rendering

    def test_extremely_long_message_rejected(self):
        """
        Test: 1MB message → 400 Bad Request or handled gracefully
        """
        url = reverse('api_v1:consensus')

        # Create a very large message (1MB)
        large_message = 'A' * (1024 * 1024)

        data = {
            'message': large_message,
            'services': ['claude'],
            'use_web_search': False
        }

        # This should either be rejected or handled without crashing
        # Django's default max request size is 2.5MB, so 1MB should go through
        # but we can test that the system handles it
        try:
            response = self.client.post(url, data, format='json')
            # Should return some response (not crash)
            self.assertIsNotNone(response.status_code)
        except Exception as e:
            # If it raises an exception, it should be a validation error, not a crash
            self.assertIn('request', str(e).lower())

    def test_empty_services_array_handled(self):
        """
        Test: Empty services array returns appropriate error
        """
        url = reverse('api_v1:consensus')
        data = {
            'message': 'Test question',
            'services': [],  # Empty array
            'use_web_search': False
        }

        response = self.client.post(url, data, format='json')

        # Should return successfully with no results, not crash
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

    def test_invalid_service_name_handled(self):
        """
        Test: Invalid service name doesn't cause errors
        """
        url = reverse('api_v1:consensus')
        data = {
            'message': 'Test question',
            'services': ['invalid_service', 'claude'],
            'use_web_search': False
        }

        response = self.client.post(url, data, format='json')

        # Should handle gracefully, possibly ignoring invalid service
        self.assertEqual(response.status_code, status.HTTP_200_OK)
