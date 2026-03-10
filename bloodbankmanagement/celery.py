import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bloodbankmanagement.settings')

app = Celery('bloodbankmanagement')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'expire_blood_requests_every_midnight': {
        'task': 'blood.tasks.expire_blood_requests',
        'schedule': crontab(minute=0, hour=0),
    },
    'expire_safety_periods_every_midnight': {
        'task': 'blood.tasks.expire_safety_periods',
        'schedule': crontab(minute=0, hour=0),
    },
}

app.conf.timezone = 'UTC'
