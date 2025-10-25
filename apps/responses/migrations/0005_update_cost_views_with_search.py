from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('responses', '0004_remove_unused_models'),
        ('ai_services', '0003_add_web_search_cost_fields'),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP VIEW IF EXISTS conversation_cost_view;",
            reverse_sql="""
            CREATE VIEW conversation_cost_view AS
            SELECT
                c.id AS conversation_id,
                c.title,
                c.total_messages,
                c.updated_at,
                c.created_at,
                c.is_active,
                COALESCE(SUM(
                    ((CAST(r.input_tokens AS REAL) / 1000.0) * s.input_cost_per_1k) +
                    ((CAST(r.output_tokens AS REAL) / 1000.0) * s.output_cost_per_1k)
                ), 0) AS total_cost,
                COALESCE(SUM(r.input_tokens), 0) AS total_input_tokens,
                COALESCE(SUM(r.output_tokens), 0) AS total_output_tokens,
                COALESCE(SUM(r.input_tokens + r.output_tokens), 0) AS total_tokens,
                COUNT(DISTINCT r.id) AS total_ai_responses
            FROM conversations c
            LEFT JOIN ai_queries q ON q.conversation_id = c.id
            LEFT JOIN ai_responses r ON r.query_id = q.id
            LEFT JOIN ai_services s ON r.service_id = s.id
            GROUP BY c.id, c.title, c.total_messages, c.updated_at, c.created_at, c.is_active;
            """
        ),
        migrations.RunSQL(
            sql="""
            CREATE VIEW conversation_cost_view AS
            WITH service_pricing AS (
                SELECT 'claude' AS service_name, 0.003 AS input_cost_per_1k, 0.015 AS output_cost_per_1k
                UNION ALL SELECT 'openai', 0.005, 0.015
                UNION ALL SELECT 'gemini', 0.0001, 0.0004
            ),
            response_data AS (
                SELECT
                    q.conversation_id,
                    COALESCE(SUM(
                        ((CAST(r.input_tokens AS REAL) / 1000.0) * COALESCE(sp.input_cost_per_1k, s.input_cost_per_1k, 0)) +
                        ((CAST(r.output_tokens AS REAL) / 1000.0) * COALESCE(sp.output_cost_per_1k, s.output_cost_per_1k, 0))
                    ), 0) AS model_cost,
                    COALESCE(SUM(r.input_tokens), 0) AS total_input_tokens,
                    COALESCE(SUM(r.output_tokens), 0) AS total_output_tokens,
                    COALESCE(SUM(r.input_tokens + r.output_tokens), 0) AS total_tokens,
                    COUNT(DISTINCT r.id) AS total_ai_responses
                FROM ai_queries q
                LEFT JOIN ai_responses r ON r.query_id = q.id
                LEFT JOIN ai_services s ON r.service_id = s.id
                LEFT JOIN service_pricing sp ON LOWER(COALESCE(s.name, '')) = sp.service_name
                GROUP BY q.conversation_id
            ),
            search_data AS (
                SELECT
                    conversation_id,
                    COALESCE(SUM(web_search_calls), 0) AS total_search_calls,
                    COALESCE(SUM(web_search_calls) * 0.025, 0) AS total_search_cost
                FROM ai_queries
                GROUP BY conversation_id
            )
            SELECT
                c.id AS conversation_id,
                c.title,
                c.total_messages,
                c.updated_at,
                c.created_at,
                c.is_active,
                COALESCE(rd.model_cost, 0) + COALESCE(sd.total_search_cost, 0) AS total_cost,
                COALESCE(rd.total_input_tokens, 0) AS total_input_tokens,
                COALESCE(rd.total_output_tokens, 0) AS total_output_tokens,
                COALESCE(rd.total_tokens, 0) AS total_tokens,
                COALESCE(rd.total_ai_responses, 0) AS total_ai_responses,
                COALESCE(sd.total_search_calls, 0) AS total_web_search_calls
            FROM conversations c
            LEFT JOIN response_data rd ON rd.conversation_id = c.id
            LEFT JOIN search_data sd ON sd.conversation_id = c.id;
            """,
            reverse_sql="DROP VIEW IF EXISTS conversation_cost_view;"
        ),
    ]
