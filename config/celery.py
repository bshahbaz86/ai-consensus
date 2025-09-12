"""
Celery configuration for ChatAI background tasks.
"""
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('chatai')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure task routes and priorities
app.conf.task_routes = {
    'apps.ai_services.tasks.call_claude_api': {'queue': 'ai_tasks'},
    'apps.ai_services.tasks.call_openai_api': {'queue': 'ai_tasks'},
    'apps.ai_services.tasks.summarize_response': {'queue': 'processing'},
    'apps.ai_services.tasks.rank_responses': {'queue': 'processing'},
}

# Configure task priorities
app.conf.task_default_priority = 5
app.conf.worker_prefetch_multiplier = 4
app.conf.task_acks_late = True
app.conf.worker_disable_rate_limits = False

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')