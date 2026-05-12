import logging
import resend
from django.conf import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY


def enviar_correo_recuperacion(destinatario_email, destinatario_nombre, token):
    """
    Envía un correo de recuperación de contraseña usando Resend.

    Args:
        destinatario_email: Email institucional del usuario
        destinatario_nombre: Nombre completo del usuario
        token: Token JWT de recuperación (20 min de vida)

    Returns:
        dict | None: Respuesta de Resend con el ID del email, o None si falla
    """
    enlace = f"{settings.FRONTEND_URL}/recovery-password/{token}"

    html_content = f"""
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

    try:
        result = resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [destinatario_email],
            "subject": "SIGESI - Recuperación de contraseña",
            "html": html_content,
        })
        logger.info("Correo de recuperación enviado a %s (id: %s)", destinatario_email, result.get('id'))
        return result
    except Exception as e:
        logger.error("Error al enviar correo de recuperación a %s: %s", destinatario_email, str(e))
        return None
