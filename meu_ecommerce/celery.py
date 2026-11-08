import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meu_ecommerce.settings')

app = Celery('meu_ecommerce')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
