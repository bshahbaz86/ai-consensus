"""
Tests for authentication flows covering passcode login and Google OAuth linkage.
"""
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import EmailPasscode, User
from apps.accounts.serializers import PasscodeVerifySerializer


class PasscodeAuthenticationTests(TestCase):
    """Validate passcode verification edge cases."""

    def test_passcode_verify_generates_unique_username(self):
        """Second user with same email local-part gets unique username."""
        User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='testpass123'
        )

        EmailPasscode.objects.create(
            email='alice@yahoo.com',
            passcode='123456',
            expires_at=timezone.now() + timezone.timedelta(minutes=15)
        )

        serializer = PasscodeVerifySerializer(data={
            'email': 'alice@yahoo.com',
            'passcode': '123456'
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.validated_data['user']
        self.assertEqual(user.email, 'alice@yahoo.com')
        self.assertNotEqual(user.username.lower(), 'alice')
        self.assertTrue(user.username.lower().startswith('alice'))


@override_settings(
    SOCIALACCOUNT_PROVIDERS={
        'google': {
            'SCOPE': ['profile', 'email'],
            'AUTH_PARAMS': {'access_type': 'online'},
            'APP': {
                'client_id': 'test-client',
                'secret': 'test-secret',
            },
        }
    },
    FRONTEND_URL='http://localhost:3000',
    ENCRYPTION_KEY='dev-key-32-chars-for-encryption!'
)
class GoogleOAuthLinkingTests(TestCase):
    """Ensure Google OAuth links to existing accounts when emails match."""

    def setUp(self):
        self.client = APIClient()
        self.init_url = reverse('api_v1:accounts:google-oauth-init')
        self.callback_url = reverse('api_v1:accounts:google-oauth-callback')
        init_response = self.client.get(self.init_url)
        self.assertEqual(init_response.status_code, status.HTTP_200_OK)
        authorization_url = init_response.data['data']['authorization_url']
        parsed_query = parse_qs(urlparse(authorization_url).query)
        self.state = parsed_query['state'][0]

        self.user = User.objects.create_user(
            username='linkeduser',
            email='linked@example.com',
            password='testpass123'
        )

    def test_google_oauth_links_existing_email_user(self):
        """Users created without Google ID are linked instead of duplicated."""
        with patch('api.v1.accounts.views.requests.post') as mock_post, \
                patch('api.v1.accounts.views.requests.get') as mock_get:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'access_token': 'token-123',
                'refresh_token': 'refresh-456',
            }
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                'id': 'google-123',
                'email': 'linked@example.com',
                'name': 'Linked User',
                'picture': 'http://example.com/avatar.png',
            }

            response = self.client.post(
                self.callback_url,
                {'code': 'auth-code', 'state': self.state},
                format='json'
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data['data']
        self.assertFalse(data.get('is_new_user'))
        self.assertEqual(data['user']['email'], 'linked@example.com')

        self.user.refresh_from_db()
        self.assertEqual(self.user.google_id, 'google-123')
        self.assertEqual(User.objects.filter(email='linked@example.com').count(), 1)

    def test_google_oauth_callback_requires_state(self):
        """Missing state should be rejected."""
        response = self.client.post(self.callback_url, {'code': 'auth-code'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('state', response.data['message'].lower())

    def test_google_oauth_callback_rejects_invalid_state(self):
        """State mismatches are rejected."""
        response = self.client.post(
            self.callback_url,
            {'code': 'auth-code', 'state': 'invalid-state'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('state', response.data['message'].lower())
