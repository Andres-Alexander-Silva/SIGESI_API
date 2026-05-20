import threading

import pytest
from django.core import mail
from django.core.management import call_command
from django.contrib.auth import get_user_model

from apps.sigesi.utils.email_service import (
    enviar_correo_recuperacion,
    enviar_correo_recuperacion_async,
)

User = get_user_model()
URL = '/api/v1/auth/recuperacion/'


@pytest.mark.django_db
def test_password_recovery_institutional_email_case_insensitive(api_client, db):
    # Create user with specific email
    user = User.objects.create(
        username='testuser1',
        cedula='CC100200',
        email='JulianEduardoVC@ufps.edu.co',
        correo_personal='julian_personal@example.com',
        is_active=True
    )
    
    # Request recovery using lowercase
    resp = api_client.post(URL, {'email': 'julianeduardovc@ufps.edu.co'}, format='json')
    assert resp.status_code == 200
    
    # Verify mail was sent to institutional email
    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert 'JulianEduardoVC@ufps.edu.co' in sent_email.to
    assert 'SIGESI - Recuperación de contraseña' in sent_email.subject


@pytest.mark.django_db
def test_password_recovery_personal_email_case_insensitive_for_egresados(api_client, db):
    # Create graduated user (email is None, correo_personal is set)
    user = User.objects.create(
        username='testuser2',
        cedula='CC100300',
        email=None,
        correo_personal='GraduatedUser@example.com',
        is_graduated=True,
        is_active=True
    )
    
    # Request recovery using lowercase personal email
    resp = api_client.post(URL, {'email': 'graduateduser@example.com'}, format='json')
    assert resp.status_code == 200
    
    # Verify mail was sent to personal email
    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert 'GraduatedUser@example.com' in sent_email.to
    assert 'SIGESI - Recuperación de contraseña' in sent_email.subject


@pytest.mark.django_db
def test_recovery_email_has_deliverability_headers():
    # El envío debe incluir cabeceras que mejoran la entrega/clasificación.
    resultado = enviar_correo_recuperacion(
        destinatario_email='destino@ufps.edu.co',
        destinatario_nombre='Prueba',
        token='tok',
    )

    assert resultado == {"status": "sent"}
    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert 'Reply-To' in sent_email.extra_headers
    assert 'List-Unsubscribe' in sent_email.extra_headers


@pytest.mark.django_db
def test_async_dispatch_runs_send_in_background_thread(settings):
    # Con EMAIL_DELIVERY='thread' el envío se delega a un hilo y la llamada
    # retorna de inmediato (None), sin bloquear con el round-trip SMTP.
    settings.EMAIL_DELIVERY = 'thread'
    resultado = enviar_correo_recuperacion_async(
        destinatario_email='async@ufps.edu.co',
        destinatario_nombre='Async',
        token='tok',
    )
    assert resultado is None

    # El hilo termina enviando vía el backend locmem; esperamos a que corra.
    for hilo in threading.enumerate():
        if hilo.name.startswith('recuperacion-email-'):
            hilo.join(timeout=5)

    assert len(mail.outbox) == 1
    assert 'async@ufps.edu.co' in mail.outbox[0].to


@pytest.mark.django_db
def test_test_email_management_command_queues_message(capsys):
    call_command('test_email', 'diagnostico@ufps.edu.co', '--nombre', 'Diag')

    assert len(mail.outbox) == 1
    assert 'diagnostico@ufps.edu.co' in mail.outbox[0].to
    out = capsys.readouterr().out
    assert 'diagnostico@ufps.edu.co' in out
