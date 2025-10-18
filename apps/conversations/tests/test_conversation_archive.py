"""
Tests for conversation archive toggle behaviour.
"""
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.conversations.models import Conversation

User = get_user_model()


class ConversationArchiveTests(TestCase):
    """Ensure archive action keeps is_active and is_archived in sync."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='archivetester',
            email='archive@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.conversation = Conversation.objects.create(
            user=self.user,
            title='Archive Test'
        )

    def test_archive_action_toggles_flags_consistently(self):
        """PATCH archive should set is_archived True and is_active False, and toggle back."""
        url = reverse('api_v1:conversations:conversation-archive', args=[self.conversation.id])

        response = self.client.patch(url, format='json')
        self.assertEqual(response.status_code, 200)

        self.conversation.refresh_from_db()
        self.assertTrue(self.conversation.is_archived)
        self.assertFalse(self.conversation.is_active)

        # Toggle back to active
        response = self.client.patch(url, format='json')
        self.assertEqual(response.status_code, 200)

        self.conversation.refresh_from_db()
        self.assertFalse(self.conversation.is_archived)
        self.assertTrue(self.conversation.is_active)
