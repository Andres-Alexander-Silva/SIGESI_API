import logging
import threading
from smtplib import SMTPException
from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def _enviar_en_hilo(
    destinatario_email: str, destinatario_nombre: str, token: str,
) -> None:
    """Lanza el envío SMTP en un hilo daemon y retorna de inmediato."""
    hilo = threading.Thread(
        target=enviar_correo_recuperacion,
        args=(destinatario_email, destinatario_nombre, token),
        name=f"recuperacion-email-{destinatario_email}",
        daemon=True,
    )
    hilo.start()
    logger.info("Envío de correo de recuperación despachado en hilo para %s", destinatario_email)
    return None


def enviar_correo_recuperacion_async(
    destinatario_email: str, destinatario_nombre: str, token: str,
) -> Optional[dict]:
    """Despacha el envío del correo de recuperación sin bloquear la respuesta.

    La estrategia la decide ``settings.EMAIL_DELIVERY``:

    - ``'celery'``: encola una tarea en el worker Celery (durable, con
      reintentos). Si el broker (Redis) está caído, hace *fallback* a un hilo
      para no reintroducir el bloqueo de la petición.
    - ``'thread'``: hilo daemon en segundo plano (sin infraestructura extra).
    - ``'sync'``: ejecuta el envío en línea y retorna su resultado (tests).

    Retorna ``None`` cuando el envío se delegó (celery/thread), o el dict de
    resultado de :func:`enviar_correo_recuperacion` cuando fue síncrono.
    """
    estrategia = getattr(settings, "EMAIL_DELIVERY", "thread")

    if estrategia == "sync":
        return enviar_correo_recuperacion(destinatario_email, destinatario_nombre, token)

    if estrategia == "celery":
        # Import local: evita acoplar este módulo (y los tests que lo importan
        # directamente) al arranque de Celery.
        from kombu.exceptions import OperationalError
        from apps.sigesi.tasks import enviar_correo_recuperacion_task
        try:
            enviar_correo_recuperacion_task.delay(
                destinatario_email, destinatario_nombre, token
            )
            logger.info("Envío de correo de recuperación encolado en Celery para %s", destinatario_email)
            return None
        except OperationalError as e:
            # Broker inaccesible: no podemos colgar la petición, usamos un hilo.
            logger.error(
                "Broker Celery inaccesible (%s); fallback a hilo para %s",
                e, destinatario_email,
            )
            return _enviar_en_hilo(destinatario_email, destinatario_nombre, token)

    # 'thread' (por defecto)
    return _enviar_en_hilo(destinatario_email, destinatario_nombre, token)


def _render_html_recuperacion(destinatario_nombre: str, enlace: str) -> str:
    """Construye el cuerpo HTML del correo de recuperación de contraseña.

    Args:
        destinatario_nombre: Nombre completo a saludar en el encabezado.
        enlace: URL absoluta del frontend para restablecer la contraseña.

    Returns:
        El HTML completo del correo, listo para adjuntar como alternativa.
    """
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f7fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f7fa; padding: 40px 0;">
            <tr>
                <td align="center">
                    <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, rgb(200, 16, 46) 0%, rgb(160, 13, 36) 100%); padding: 32px 40px; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">
                                    SIGESI
                                </h1>
                                <p style="margin: 8px 0 0; color: rgba(255, 255, 255, 0.85); font-size: 14px;">
                                    Sistema de Gestión de Semilleros de Investigación
                                </p>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="padding: 40px;">
                                <h2 style="margin: 0 0 8px; color: #1a1a2e; font-size: 22px; font-weight: 600;">
                                    Hola, {destinatario_nombre}
                                </h2>
                                <p style="margin: 0 0 24px; color: #C8102E; font-size: 15px; line-height: 1.6;">
                                    Recibimos una solicitud para restablecer la contraseña de tu cuenta. 
                                    Haz clic en el siguiente botón para crear una nueva contraseña:
                                </p>

                                <!-- CTA Button -->
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center" style="padding: 8px 0 32px;">
                                            <a href="{enlace}" 
                                               target="_blank"
                                               style="display: inline-block; background: linear-gradient(135deg, rgb(200, 16, 46) 0%, rgb(160, 13, 36) 100%); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 8px; font-size: 16px; font-weight: 600; letter-spacing: 0.3px; box-shadow: 0 4px 12px rgba(26, 115, 232, 0.35);">
                                                Restablecer Contraseña
                                            </a>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Info box -->
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="background-color: #fff8e1; border-left: 4px solid #f9a825; padding: 16px 20px; border-radius: 0 8px 8px 0;">
                                            <p style="margin: 0; color: #5d4037; font-size: 14px; line-height: 1.5;">
                                                ⏱️ Este enlace expirará en <strong>20 minutos</strong> por seguridad.
                                            </p>
                                        </td>
                                    </tr>
                                </table>

                                <p style="margin: 24px 0 0; color: #C8102E; font-size: 13px; line-height: 1.6;">
                                    Si no solicitaste este cambio, puedes ignorar este correo. 
                                    Tu contraseña actual permanecerá sin cambios.
                                </p>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f8fafc; padding: 24px 40px; border-top: 1px solid #e2e8f0; text-align: center;">
                                <p style="margin: 0; color: #C8102E; font-size: 12px; line-height: 1.5;">
                                    Este es un correo automático generado por SIGESI.<br>
                                    Por favor, no respondas a este mensaje.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def _construir_correo(
    destinatario_email: str, destinatario_nombre: str, token: str,
) -> EmailMultiAlternatives:
    """Arma el mensaje de recuperación (asunto, cuerpos, cabeceras) sin enviarlo.

    Args:
        destinatario_email: Email institucional del destinatario.
        destinatario_nombre: Nombre completo del destinatario.
        token: Token JWT de recuperación (20 min de vida).

    Returns:
        El ``EmailMultiAlternatives`` con texto plano + alternativa HTML listo
        para ``send()``.
    """
    enlace = f"{settings.FRONTEND_URL}/recovery-password/{token}"
    html_content = _render_html_recuperacion(destinatario_nombre, enlace)
    from_email = settings.DEFAULT_FROM_EMAIL

    # Cabeceras que reducen la clasificación como spam y dan una vía de
    # respuesta legítima (relevante para la entrega en buzones institucionales).
    headers = {
        "Reply-To": from_email,
        "List-Unsubscribe": f"<mailto:{settings.EMAIL_HOST_USER}>",
    }

    msg = EmailMultiAlternatives(
        "SIGESI - Recuperación de contraseña",
        strip_tags(html_content),
        from_email,
        [destinatario_email],
        headers=headers,
    )
    msg.attach_alternative(html_content, "text/html")
    return msg


def enviar_correo_recuperacion(
    destinatario_email: str, destinatario_nombre: str, token: str,
) -> dict:
    """Envía el correo de recuperación de contraseña vía SMTP (django.core.mail).

    Args:
        destinatario_email: Email institucional del usuario.
        destinatario_nombre: Nombre completo del usuario.
        token: Token JWT de recuperación (20 min de vida).

    Returns:
        ``{"status": "sent"}`` si el servidor SMTP aceptó el mensaje, o
        ``{"status": "error", "error_type": ..., "detail": ...}`` si falló.
        NOTA: "sent" significa que el servidor SMTP (Gmail) aceptó el mensaje,
        no que el destinatario lo haya recibido — la entrega final puede fallar
        por filtrado/cuarentena del lado del receptor.
    """
    try:
        msg = _construir_correo(destinatario_email, destinatario_nombre, token)
        msg.send(fail_silently=False)
        logger.info("Correo de recuperación aceptado por el servidor SMTP para %s", destinatario_email)
        return {"status": "sent"}
    except SMTPException as e:
        # El servidor SMTP rechazó el mensaje: registrar código y respuesta.
        smtp_code = getattr(e, "smtp_code", None)
        smtp_error = getattr(e, "smtp_error", None)
        logger.error(
            "El servidor SMTP rechazó el correo de recuperación para %s [%s] code=%s reply=%s",
            destinatario_email, type(e).__name__, smtp_code, smtp_error,
        )
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "smtp_code": smtp_code,
            "detail": str(smtp_error or e),
        }
    except Exception as e:
        logger.error(
            "Error al enviar correo de recuperación a %s [%s]: %s",
            destinatario_email, type(e).__name__, str(e),
        )
        return {"status": "error", "error_type": type(e).__name__, "detail": str(e)}
