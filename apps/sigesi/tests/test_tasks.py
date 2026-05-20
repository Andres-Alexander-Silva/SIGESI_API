"""Tests de la tarea Celery de envío de correo y del dispatcher con Celery."""
import threading
from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from django.core import mail
from kombu.exceptions import OperationalError

from apps.sigesi.tasks import enviar_correo_recuperacion_task
from apps.sigesi.utils import email_service


@pytest.mark.django_db
def test_task_sends_email_eagerly(settings):
    # ALWAYS_EAGER (forzado en conftest) -> la tarea corre en línea al hacer .delay().
    enviar_correo_recuperacion_task.delay('user@ufps.edu.co', 'Nombre', 'tok')

    assert len(mail.outbox) == 1
    assert 'user@ufps.edu.co' in mail.outbox[0].to


@pytest.mark.django_db
def test_task_retries_on_smtp_error():
    # Ante un resultado de error, la tarea debe pedir reintento (self.retry).
    with patch(
        'apps.sigesi.tasks.enviar_correo_recuperacion',
        return_value={'status': 'error', 'detail': 'fallo SMTP'},
    ):
        with patch.object(enviar_correo_recuperacion_task, 'retry', side_effect=Retry) as mock_retry:
            with pytest.raises(Retry):
                enviar_correo_recuperacion_task.apply(
                    args=('user@ufps.edu.co', 'Nombre', 'tok'), throw=True
                )
    assert mock_retry.called


@pytest.mark.django_db
def test_celery_dispatch_falls_back_to_thread_when_broker_down(settings):
    # Si el broker está caído, el dispatcher NO debe propagar el error ni
    # bloquear: hace fallback a un hilo en segundo plano.
    settings.EMAIL_DELIVERY = 'celery'
    with patch.object(
        enviar_correo_recuperacion_task, 'delay',
        side_effect=OperationalError('broker down'),
    ):
        res = email_service.enviar_correo_recuperacion_async('user@ufps.edu.co', 'Nombre', 'tok')

    assert res is None  # se delegó (no excepción)

    for hilo in threading.enumerate():
        if hilo.name.startswith('recuperacion-email-'):
            hilo.join(timeout=5)

    assert len(mail.outbox) == 1
    assert 'user@ufps.edu.co' in mail.outbox[0].to
