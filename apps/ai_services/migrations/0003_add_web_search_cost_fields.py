from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_services', '0002_alter_aiquery_user'),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP VIEW IF EXISTS conversation_cost_view;",
            reverse_sql=migrations.RunSQL.noop
        ),
        migrations.AddField(
            model_name='aiquery',
            name='web_search_calls',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
