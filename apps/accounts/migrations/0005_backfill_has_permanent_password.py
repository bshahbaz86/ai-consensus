from django.db import migrations


def set_has_permanent_password(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    users = User.objects.filter(has_permanent_password=False)
    for user in users.iterator():
        if user.has_usable_password():
            user.has_permanent_password = True
            user.save(update_fields=['has_permanent_password'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_emailpasscode'),
    ]

    operations = [
        migrations.RunPython(set_has_permanent_password, migrations.RunPython.noop),
    ]
