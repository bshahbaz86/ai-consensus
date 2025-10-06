"""Maintenance utilities for the conversations app."""
from __future__ import annotations

import logging
from typing import Iterable

from django.db import connections, DEFAULT_DB_ALIAS

logger = logging.getLogger(__name__)


REQUIRED_TABLES: frozenset[str] = frozenset({"messages", "conversations"})
AI_TABLES: frozenset[str] = frozenset({"ai_responses", "ai_queries"})


def cleanup_orphan_records(using: str = DEFAULT_DB_ALIAS) -> dict[str, int]:
    """Remove orphaned records across all related tables.

    This comprehensive cleanup handles orphaned records in:
    - messages (conversation deleted)
    - ai_responses (query deleted)
    - ai_queries (conversation deleted)

    Parameters
    ----------
    using:
        The database alias where the cleanup should be executed. Defaults to
        Django's ``DEFAULT_DB_ALIAS``.

    Returns
    -------
    dict[str, int]
        Dictionary with table names as keys and number of deleted rows as values.
    """
    connection = connections[using]
    deleted_counts = {}

    with connection.cursor() as cursor:
        existing_tables = set(connection.introspection.table_names(cursor))

        # Clean up orphaned AI responses first (depends on ai_queries)
        if AI_TABLES.issubset(existing_tables):
            cursor.execute(
                """
                DELETE FROM ai_responses
                WHERE query_id NOT IN (SELECT id FROM ai_queries)
                """
            )
            deleted = cursor.rowcount or 0
            if deleted:
                deleted_counts['ai_responses'] = deleted
                logger.warning(
                    "Removed %s orphan ai_response(s) without a matching query from database alias %s.",
                    deleted,
                    using,
                )

        # Clean up orphaned AI queries (depends on conversations)
        if 'ai_queries' in existing_tables and 'conversations' in existing_tables:
            cursor.execute(
                """
                DELETE FROM ai_queries
                WHERE conversation_id IS NOT NULL
                AND conversation_id NOT IN (SELECT id FROM conversations)
                """
            )
            deleted = cursor.rowcount or 0
            if deleted:
                deleted_counts['ai_queries'] = deleted
                logger.warning(
                    "Removed %s orphan ai_query(ies) without a matching conversation from database alias %s.",
                    deleted,
                    using,
                )

        # Clean up orphaned messages
        if ensure_required_tables_exist(using, existing_tables):
            cursor.execute(
                """
                DELETE FROM messages
                WHERE conversation_id NOT IN (SELECT id FROM conversations)
                """
            )
            deleted = cursor.rowcount or 0
            if deleted:
                deleted_counts['messages'] = deleted
                logger.warning(
                    "Removed %s orphan message(s) without a matching conversation from database alias %s.",
                    deleted,
                    using,
                )

    return deleted_counts


def cleanup_orphan_messages(using: str = DEFAULT_DB_ALIAS) -> int:
    """Legacy function - now calls cleanup_orphan_records.

    This function is kept for backward compatibility but delegates to the
    more comprehensive cleanup_orphan_records function.

    Parameters
    ----------
    using:
        The database alias where the cleanup should be executed.

    Returns
    -------
    int
        The number of message rows that were removed.
    """
    result = cleanup_orphan_records(using)
    return result.get('messages', 0)


def ensure_required_tables_exist(using: str, table_names: Iterable[str]) -> bool:
    """Check if the required tables for cleanup exist.

    This helper primarily exists for unit tests, keeping the table existence
    check logic in one place while remaining easy to patch.
    """

    return REQUIRED_TABLES.issubset(set(table_names))
