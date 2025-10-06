"""Tests for database maintenance utilities."""
from __future__ import annotations

from uuid import uuid4

from django.db import DEFAULT_DB_ALIAS, connection
from django.test import TransactionTestCase
from django.utils import timezone

from apps.conversations.maintenance import cleanup_orphan_messages
from apps.conversations.models import Conversation, Message


class CleanupOrphanMessagesTests(TransactionTestCase):
    """Ensure that orphaned message rows are removed safely."""

    reset_sequences = True

    def test_noop_when_tables_are_clean(self) -> None:
        """Calling the cleanup on a pristine database should not delete anything."""

        deleted = cleanup_orphan_messages(DEFAULT_DB_ALIAS)
        self.assertEqual(deleted, 0)

    def test_removes_orphan_messages(self) -> None:
        """The helper should delete message rows whose conversation is missing."""

        conversation = Conversation.objects.create(title="Temp conversation")
        conversation_id = str(conversation.id)
        conversation.delete()

        legacy_message_id = str(uuid4())
        inserted_at = timezone.now()

        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = OFF")
            cursor.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, timestamp, tokens_used, metadata, query_session)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    legacy_message_id,
                    conversation_id,
                    "user",
                    "Hello world",
                    inserted_at,
                    0,
                    "{}",
                    None,
                ],
            )
            cursor.execute("PRAGMA foreign_keys = ON")

        deleted = cleanup_orphan_messages(DEFAULT_DB_ALIAS)

        self.assertEqual(deleted, 1)
        self.assertFalse(
            Message.objects.filter(id=legacy_message_id).exists(),
            "Orphaned message rows should be removed by the cleanup utility.",
        )
