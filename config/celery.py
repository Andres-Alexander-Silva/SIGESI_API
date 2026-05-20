"""Aplicación Celery del proyecto SIGESI.

El worker se arranca con:  celery -A config worker -l info
(en Windows local, añadir --pool=solo).

La configuración se lee desde Django settings con el prefijo ``CELERY_``
(ver config/settings.py). El broker es la misma instancia de Redis que usa
Channels.
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('sigesi')

# Toma CELERY_* desde Django settings.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubre tasks.py en cada app instalada (apps/sigesi/tasks.py).
app.autodiscover_tasks()
