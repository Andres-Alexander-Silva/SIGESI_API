"""Tareas Celery de la app sigesi.

Por ahora solo el envío de correo de recuperación, movido fuera del ciclo
petición/respuesta para no bloquear el endpoint con el round-trip SMTP.
"""
import logging

from celery import shared_task

from apps.sigesi.utils.email_service import enviar_correo_recuperacion

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def enviar_correo_recuperacion_task(self, destinatario_email, destinatario_nombre, token):
    """Envía el correo de recuperación; reintenta ante fallos transitorios.

    A diferencia del hilo en segundo plano, un fallo SMTP transitorio se
    reintenta hasta 3 veces (30s de espera) en lugar de perderse en silencio.
    """
    resultado = enviar_correo_recuperacion(destinatario_email, destinatario_nombre, token)
    if resultado and resultado.get('status') == 'error':
        logger.warning(
            "Reintentando envío de correo de recuperación a %s (intento %s/%s)",
            destinatario_email, self.request.retries + 1, self.max_retries,
        )
        raise self.retry(exc=RuntimeError(resultado.get('detail', 'error SMTP')))
    return resultado
