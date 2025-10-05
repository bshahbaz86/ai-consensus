# Generated manually for cost calculation views

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('responses', '0002_add_token_fields'),
        ('ai_services', '0001_initial'),
        ('conversations', '0001_initial'),
    ]

    operations = [
        # Create response_cost_view for per-response cost calculation
        migrations.RunSQL(
            sql="""
            CREATE VIEW response_cost_view AS
            SELECT
                r.id,
                r.query_id,
                r.service_id,
                r.content,
                r.input_tokens,
                r.output_tokens,
                r.created_at,
                -- Calculate cost using service pricing (compatible with both SQLite and PostgreSQL)
                ((CAST(r.input_tokens AS REAL) / 1000.0) * s.input_cost_per_1k) +
                ((CAST(r.output_tokens AS REAL) / 1000.0) * s.output_cost_per_1k) AS calculated_cost,
                s.name AS service_name,
                s.display_name AS service_display_name,
                s.input_cost_per_1k,
                s.output_cost_per_1k
            FROM ai_responses r
            INNER JOIN ai_services s ON r.service_id = s.id;
            """,
            reverse_sql="DROP VIEW IF EXISTS response_cost_view;"
        ),

        # Create conversation_cost_view for per-conversation cost aggregation
        migrations.RunSQL(
            sql="""
            CREATE VIEW conversation_cost_view AS
            SELECT
                c.id AS conversation_id,
                c.title,
                c.total_messages,
                c.updated_at,
                c.created_at,
                c.is_active,
                -- Aggregate total cost from all responses (compatible with both SQLite and PostgreSQL)
                COALESCE(SUM(
                    ((CAST(r.input_tokens AS REAL) / 1000.0) * s.input_cost_per_1k) +
                    ((CAST(r.output_tokens AS REAL) / 1000.0) * s.output_cost_per_1k)
                ), 0) AS total_cost,
                -- Total input tokens across all responses
                COALESCE(SUM(r.input_tokens), 0) AS total_input_tokens,
                -- Total output tokens across all responses
                COALESCE(SUM(r.output_tokens), 0) AS total_output_tokens,
                -- Total tokens across all responses
                COALESCE(SUM(r.input_tokens + r.output_tokens), 0) AS total_tokens,
                -- Count of AI responses
                COUNT(DISTINCT r.id) AS total_ai_responses
            FROM conversations c
            LEFT JOIN ai_queries q ON q.conversation_id = c.id
            LEFT JOIN ai_responses r ON r.query_id = q.id
            LEFT JOIN ai_services s ON r.service_id = s.id
            GROUP BY c.id, c.title, c.total_messages, c.updated_at, c.created_at, c.is_active;
            """,
            reverse_sql="DROP VIEW IF EXISTS conversation_cost_view;"
        ),
    ]
