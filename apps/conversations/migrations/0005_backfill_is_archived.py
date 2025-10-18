from django.db import migrations


def populate_is_archived(apps, schema_editor):
    Conversation = apps.get_model('conversations', 'Conversation')
    Conversation.objects.filter(is_active=False, is_archived=False).update(is_archived=True)


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0004_make_user_optional'),
    ]

    operations = [
        migrations.RunPython(populate_is_archived, migrations.RunPython.noop),
    ]
