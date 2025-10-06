from django.apps import AppConfig
from django.db.models.signals import pre_migrate


class ConversationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.conversations'
    label = 'conversations'

    def ready(self):
        from .maintenance import cleanup_orphan_messages

        pre_migrate.connect(
            self._pre_migrate_cleanup,
            sender=self,
            dispatch_uid='conversations_pre_migrate_cleanup',
        )

    @staticmethod
    def _pre_migrate_cleanup(app_config, using, **kwargs):
        from .maintenance import cleanup_orphan_messages
        cleanup_orphan_messages(using)
